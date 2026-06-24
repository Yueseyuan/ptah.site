"""Client portal router — self-service endpoints for portal clients."""
import os
import secrets
import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AegisClient, AegisCase, ClientDocument, User, PasswordResetToken
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
    try:
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
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"[REGISTER-ERROR] {type(e).__name__}: {e}")
        raise HTTPException(500, f"Registration failed: {type(e).__name__}: {e}")


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


# Staff endpoint — list portal intake cases
@router.get("/admin/pending")
def pending_portal_cases(
    status: str = "pending",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Staff: list cases created via portal. Pass status=all for every portal case."""
    if current_user.role not in ("admin", "investigator", "reviewer"):
        raise HTTPException(403, "Staff access required")
    q = db.query(AegisCase).filter(AegisCase.portal_status.isnot(None))
    if status != "all":
        q = q.filter(AegisCase.portal_status == status)
    cases = q.order_by(AegisCase.created_at.desc()).all()
    results = []
    for case in cases:
        client = db.query(AegisClient).filter(AegisClient.id == case.client_id).first()
        doc_count = db.query(ClientDocument).filter(ClientDocument.case_id == case.id).count()
        results.append({
            "case_id": case.id,
            "case_number": case.case_number,
            "portal_status": case.portal_status,
            "client_id": client.id if client else None,
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


# ── Letter Downloads ──────────────────────────────────────────────────────────

def _get_client_and_case(current_user: User, db: Session):
    """Helper: return (client, case) for the authenticated portal user."""
    client = db.query(AegisClient).filter(AegisClient.portal_user_id == current_user.id).first()
    if not client:
        raise HTTPException(404, "No client profile found")
    case = db.query(AegisCase).filter(AegisCase.client_id == client.id).order_by(AegisCase.id.desc()).first()
    if not case:
        raise HTTPException(404, "No case found")
    return client, case


@router.get("/letters")
def list_portal_letters(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List letters available for download by the portal client."""
    from app.models import DisputeRound
    client, case = _get_client_and_case(current_user, db)

    rounds = db.query(DisputeRound).filter(DisputeRound.case_id == case.id).order_by(
        DisputeRound.round_number, DisputeRound.id
    ).all()

    ROUND_TYPE_LABELS = {
        "bureau":                  "Bureau Dispute Letter",
        "creditor":                "Creditor Dispute Letter",
        "debt_collector":          "Debt Collector Letter",
        "failure_to_investigate":  "Failure to Investigate Letter",
        "method_of_verification":  "Method of Verification Letter",
        "full_file_disclosure":    "Full File Disclosure Request",
        "cease_desist":            "Cease & Desist Letter",
        "cfpb_complaint":          "CFPB Complaint",
        "student_loan":            "Student Loan Dispute Letter",
        "personal_info_dispute":   "Personal Information Dispute",
    }

    dispute_letters = [
        {
            "id": f"dispute_{r.id}",
            "type": "dispute",
            "round_id": r.id,
            "label": ROUND_TYPE_LABELS.get(r.recipient_type or "", "Dispute Letter"),
            "recipient": r.bureau or r.recipient_name or r.recipient_type,
            "round_number": r.round_number,
            "status": r.status,
            "sent_date": r.sent_date,
            "download_url": f"/api/portal/letters/dispute/{r.id}",
        }
        for r in rounds
    ]

    static_letters = [
        {
            "id": "affidavit",
            "type": "affidavit",
            "label": "Affidavit of Truth",
            "recipient": "All Bureaus / Creditors",
            "download_url": "/api/portal/letters/affidavit",
        },
        {
            "id": "authorization",
            "type": "authorization",
            "label": "Authorization Letter",
            "recipient": "Cruel & Associates",
            "download_url": "/api/portal/letters/authorization",
        },
    ]

    return {"dispute_letters": dispute_letters, "static_letters": static_letters}


@router.get("/letters/affidavit")
def portal_download_affidavit(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Client: download their Affidavit of Truth."""
    from app.routers.report_generator import _make_affidavit
    client, case = _get_client_and_case(current_user, db)
    today = datetime.now().strftime("%B %d, %Y")
    content = _make_affidavit(client, case, today)
    filename = f"Affidavit_{client.last_name}_{client.first_name}_{datetime.now().strftime('%Y%m%d')}.txt"
    return PlainTextResponse(
        content,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/letters/authorization")
def portal_download_authorization(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Client: download their Authorization Letter."""
    from app.routers.report_generator import _make_authorization_letter
    client, case = _get_client_and_case(current_user, db)
    today = datetime.now().strftime("%B %d, %Y")
    content = _make_authorization_letter(client, today)
    filename = f"Authorization_{client.last_name}_{client.first_name}_{datetime.now().strftime('%Y%m%d')}.txt"
    return PlainTextResponse(
        content,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/letters/dispute/{round_id}")
def portal_download_dispute_letter(
    round_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Client: download a specific dispute letter (ownership-verified)."""
    from app.models import DisputeRound
    from app.routers.report_generator import _make_dispute_letter
    client, case = _get_client_and_case(current_user, db)

    round_ = db.query(DisputeRound).filter(
        DisputeRound.id == round_id,
        DisputeRound.case_id == case.id,
    ).first()
    if not round_:
        raise HTTPException(404, "Letter not found")

    no_items_ok = (round_.recipient_type or "").lower() in (
        "full_file_disclosure", "cfpb_complaint", "personal_info_dispute",
    )
    if not round_.items and not no_items_ok:
        raise HTTPException(400, "This letter has no dispute items yet — contact your case manager.")

    today = datetime.now().strftime("%B %d, %Y")
    content = _make_dispute_letter(round_, client, today)
    slug = (round_.bureau or round_.recipient_name or round_.recipient_type or "letter").replace(" ", "_").lower()
    filename = f"Letter_{slug}_Round{round_.round_number}_{datetime.now().strftime('%Y%m%d')}.txt"
    return PlainTextResponse(
        content,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Password Reset ────────────────────────────────────────────────────────────

class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


@router.post("/forgot-password")
def forgot_password(data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Public: request a password reset link. Always returns 200 to prevent email enumeration."""
    from app.services.email_service import send_password_reset_email

    user = db.query(User).filter(User.email == data.email).first()
    if user and user.is_active:
        db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used == False,  # noqa: E712
        ).delete()
        db.flush()

        raw_token = secrets.token_urlsafe(32)
        reset_token = PasswordResetToken(
            user_id=user.id,
            token=raw_token,
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        db.add(reset_token)
        db.commit()

        reset_url = f"{settings.PORTAL_BASE_URL}/portal/reset-password?token={raw_token}"
        client = db.query(AegisClient).filter(AegisClient.portal_user_id == user.id).first()
        first_name = client.first_name if client else ""
        try:
            send_password_reset_email(user.email, reset_url, first_name)
        except Exception as e:
            print(f"[PASSWORD RESET EMAIL ERROR] {e}")

    return {"ok": True, "message": "If that email is registered, a reset link has been sent."}


@router.post("/reset-password")
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Public: consume a reset token and set a new password."""
    if len(data.new_password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")

    record = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == data.token,
        PasswordResetToken.used == False,  # noqa: E712
    ).first()

    if not record:
        raise HTTPException(400, "Invalid or already-used reset link")
    if datetime.utcnow() > record.expires_at:
        raise HTTPException(400, "Reset link has expired. Please request a new one.")

    user = db.query(User).filter(User.id == record.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(400, "Account not found or inactive")

    user.hashed_password = hash_password(data.new_password)
    record.used = True
    db.commit()
    return {"ok": True, "message": "Password updated. You can now log in with your new password."}
