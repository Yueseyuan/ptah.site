from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models import Organization
from app.dependencies import get_current_user, require_admin
from app.models import User

router = APIRouter(prefix="/api/organizations", tags=["organizations"])


class OrgCreate(BaseModel):
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class OrgUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    active: Optional[bool] = None


def _out(org: Organization) -> dict:
    return {
        "id": org.id,
        "name": org.name,
        "address": org.address,
        "phone": org.phone,
        "email": org.email,
        "active": org.active,
        "created_at": org.created_at.isoformat() if org.created_at else None,
    }


@router.get("/")
def list_organizations(db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    return [_out(o) for o in db.query(Organization).filter(Organization.active == True).all()]


@router.post("/", status_code=201)
def create_organization(data: OrgCreate, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    org = Organization(**data.model_dump())
    db.add(org)
    db.commit()
    db.refresh(org)
    return _out(org)


@router.get("/{org_id}")
def get_organization(org_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(404, "Organization not found")
    return _out(org)


@router.patch("/{org_id}")
def update_organization(org_id: int, data: OrgUpdate, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(404, "Organization not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        if v is not None:
            setattr(org, k, v)
    db.commit()
    db.refresh(org)
    return _out(org)
