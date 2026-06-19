"""Client portal router — self-service endpoints for portal clients."""
import os
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AegisClient, AegisCase, ClientDocument, User
from app.dependencies import get_current_user, get_portal_client
from app.config import settings
from app.services.auth_service import hash_password, create_access_token

router = APIRouter(prefix="/api/portal", tags=["portal"])

PORTAL_DOC_TYPES = [
    "credit_report_experian",
    "credit_report_equifax",
    "credit_report_transunion",
    "drivers_license",
    "proof_of_address",
    "supporting_doc",
    "other",
]

PORTAL_STATUS_LABELS = {
    "pending":      "Pending Review",
    "docs_needed":  "Documents Needed",
    "under_review": "Under Review",
    "active":       "Active — Disputes in Progress",
    "completed":    "Completed",
}


class ClientRegister(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = ""
    address: Optional[str] = ""
    city: Optional[str] = ""
    state: Optional[str] = "SC"
    zip_code: Optional[str] = ""
    dob: Optional[str] = ""
    ssn_last4: Optional[str] = ""
    username: str
    password: str


class ProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    dob: Optional[str] = None
    ssn_last4: Optional[str] = None


def _case_out(case: AegisCase) -> dict:
    return {
        "id": case.id,
        "case_number": case.case_number,
        "status": case.status,
        "portal_status": case.portal_status or "pending",
        "portal_status_label": PORTAL_STATUS_LABELS.get(case.portal_status or "pending", case.portal_status),
        "goal": case.goal,
        "created_at": case.created_at.isoformat() if case.created_at else None,
    }


def _doc_out(doc: ClientDocument) -> dict:
    return {
        "id": doc.id,
        "doc_type": doc.doc_type,
        "bureau": doc.bureau,
        "original_filename": doc.original_filename,
        "notes": doc.notes,
        "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
        "reviewed": doc.reviewed,
    }


@router.post("/register", status_code=201)
def client_register(data: ClientRegister, db: Session = Depends(get_db)):
    """Public endpoint — register a new client portal account."""
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(400, "Username already taken")
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(400, "Email already registered")

    user = User(
        username=data.username,
        email=data.email,
        full_name=f"{data.first_name} {data.last_name}",
        hashed_password=hash_password(data.password),
        role="client",
        is_active=True,
    )
    db.add(user)
    db.flush()

    client = AegisClient(
        first_name=data.first_name,
        last_name=data.last_name,
        email=data.email,
        phone=data.phone or "",
        address=data.address or "",
        city=data.city or "",
        state=data.state or "SC",
        zip_code=data.zip_code or "",
        dob=data.dob or "",
        ssn_last4=data.ssn_last4 or "",
        portal_user_id=user.id,
    )
    db.add(client)
    db.flush()

    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    case = AegisCase(
        client_id=client.id,
        case_number=f"CA-{client.last_name.upper()[:4]}-{ts}",
        status="intake",
        portal_status="pending",
        goal="Credit report review and dispute",
    )
    db.add(case)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user.username, "role": "client"})
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": "client",
        "username": user.username,
        "client_id": client.id,
        "case_number": case.case_number,
    }


@router.get("/me")
def portal_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return portal client's profile and case summary."""
    client = db.query(AegisClient).filter(AegisClient.portal_user_id == current_user.id).first()
    if not client:
        raise HTTPException(404, "No client profile found")

    case = db.query(AegisCase).filter(AegisCase.client_id == client.id).order_by(AegisCase.id.desc()).first()

    doc_count = db.query(ClientDocument).filter(ClientDocument.client_id == client.id).count()

    return {
        "user": {"username": current_user.username, "email": current_user.email},
        "client": {
            "id": client.id,
            "first_name": client.first_name,
            "last_name": client.last_name,
            "email": client.email,
            "phone": client.phone,
            "address": client.address,
            "city": client.city,
            "state": client.state,
            "zip_code": client.zip_code,
            "dob": client.dob,
            "ssn_last4": client.ssn_last4,
        },
        "case": _case_out(case) if case else None,
        "documents_uploaded": doc_count,
    }


