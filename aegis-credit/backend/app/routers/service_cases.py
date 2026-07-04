import json
from datetime import datetime
from typing import Optional, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import AegisClient, ServiceCase, User

router = APIRouter(prefix="/api/service-cases", tags=["service-cases"])

# ---------------------------------------------------------------------------
# Division registry
# ---------------------------------------------------------------------------

DIVISIONS = [
    {
        "slug": "notary",
        "name": "Mobile Notary",
        "description": (
            "Certified mobile notary services for loan signings, real estate closings, "
            "affidavits, powers of attorney, and other legal documents — at a location "
            "convenient for you."
        ),
        "icon": "stamp",
    },
    {
        "slug": "credit",
        "name": "Credit Restoration",
        "description": (
            "Comprehensive credit repair and restoration services including bureau dispute "
            "management, FCRA violation identification, goodwill interventions, and "
            "ongoing score monitoring to rebuild your financial profile."
        ),
        "icon": "credit-card",
    },
    {
        "slug": "criminal",
        "name": "Criminal Record Relief",
        "description": (
            "Document preparation and attorney referral services for expungements, record "
            "sealings, pardons, and post-conviction relief — helping clients move forward "
            "with a clean slate."
        ),
        "icon": "shield",
    },
    {
        "slug": "document",
        "name": "Document Preparation",
        "description": (
            "Professional preparation of legal and business documents including contracts, "
            "LLC formations, demand letters, lease agreements, and custom forms — "
            "accurate, compliant, and ready to sign."
        ),
        "icon": "file-text",
    },
    {
        "slug": "judgment",
        "name": "Judgment & Asset Recovery",
        "description": (
            "Strategic assistance with judgment enforcement, lien research, asset location, "
            "and collections — helping creditors and individuals recover what they are owed "
            "through legal channels."
        ),
        "icon": "gavel",
    },
    {
        "slug": "consulting",
        "name": "Business Consulting",
        "description": (
            "Practical business advisory services covering entity formation, compliance, "
            "credit building for businesses, operational workflows, and growth strategy "
            "tailored to small and mid-sized enterprises."
        ),
        "icon": "briefcase",
    },
    {
        "slug": "overages",
        "name": "Tax Overage Recovery",
        "description": (
            "Asset recovery services for tax deed surplus funds — helping former property "
            "owners reclaim excess proceeds from tax sales through authorized claim filing, "
            "county research, and end-to-end case management on a contingency basis."
        ),
        "icon": "landmark",
    },
]

_VALID_SLUGS = {d["slug"] for d in DIVISIONS}
_VALID_STATUSES = {"intake", "active", "on_hold", "closed"}


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class ServiceCaseCreate(BaseModel):
    client_id: int
    division_slug: str
    title: Optional[str] = None
    intake_data: Optional[Any] = None   # dict from frontend, serialised to JSON string
    notes: Optional[str] = None
    assigned_to: Optional[str] = None
    status: Optional[str] = "intake"


class ServiceCaseUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None
    intake_data: Optional[Any] = None   # dict or JSON string
    notes: Optional[str] = None
    assigned_to: Optional[str] = None


class ServiceCaseOut(BaseModel):
    id: int
    client_id: int
    division_slug: str
    case_number: Optional[str]
    status: str
    title: Optional[str]
    intake_data: Optional[str]
    notes: Optional[str]
    assigned_to: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _gen_case_number(division_slug: str, year: int, record_id: int) -> str:
    prefix = division_slug[:3].upper()
    return f"SVC-{prefix}-{year}-{record_id:04d}"


