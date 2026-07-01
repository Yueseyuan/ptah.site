"""Attorney referral router."""
import os
from typing import Optional

import anthropic
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import AegisClient, AttorneyReferral, ServiceCase, ServiceDocument, User
from app.services.document_service import (
    generate_pdf_from_text,
    get_client_template_vars,
)

router = APIRouter(prefix="/api/referrals", tags=["referrals"])

_VALID_STATUSES = {"pending", "accepted", "declined", "completed"}
_AI_MODEL = "claude-sonnet-4-6"

LETTER_SYSTEM_PROMPT = (
    "You are a professional document preparer for Cruel & Associates. "
    "Generate attorney referral letters that are formal, concise, and complete. "
    "Return only the letter text — no preamble, no commentary."
)


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class ReferralCreate(BaseModel):
    client_id: int
    service_case_id: Optional[int] = None
    attorney_name: Optional[str] = None
    attorney_firm: Optional[str] = None
    attorney_email: Optional[str] = None
    attorney_phone: Optional[str] = None
    practice_area: Optional[str] = None
    reason: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = "pending"


class ReferralUpdate(BaseModel):
    attorney_name: Optional[str] = None
    attorney_firm: Optional[str] = None
    attorney_email: Optional[str] = None
    attorney_phone: Optional[str] = None
    practice_area: Optional[str] = None
    reason: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _out(ref: AttorneyReferral) -> dict:
    return {
        "id": ref.id,
        "client_id": ref.client_id,
        "service_case_id": ref.service_case_id,
        "attorney_name": ref.attorney_name,
        "attorney_firm": ref.attorney_firm,
        "attorney_email": ref.attorney_email,
        "attorney_phone": ref.attorney_phone,
        "practice_area": ref.practice_area,
        "reason": ref.reason,
        "status": ref.status,
        "referral_letter_path": ref.referral_letter_path,
        "notes": ref.notes,
        "referred_at": ref.referred_at.isoformat() if ref.referred_at else None,
    }


def _api_key() -> str:
    return settings.ANTHROPIC_API_KEY or os.environ.get("ANTHROPIC_API_KEY", "")


def _build_letter_prompt(
    client: AegisClient,
    referral: AttorneyReferral,
    case: Optional[ServiceCase],
) -> str:
    parts = ["Generate a professional attorney referral letter with the following details.\n"]

    parts.append("CLIENT INFORMATION:")
    parts.append(f"  Name:    {client.first_name or ''} {client.last_name or ''}".strip())
    if client.address:
        parts.append(f"  Address: {client.address}, {client.city or ''}, {client.state or ''} {client.zip_code or ''}".strip(", "))
    if client.email:
        parts.append(f"  Email:   {client.email}")
    if client.phone:
        parts.append(f"  Phone:   {client.phone}")

    parts.append("\nREFERRAL DETAILS:")
    if referral.attorney_name:
        parts.append(f"  Referring to Attorney: {referral.attorney_name}")
    if referral.attorney_firm:
        parts.append(f"  Firm:                  {referral.attorney_firm}")
    if referral.attorney_email:
        parts.append(f"  Attorney Email:        {referral.attorney_email}")
    if referral.attorney_phone:
        parts.append(f"  Attorney Phone:        {referral.attorney_phone}")
    if referral.practice_area:
        parts.append(f"  Practice Area:         {referral.practice_area}")
    if referral.reason:
        parts.append(f"  Reason for Referral:\n    {referral.reason}")

    if case:
        parts.append("\nASSOCIATED SERVICE CASE:")
        parts.append(f"  Case Number:   {case.case_number or 'N/A'}")
        parts.append(f"  Division:      {case.division_slug or 'N/A'}")
        if case.title:
            parts.append(f"  Case Title:    {case.title}")
        if case.notes:
            parts.append(f"  Case Notes:    {case.notes}")

    parts.append(
        "\nWrite a formal referral letter on behalf of Cruel & Associates. "
        "The letter should introduce the client, explain the reason for referral, "
        "and include all relevant case details. "
        "End with a professional closing from Cruel & Associates."
    )

    return "\n".join(parts)