@router.patch("/profile")
def update_profile(
    data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    client = db.query(AegisClient).filter(AegisClient.portal_user_id == current_user.id).first()
    if not client:
        raise HTTPException(404, "No client profile found")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(client, field, value)
    db.commit()
    db.refresh(client)
    return {"ok": True, "first_name": client.first_name, "last_name": client.last_name}


@router.get("/case")
def portal_case(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    client = db.query(AegisClient).filter(AegisClient.portal_user_id == current_user.id).first()
    if not client:
        raise HTTPException(404, "No client profile found")
    case = db.query(AegisCase).filter(AegisCase.client_id == client.id).order_by(AegisCase.id.desc()).first()
    if not case:
        raise HTTPException(404, "No case found")
    return _case_out(case)


@router.get("/documents")
def list_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    client = db.query(AegisClient).filter(AegisClient.portal_user_id == current_user.id).first()
    if not client:
        raise HTTPException(404, "No client profile found")
    docs = db.query(ClientDocument).filter(ClientDocument.client_id == client.id).order_by(ClientDocument.uploaded_at.desc()).all()
    return [_doc_out(d) for d in docs]


@router.post("/documents/upload")
def upload_document(
    doc_type: str = Form(...),
    bureau: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if doc_type not in PORTAL_DOC_TYPES:
        raise HTTPException(400, f"Invalid doc_type. Must be one of: {', '.join(PORTAL_DOC_TYPES)}")

    client = db.query(AegisClient).filter(AegisClient.portal_user_id == current_user.id).first()
    if not client:
        raise HTTPException(404, "No client profile found")
    case = db.query(AegisCase).filter(AegisCase.client_id == client.id).order_by(AegisCase.id.desc()).first()

    upload_dir = os.path.join(settings.UPLOAD_DIR, "client_docs", str(client.id))
    os.makedirs(upload_dir, exist_ok=True)

    ext = os.path.splitext(file.filename or "doc")[1] or ".bin"
    filename = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(upload_dir, filename)

    with open(file_path, "wb") as f:
        f.write(file.file.read())

    doc = ClientDocument(
        case_id=case.id if case else None,
        client_id=client.id,
        doc_type=doc_type,
        bureau=bureau,
        original_filename=file.filename,
        file_path=file_path,
        notes=notes,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return _doc_out(doc)


@router.get("/disputes")
def portal_disputes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Read-only dispute status for portal clients."""
    from app.models import DisputeRound, DisputeItem
    client = db.query(AegisClient).filter(AegisClient.portal_user_id == current_user.id).first()
    if not client:
        raise HTTPException(404, "No client profile found")
    case = db.query(AegisCase).filter(AegisCase.client_id == client.id).order_by(AegisCase.id.desc()).first()
    if not case:
        return []
    rounds = db.query(DisputeRound).filter(DisputeRound.case_id == case.id).order_by(DisputeRound.round_number).all()
    return [
        {
            "round_number": r.round_number,
            "recipient_type": r.recipient_type,
            "bureau": r.bureau,
            "recipient_name": r.recipient_name,
            "status": r.status,
            "sent_date": r.sent_date,
            "response_due_date": r.response_due_date,
            "items": [
                {
                    "creditor_name": item.creditor_name,
                    "status": item.status,
                    "resolution": item.resolution,
                }
                for item in r.items
            ],
        }
        for r in rounds
    ]


# Staff endpoint — list pending portal intake cases
@router.get("/admin/pending")
def pending_portal_cases(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Staff: list all cases created via portal that are pending review."""
    if current_user.role not in ("admin", "investigator", "reviewer"):
        raise HTTPException(403, "Staff access required")
    cases = db.query(AegisCase).filter(AegisCase.portal_status == "pending").order_by(AegisCase.created_at.desc()).all()
    results = []
    for case in cases:
        client = db.query(AegisClient).filter(AegisClient.id == case.client_id).first()
        doc_count = db.query(ClientDocument).filter(ClientDocument.case_id == case.id).count()
        results.append({
            "case_id": case.id,
            "case_number": case.case_number,
            "portal_status": case.portal_status,
            "client_name": f"{client.first_name} {client.last_name}" if client else "Unknown",
            "client_email": client.email if client else "",
            "client_state": client.state if client else "",
            "documents_uploaded": doc_count,
            "created_at": case.created_at.isoformat() if case.created_at else None,
        })
    return results


@router.patch("/admin/case/{case_id}/status")
def update_portal_case_status(
    case_id: int,
    portal_status: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Staff: update a portal case status."""
    if current_user.role not in ("admin", "investigator"):
        raise HTTPException(403, "Staff access required")
    valid = list(PORTAL_STATUS_LABELS.keys())
    if portal_status not in valid:
        raise HTTPException(400, f"portal_status must be one of: {', '.join(valid)}")
    case = db.query(AegisCase).filter(AegisCase.id == case_id).first()
    if not case:
        raise HTTPException(404, "Case not found")
    case.portal_status = portal_status
    if portal_status == "active":
        case.status = "active"
    db.commit()
    return {"ok": True, "portal_status": portal_status}


@router.patch("/admin/documents/{doc_id}/reviewed")
def mark_document_reviewed(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Staff: mark a client-uploaded document as reviewed."""
    if current_user.role not in ("admin", "investigator", "reviewer"):
        raise HTTPException(403, "Staff access required")
    doc = db.query(ClientDocument).filter(ClientDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "Document not found")
    doc.reviewed = True
    db.commit()
    return {"ok": True}