def _parse_intake(raw: Optional[str]) -> dict:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def _serialize_intake(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        return value  # already serialized
    return json.dumps(value)


def _out(sc: ServiceCase, client: Optional[AegisClient] = None) -> dict:
    return {
        "id": sc.id,
        "client_id": sc.client_id,
        "client_name": (
            f"{client.first_name} {client.last_name}".strip() if client else None
        ),
        "division_slug": sc.division_slug,
        "case_number": sc.case_number,
        "status": sc.status,
        "title": sc.title,
        "intake_data": _parse_intake(sc.intake_data),
        "notes": sc.notes,
        "assigned_to": sc.assigned_to,
        "created_at": sc.created_at.isoformat() if sc.created_at else None,
        "updated_at": sc.updated_at.isoformat() if sc.updated_at else None,
    }


# ---------------------------------------------------------------------------
# Routes — /divisions must come before /{id} to avoid path conflict
# ---------------------------------------------------------------------------

@router.get("/divisions")
def list_divisions():
    """Return all 6 service divisions with slug, display name, description, and icon."""
    return DIVISIONS


@router.get("/")
def list_service_cases(
    division: Optional[str] = None,
    client_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """List service cases with optional filters: division slug, client_id, status."""
    q = db.query(ServiceCase)
    if division is not None:
        q = q.filter(ServiceCase.division_slug == division)
    if client_id is not None:
        q = q.filter(ServiceCase.client_id == client_id)
    if status is not None:
        q = q.filter(ServiceCase.status == status)
    cases = q.order_by(ServiceCase.id.desc()).all()
    client_map = {
        c.id: c
        for c in db.query(AegisClient).filter(
            AegisClient.id.in_([sc.client_id for sc in cases])
        ).all()
    }
    return [_out(sc, client_map.get(sc.client_id)) for sc in cases]


@router.post("/", status_code=201)
def create_service_case(
    data: ServiceCaseCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Create a new service case. Validates division slug and client existence."""
    if data.division_slug not in _VALID_SLUGS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid division_slug '{data.division_slug}'. "
                   f"Must be one of: {', '.join(sorted(_VALID_SLUGS))}",
        )
    if data.status and data.status not in _VALID_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status '{data.status}'. "
                   f"Must be one of: {', '.join(sorted(_VALID_STATUSES))}",
        )

    client = db.query(AegisClient).filter(AegisClient.id == data.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    payload = data.model_dump()
    payload["intake_data"] = _serialize_intake(payload.get("intake_data"))
    sc = ServiceCase(**payload)
    # Placeholder case_number — will be replaced after flush gives us the id.
    sc.case_number = "SVC-PENDING"
    db.add(sc)
    db.flush()   # populates sc.id without committing

    year = (sc.created_at or datetime.utcnow()).year
    sc.case_number = _gen_case_number(sc.division_slug, year, sc.id)
    db.commit()
    db.refresh(sc)
    return _out(sc, client)


@router.get("/{service_case_id}")
def get_service_case(
    service_case_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Retrieve a single service case by ID."""
    sc = db.query(ServiceCase).filter(ServiceCase.id == service_case_id).first()
    if not sc:
        raise HTTPException(status_code=404, detail="Service case not found")
    client = db.query(AegisClient).filter(AegisClient.id == sc.client_id).first()
    return _out(sc, client)


@router.put("/{service_case_id}")
def update_service_case(
    service_case_id: int,
    data: ServiceCaseUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Update title, status, intake_data, notes, or assigned_to for a service case."""
    sc = db.query(ServiceCase).filter(ServiceCase.id == service_case_id).first()
    if not sc:
        raise HTTPException(status_code=404, detail="Service case not found")

    if data.status is not None and data.status not in _VALID_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status '{data.status}'. "
                   f"Must be one of: {', '.join(sorted(_VALID_STATUSES))}",
        )

    updates = data.model_dump(exclude_unset=True)
    if "intake_data" in updates:
        updates["intake_data"] = _serialize_intake(updates["intake_data"])
    for field, value in updates.items():
        setattr(sc, field, value)

    db.commit()
    db.refresh(sc)
    client = db.query(AegisClient).filter(AegisClient.id == sc.client_id).first()
    return _out(sc, client)


@router.patch("/{service_case_id}")
def patch_service_case(
    service_case_id: int,
    data: ServiceCaseUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Partial update — same as PUT but registered as PATCH for frontend compatibility."""
    return update_service_case(service_case_id, data, db, _user)


@router.delete("/{service_case_id}", status_code=204)
def delete_service_case(
    service_case_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Delete a service case by ID."""
    sc = db.query(ServiceCase).filter(ServiceCase.id == service_case_id).first()
    if not sc:
        raise HTTPException(status_code=404, detail="Service case not found")
    db.delete(sc)
    db.commit()