def _call_ai(prompt: str) -> str:
    client = anthropic.Anthropic(api_key=_api_key())
    response = client.messages.create(
        model=_AI_MODEL,
        max_tokens=2048,
        system=LETTER_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/")
def list_referrals(
    client_id: Optional[int] = None,
    status: Optional[str] = None,
    practice_area: Optional[str] = None,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """List attorney referrals with optional filters: client_id, status, practice_area."""
    q = db.query(AttorneyReferral)
    if client_id is not None:
        q = q.filter(AttorneyReferral.client_id == client_id)
    if status is not None:
        q = q.filter(AttorneyReferral.status == status)
    if practice_area is not None:
        q = q.filter(AttorneyReferral.practice_area == practice_area)
    return [_out(r) for r in q.order_by(AttorneyReferral.id.desc()).all()]


@router.post("/", status_code=201)
def create_referral(
    data: ReferralCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Create a new attorney referral."""
    client = db.query(AegisClient).filter(AegisClient.id == data.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if data.service_case_id is not None:
        case = db.query(ServiceCase).filter(ServiceCase.id == data.service_case_id).first()
        if not case:
            raise HTTPException(status_code=404, detail="Service case not found")

    if data.status and data.status not in _VALID_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status '{data.status}'. Must be one of: {', '.join(sorted(_VALID_STATUSES))}",
        )

    ref = AttorneyReferral(**data.model_dump())
    db.add(ref)
    db.commit()
    db.refresh(ref)
    return _out(ref)


@router.get("/{referral_id}")
def get_referral(
    referral_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Retrieve a single attorney referral by ID."""
    ref = db.query(AttorneyReferral).filter(AttorneyReferral.id == referral_id).first()
    if not ref:
        raise HTTPException(status_code=404, detail="Referral not found")
    return _out(ref)


@router.put("/{referral_id}")
def update_referral(
    referral_id: int,
    data: ReferralUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Update an attorney referral."""
    ref = db.query(AttorneyReferral).filter(AttorneyReferral.id == referral_id).first()
    if not ref:
        raise HTTPException(status_code=404, detail="Referral not found")

    if data.status is not None and data.status not in _VALID_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status '{data.status}'. Must be one of: {', '.join(sorted(_VALID_STATUSES))}",
        )

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(ref, field, value)

    db.commit()
    db.refresh(ref)
    return _out(ref)


@router.delete("/{referral_id}", status_code=204)
def delete_referral(
    referral_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Delete an attorney referral by ID."""
    ref = db.query(AttorneyReferral).filter(AttorneyReferral.id == referral_id).first()
    if not ref:
        raise HTTPException(status_code=404, detail="Referral not found")
    db.delete(ref)
    db.commit()


@router.post("/{referral_id}/generate-letter", status_code=201)
def generate_referral_letter(
    referral_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Use AI to generate a referral letter for this referral.

    Calls the Anthropic API with client info + referral details, saves the
    result as a ServiceDocument, writes a PDF to disk, and returns the
    generated letter content alongside the created document record id.
    """
    ref = db.query(AttorneyReferral).filter(AttorneyReferral.id == referral_id).first()
    if not ref:
        raise HTTPException(status_code=404, detail="Referral not found")

    client = db.query(AegisClient).filter(AegisClient.id == ref.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found for referral")

    case: Optional[ServiceCase] = None
    if ref.service_case_id is not None:
        case = db.query(ServiceCase).filter(ServiceCase.id == ref.service_case_id).first()

    # Build AI prompt
    prompt = _build_letter_prompt(client, ref, case)

    # Call AI
    ai_generated = False
    if _api_key():
        try:
            letter_content = _call_ai(prompt)
            ai_generated = True
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"AI letter generation failed: {exc}")
    else:
        # Fallback stub when no API key is configured
        full_name = f"{client.first_name or ''} {client.last_name or ''}".strip()
        attorney_info = ref.attorney_name or "the referred attorney"
        letter_content = (
            f"RE: Referral of {full_name}\n\n"
            f"Dear {attorney_info},\n\n"
            f"We are writing on behalf of {full_name} to refer this client to your office "
            f"regarding: {ref.reason or 'the matter described in our intake notes'}.\n\n"
            f"[AI generation unavailable — ANTHROPIC_API_KEY not configured]\n\n"
            f"Please do not hesitate to contact us with any questions.\n\n"
            f"Sincerely,\nCruel & Associates"
        )

    # Determine PDF output path
    letter_title = (
        f"Attorney Referral Letter — "
        f"{client.first_name or ''} {client.last_name or ''}".strip(" — ")
    )
    reports_dir = settings.REPORTS_DIR or "generated_reports"
    pdf_filename = f"referral_letter_{referral_id}.pdf"
    pdf_path = os.path.join(reports_dir, "referrals", pdf_filename)

    try:
        saved_path = generate_pdf_from_text(
            title=letter_title,
            content=letter_content,
            output_path=pdf_path,
        )
    except Exception as exc:
        # PDF generation failure is non-fatal; we still save the text content
        saved_path = None

    # Persist as a ServiceDocument
    template_vars = get_client_template_vars(client, case)
    doc = ServiceDocument(
        service_case_id=ref.service_case_id,
        client_id=ref.client_id,
        template_id=None,
        division_slug=(case.division_slug if case else "criminal"),
        title=letter_title,
        document_type="referral_letter",
        content=letter_content,
        file_path=saved_path,
        status="draft",
        ai_generated=ai_generated,
    )
    db.add(doc)

    # Update the referral with the letter path
    if saved_path:
        ref.referral_letter_path = saved_path

    db.commit()
    db.refresh(doc)

    return {
        "referral_id": referral_id,
        "document_id": doc.id,
        "title": letter_title,
        "content": letter_content,
        "file_path": saved_path,
        "ai_generated": ai_generated,
    }
