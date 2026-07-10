"""Client portal router — self-service endpoints for portal clients."""
import os
import secrets
import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AegisClient, AegisCase, ClientDocument, CreditReport, EvidenceItem, User, PasswordResetToken, ServiceCase
from app.dependencies import get_current_user, get_portal_client
from app.config import settings
from app.services.auth_service import hash_password, create_access_token
from app.services.email_service import (
    send_welcome_email,
    send_document_uploaded_admin_alert,
    send_document_reviewed_email,
    send_case_status_update_email,
)

# Credit report doc_type → bureau name mapping
_CREDIT_REPORT_TYPES = {
    "credit_report_experian": "experian",
    "credit_report_equifax": "equifax",
    "credit_report_transunion": "transunion",
}

# Evidence title map for identity/support docs
_EVIDENCE_TITLES = {
    "drivers_license": "Driver's License / State ID",
    "proof_of_address": "Proof of Address",
    "supporting_doc": "Supporting Document",
    "other": "Client Document",
}


def _parse_portal_credit_report(report_id: int, case_id: int) -> None:
    """Background task: parse a portal-uploaded credit report using the same pipeline as admin uploads."""
    from app.database import SessionLocal
    from app.models import CreditReport
    from app.services.pdf_service import extract_text_from_pdf, detect_bureau_from_text
    from app.services.ai_service import extract_report_data, extract_tradelines_from_text
    from app.routers.reports import _save_tradelines, _save_inquiries, _save_personal_info

    db = SessionLocal()
    try:
        report = db.query(CreditReport).filter(CreditReport.id == report_id).first()
        if not report:
            return

        raw_text = extract_text_from_pdf(report.file_path)
        if not report.bureau or report.bureau == "unknown":
            detected = detect_bureau_from_text(raw_text)
            if detected:
                report.bureau = detected

        report.raw_text = raw_text
        report.parse_status = "parsed"
        db.commit()

        try:
            extracted = extract_report_data(raw_text)
            tradelines_data = extracted.get("tradelines", [])
            inquiries_data = extracted.get("inquiries", [])
            pi_data = extracted.get("personal_info", [])
        except Exception:
            tradelines_data = extract_tradelines_from_text(raw_text)
            inquiries_data = []
            pi_data = []

        _save_tradelines(db, case_id, report, tradelines_data)
        _save_inquiries(db, case_id, report_id, inquiries_data)
        _save_personal_info(db, case_id, report_id, pi_data)
        db.commit()
        print(f"[PORTAL] Parsed credit report {report_id} for case {case_id}: "
              f"{len(tradelines_data)} tradelines, {len(inquiries_data)} inquiries")
    except Exception as e:
        print(f"[PORTAL] Failed to parse credit report {report_id}: {e}")
        try:
            report = db.query(CreditReport).filter(CreditReport.id == report_id).first()
            if report:
                report.parse_status = "failed"
                report.parse_error = str(e)
                db.commit()
        except Exception:
            pass
    finally:
        db.close()

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
        try:
            send_welcome_email(client.email, client.first_name, case.case_number)
        except Exception as _e:
            print(f"[EMAIL] Welcome email failed: {_e}")
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
    background_tasks: BackgroundTasks,
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

    # Auto-detect bureau for credit report types
    resolved_bureau = bureau or _CREDIT_REPORT_TYPES.get(doc_type)

    doc = ClientDocument(
        case_id=case.id if case else None,
        client_id=client.id,
        doc_type=doc_type,
        bureau=resolved_bureau,
        original_filename=file.filename,
        file_path=file_path,
        notes=notes,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    if case:
        if doc_type in _CREDIT_REPORT_TYPES:
            # Create a CreditReport record and queue parsing — same pipeline as admin upload
            report = CreditReport(
                case_id=case.id,
                bureau=_CREDIT_REPORT_TYPES[doc_type],
                file_path=file_path,
                parse_status="pending",
            )
            db.add(report)
            db.commit()
            db.refresh(report)
            background_tasks.add_task(_parse_portal_credit_report, report.id, case.id)
            print(f"[PORTAL] Queued credit report parsing: case={case.id} bureau={report.bureau}")
        elif doc_type in _EVIDENCE_TITLES:
            # Add to case evidence so it shows in the Evidence tab
            evidence = EvidenceItem(
                case_id=case.id,
                evidence_type="identity_document" if doc_type in ("drivers_license", "proof_of_address") else "correspondence",
                title=_EVIDENCE_TITLES[doc_type],
                description=notes or "Uploaded by client via portal",
                file_path=file_path,
                source="client_portal",
                collected_at=datetime.utcnow().isoformat(),
            )
            db.add(evidence)
            db.commit()

    try:
        case_number = case.case_number if case else "N/A"
        send_document_uploaded_admin_alert(
            admin_email=settings.ADMIN_NOTIFICATION_EMAIL,
            client_name=f"{client.first_name} {client.last_name}",
            client_email=client.email,
            doc_type=doc_type,
            filename=file.filename or "unknown",
            case_number=case_number,
        )
    except Exception as _e:
        print(f"[EMAIL] Admin document alert failed: {_e}")

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


@router.get("/outcomes")
def portal_outcomes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Read-only outcomes and credit score progress for portal clients."""
    from app.models import Outcome
    client = db.query(AegisClient).filter(AegisClient.portal_user_id == current_user.id).first()
    if not client:
        raise HTTPException(404, "No client profile found")
    case = db.query(AegisCase).filter(AegisCase.client_id == client.id).order_by(AegisCase.id.desc()).first()
    if not case:
        return {"outcomes": [], "score_snapshots": []}
    outcomes = db.query(Outcome).filter(Outcome.case_id == case.id).order_by(Outcome.achieved_date).all()
    # Surface score snapshots from score_increase outcomes and any outcome that has before/after
    snapshots = [
        {
            "date": o.achieved_date,
            "bureau": o.bureau,
            "score_before": o.score_before,
            "score_after": o.score_after,
        }
        for o in outcomes
        if o.score_before is not None or o.score_after is not None
    ]
    return {
        "outcomes": [
            {
                "outcome_type": o.outcome_type,
                "description": o.description,
                "bureau": o.bureau,
                "achieved_date": o.achieved_date,
                "verified": o.verified,
                "score_before": o.score_before,
                "score_after": o.score_after,
            }
            for o in outcomes
            if o.verified
        ],
        "score_snapshots": snapshots,
        "total_deletions": sum(1 for o in outcomes if o.outcome_type == "deleted" and o.verified),
        "total_verified": sum(1 for o in outcomes if o.verified),
    }


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
    try:
        client = db.query(AegisClient).filter(AegisClient.id == case.client_id).first()
        portal_user = (
            db.query(User).filter(User.id == client.portal_user_id).first()
            if client and client.portal_user_id else None
        )
        if portal_user and client:
            send_case_status_update_email(
                portal_user.email, client.first_name, portal_status, case.case_number
            )
    except Exception as _e:
        print(f"[EMAIL] Case status email failed: {_e}")
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
    try:
        portal_user = (
            db.query(User)
            .join(AegisClient, AegisClient.portal_user_id == User.id)
            .filter(AegisClient.id == doc.client_id)
            .first()
        )
        client = db.query(AegisClient).filter(AegisClient.id == doc.client_id).first()
        if portal_user and client:
            send_document_reviewed_email(
                portal_user.email,
                client.first_name,
                doc.doc_type,
                doc.original_filename or "document",
            )
    except Exception as _e:
        print(f"[EMAIL] Document reviewed email failed: {_e}")
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


# ---------------------------------------------------------------------------
# Service intake — portal clients self-submit for criminal, doc-prep, consulting
# ---------------------------------------------------------------------------

import json as _json

_CLIENT_SLUGS = {"criminal", "document", "consulting", "notary", "credit", "judgment"}

# Checklist generation per division
def _checklist(slug: str, intake: dict) -> list[dict]:
    state = intake.get("state", "")
    if slug == "criminal":
        record_type = intake.get("record_type", "")
        items = [
            {"item": "Valid government-issued photo ID (driver's license or state ID)", "required": True},
            {"item": "Court docket printout or case number confirmation", "required": True},
            {"item": "Disposition paperwork (plea, verdict, or dismissal order)", "required": True},
        ]
        if record_type in ("felony", "misdemeanor"):
            items.append({"item": "Arrest record or RAP sheet (obtainable from state SLED or county clerk)", "required": True})
        if state == "SC":
            items.append({"item": "SC SLED background check ($25 — request at sled.sc.gov)", "required": False})
        items.append({"item": "Fingerprint card (if required by your state for expungement petition)", "required": False})
        items.append({"item": "Any probation/parole completion documents (if applicable)", "required": False})
        return items

    if slug == "document":
        doc_type = intake.get("doc_type", "")
        base = [{"item": "Valid photo ID of all signing parties", "required": True}]
        extras = {
            "llc_formation": [
                {"item": "Desired LLC name (we'll verify availability)", "required": True},
                {"item": "Registered agent name and address in formation state", "required": True},
                {"item": "Member names, addresses, and ownership percentages", "required": True},
                {"item": "Business purpose description (one sentence)", "required": False},
            ],
            "operating_agreement": [
                {"item": "LLC formation documents (Articles of Organization)", "required": True},
                {"item": "All member names, addresses, and ownership stakes", "required": True},
                {"item": "Management structure (member-managed vs. manager-managed)", "required": True},
            ],
            "demand_letter": [
                {"item": "Details of the debt or dispute (amount, date, parties)", "required": True},
                {"item": "Any contracts, invoices, or receipts related to the matter", "required": True},
                {"item": "Correspondence history (prior emails, texts, or letters)", "required": False},
            ],
            "power_of_attorney": [
                {"item": "Principal's full legal name and address", "required": True},
                {"item": "Agent's full legal name and address", "required": True},
                {"item": "Specific powers to be granted (financial, medical, general)", "required": True},
            ],
            "lease_agreement": [
                {"item": "Property address and description", "required": True},
                {"item": "Landlord and tenant full legal names", "required": True},
                {"item": "Lease term, monthly rent, and security deposit amounts", "required": True},
                {"item": "Pet policy, utilities, and any special terms", "required": False},
            ],
        }
        return base + extras.get(doc_type, [
            {"item": "Any reference documents or examples for the requested document", "required": False},
            {"item": "Names and addresses of all parties involved", "required": True},
        ])

    if slug == "consulting":
        goals = intake.get("goals", [])
        items = [
            {"item": "Current business plan or executive summary (if exists)", "required": False},
            {"item": "Most recent financial statements or projections", "required": False},
        ]
        if "entity_setup" in goals or "compliance" in goals:
            items.append({"item": "Existing formation documents (EIN, Articles, Operating Agreement)", "required": False})
        if "credit_building" in goals:
            items.append({"item": "Business credit report (Nav, Dun & Bradstreet, or Experian Business)", "required": False})
        if "growth_plan" in goals:
            items.append({"item": "Current revenue figures and top 3 customer/revenue sources", "required": False})
        items.append({"item": "List of your top 3 immediate business challenges", "required": True})
        return items

    if slug == "judgment":
        case_type = intake.get("case_type", "")
        has_judgment = intake.get("has_judgment", "")
        items = [
            {"item": "Valid government-issued photo ID", "required": True},
        ]
        if has_judgment == "yes":
            items += [
                {"item": "Certified copy of the court judgment (obtainable from the clerk of court)", "required": True},
                {"item": "Proof of service on the judgment debtor", "required": True},
                {"item": "Any abstract of judgment filed with the county recorder", "required": False},
            ]
        elif has_judgment == "no":
            items += [
                {"item": "Signed contracts, invoices, or promissory notes evidencing the debt", "required": True},
                {"item": "Correspondence history with the debtor (emails, texts, letters)", "required": True},
                {"item": "Any prior collection attempts or demand letters", "required": False},
            ]
        elif has_judgment == "partial":
            items += [
                {"item": "Original court judgment and satisfaction records showing partial payment", "required": True},
                {"item": "Ledger showing payments received and remaining balance", "required": True},
            ]
        if case_type in ("asset_tracing", "divorce_assets"):
            items.append({"item": "Any known bank accounts, property addresses, or employer information for the debtor", "required": False})
            items.append({"item": "Documentation of suspected asset transfers or fraudulent conveyances", "required": False})
        if case_type == "landlord_tenant":
            items += [
                {"item": "Signed lease agreement", "required": True},
                {"item": "Move-out inspection report and security deposit accounting", "required": False},
                {"item": "Eviction judgment or small claims judgment (if obtained)", "required": False},
            ]
        if case_type == "estate_recovery":
            items += [
                {"item": "Letters testamentary or letters of administration (if appointed)", "required": True},
                {"item": "Death certificate of decedent", "required": True},
                {"item": "List of known estate assets and their approximate values", "required": False},
            ]
        items.append({"item": "List of known debtor addresses, phone numbers, or social security number (last 4 digits)", "required": False})
        return items

    return [{"item": "Contact us to discuss your specific needs", "required": True}]


def _next_steps(slug: str, intake: dict) -> list[str]:
    if slug == "criminal":
        state = intake.get("state", "")
        record_type = intake.get("record_type", "")
        steps = [
            "We will review your intake information within 1-2 business days.",
            "Our team will perform an eligibility pre-check based on your state's expungement statutes.",
        ]
        if state == "SC":
            if record_type == "arrest":
                steps.append("SC Code § 17-1-40 allows expungement of arrest records with no conviction — strong eligibility likely.")
            elif record_type == "misdemeanor":
                steps.append("SC first-offense misdemeanor expungement requires 3-5 years post-completion with no additional offenses.")
            elif record_type == "felony":
                steps.append("Felony expungement in SC is limited — we'll assess specific charge eligibility individually.")
        steps.append("Once eligibility is confirmed, we'll prepare your petition and send you a signing appointment.")
        steps.append("After signing, we file with the appropriate court(s) and track the outcome.")
        return steps

    if slug == "document":
        return [
            "We will review your intake and confirm the document scope within 1 business day.",
            "Our team will follow up with any clarifying questions before drafting begins.",
            "You will receive a draft for your review within the agreed turnaround window.",
            "Upon approval, we deliver the finalized, ready-to-sign document.",
        ]

    if slug == "consulting":
        return [
            "Your intake has been received. We'll review your goals and match you with the right advisory track.",
            "Expect a call or email within 1 business day to schedule your initial consultation.",
            "During the consultation we'll build your 90-day action plan.",
            "You'll receive a written plan summary within 48 hours of your consultation.",
        ]

    if slug == "judgment":
        has_judgment = intake.get("has_judgment", "")
        steps = [
            "We'll review your case details and assess recoverability within 1 business day.",
            "Our team will contact you to discuss your recovery strategy, estimated timeline, and fee structure.",
        ]
        if has_judgment == "yes":
            steps.append("We'll verify the judgment is still active and identify all available enforcement remedies (wage garnishment, bank levy, property lien).")
            steps.append("We begin asset location immediately — bank accounts, employer, real property, and vehicles.")
        elif has_judgment == "no":
            steps.append("We'll evaluate whether to pursue a demand letter, small claims, or full litigation referral to collect your debt.")
            steps.append("If litigation is the right path, we'll connect you with the appropriate counsel and prepare your supporting documentation.")
        steps.append("You'll receive a status update each time we take action on your case, and all recovered funds are disbursed to you promptly.")
        return steps

    return ["We'll be in touch within 1-2 business days to discuss next steps."]


class ServiceIntakeCreate(BaseModel):
    division_slug: str
    intake_data: dict
    title: Optional[str] = None


def _serialize(d: dict) -> str:
    return _json.dumps(d)


def _gen_sc_number(slug: str, sc_id: int) -> str:
    prefix = slug[:3].upper()
    return f"SVC-{prefix}-{datetime.utcnow().year}-{sc_id:04d}"


@router.post("/service-intake")
def create_service_intake(
    data: ServiceIntakeCreate,
    db: Session = Depends(get_db),
    client: AegisClient = Depends(get_portal_client),
):
    """Portal client self-submits a service intake. Returns case number + checklist."""
    if data.division_slug not in _CLIENT_SLUGS:
        raise HTTPException(422, f"Service '{data.division_slug}' not available for self-service intake.")

    title = data.title or {
        "criminal": "Criminal Record Relief",
        "document": "Document Preparation",
        "consulting": "Business Consulting",
        "notary": "Mobile Notary Request",
        "credit": "Credit Restoration",
        "judgment": "Judgment & Asset Recovery",
    }.get(data.division_slug, data.division_slug.title())

    sc = ServiceCase(
        client_id=client.id,
        division_slug=data.division_slug,
        title=title,
        intake_data=_serialize(data.intake_data),
        status="intake",
        case_number="SVC-PENDING",
    )
    db.add(sc)
    db.flush()
    sc.case_number = _gen_sc_number(data.division_slug, sc.id)
    db.commit()
    db.refresh(sc)

    checklist = _checklist(data.division_slug, data.intake_data)
    next_steps = _next_steps(data.division_slug, data.intake_data)

    return {
        "case_number": sc.case_number,
        "id": sc.id,
        "division_slug": sc.division_slug,
        "title": sc.title,
        "status": sc.status,
        "checklist": checklist,
        "next_steps": next_steps,
        "created_at": sc.created_at.isoformat() if sc.created_at else None,
    }


@router.get("/service-cases")
def portal_service_cases(
    db: Session = Depends(get_db),
    client: AegisClient = Depends(get_portal_client),
):
    """Return all service cases for the authenticated portal client."""
    cases = (
        db.query(ServiceCase)
        .filter(ServiceCase.client_id == client.id)
        .order_by(ServiceCase.id.desc())
        .all()
    )
    return [
        {
            "id": sc.id,
            "case_number": sc.case_number,
            "division_slug": sc.division_slug,
            "title": sc.title,
            "status": sc.status,
            "created_at": sc.created_at.isoformat() if sc.created_at else None,
        }
        for sc in cases
    ]
