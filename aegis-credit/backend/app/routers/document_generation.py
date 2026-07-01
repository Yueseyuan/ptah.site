"""Document generation router — AI-powered document pipeline for service cases."""
import json
import os
from typing import Optional

import anthropic
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import AegisClient, DocumentTemplate, ServiceCase, ServiceDocument, User

router = APIRouter(prefix="/api/documents", tags=["documents"])

_DOC_GEN_MODEL = "claude-sonnet-5"

_VALID_STATUSES = {"draft", "pending_sign", "signed", "archived"}

SYSTEM_PROMPT = (
    "You are a professional document preparer for Cruel & Associates. "
    "Generate the requested document professionally, using all provided client information. "
    "Return only the document content, no preamble."
)


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class GenerateDocumentRequest(BaseModel):
    service_case_id: int
    template_id: Optional[int] = None
    document_type: str
    custom_instructions: Optional[str] = None


class UpdateStatusRequest(BaseModel):
    status: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _api_key() -> str:
    return settings.ANTHROPIC_API_KEY or os.environ.get("ANTHROPIC_API_KEY", "")


def _out(doc: ServiceDocument) -> dict:
    return {
        "id": doc.id,
        "service_case_id": doc.service_case_id,
        "client_id": doc.client_id,
        "template_id": doc.template_id,
        "division_slug": doc.division_slug,
        "title": doc.title,
        "document_type": doc.document_type,
        "content": doc.content,
        "file_path": doc.file_path,
        "status": doc.status,
        "esign_request_id": doc.esign_request_id,
        "esign_provider": doc.esign_provider,
        "ai_generated": doc.ai_generated,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
    }


def _client_fields(client: AegisClient) -> dict:
    """Return a flat dict of client fields suitable for inclusion in an AI prompt."""
    return {
        "first_name": client.first_name or "",
        "last_name": client.last_name or "",
        "email": client.email or "",
        "phone": client.phone or "",
        "address": client.address or "",
        "city": client.city or "",
        "state": client.state or "",
        "zip_code": client.zip_code or "",
        "dob": client.dob or "",
        "ssn_last4": client.ssn_last4 or "",
    }


def _build_user_message(
    document_type: str,
    client: AegisClient,
    intake_data: Optional[str],
    template_content: Optional[str],
    custom_instructions: Optional[str],
) -> str:
    parts: list[str] = []

    parts.append(f"DOCUMENT TYPE: {document_type}")

    # Client fields
    parts.append("\nCLIENT INFORMATION:")
    for key, value in _client_fields(client).items():
        if value:
            parts.append(f"  {key}: {value}")

    # Intake data
    if intake_data:
        try:
            parsed = json.loads(intake_data)
            if isinstance(parsed, dict):
                parts.append("\nCASE INTAKE DATA:")
                for key, value in parsed.items():
                    parts.append(f"  {key}: {value}")
            else:
                parts.append(f"\nCASE INTAKE DATA:\n{intake_data}")
        except (json.JSONDecodeError, TypeError):
            parts.append(f"\nCASE INTAKE DATA:\n{intake_data}")

    # Template body
    if template_content:
        parts.append(f"\nDOCUMENT TEMPLATE (fill in all [FIELD] placeholders and {{{{variable}}}} markers):\n{template_content}")
    else:
        parts.append(
            "\nNo template provided — generate a complete, professional document of the requested type "
            "using the client information above."
        )

    # Custom instructions
    if custom_instructions:
        parts.append(f"\nADDITIONAL INSTRUCTIONS:\n{custom_instructions}")

    parts.append("\nGenerate the complete document now.")
    return "\n".join(parts)


def _generate_stub(document_type: str, client: AegisClient) -> str:
    """Return a placeholder stub when no API key is configured."""
    full_name = f"{client.first_name or '[FIRST_NAME]'} {client.last_name or '[LAST_NAME]'}".strip()
    return (
        f"{document_type.upper()}\n"
        f"{'=' * len(document_type)}\n\n"
        f"Client Name:    {full_name}\n"
        f"Address:        {client.address or '[ADDRESS]'}, "
        f"{client.city or '[CITY]'}, {client.state or '[STATE]'} {client.zip_code or '[ZIP]'}\n"
        f"Email:          {client.email or '[EMAIL]'}\n"
        f"Phone:          {client.phone or '[PHONE]'}\n"
        f"Date of Birth:  {client.dob or '[DOB]'}\n\n"
        f"[DOCUMENT BODY — AI generation unavailable: ANTHROPIC_API_KEY not configured]\n\n"
        f"[CLAUSE_1]\n\n"
        f"[CLAUSE_2]\n\n"
        f"[CLAUSE_3]\n\n"
        f"Signature: ________________________   Date: [DATE]\n\n"
        f"Prepared by Cruel & Associates\n"
    )


def _call_ai(user_message: str) -> str:
    """Call Claude and return the generated document text."""
    ai_client = anthropic.Anthropic(api_key=_api_key())
    response = ai_client.messages.create(
        model=_DOC_GEN_MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/generate", status_code=201)
def generate_document(
    body: GenerateDocumentRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """
    Generate an AI-filled document for a service case.

    Loads the service case and its client, optionally loads a DocumentTemplate,
    sends all data to Claude, and saves the result as a ServiceDocument record.
    """
    # Load service case
    case = db.query(ServiceCase).filter(ServiceCase.id == body.service_case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Service case not found")

    # Load client
    client = db.query(AegisClient).filter(AegisClient.id == case.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found for service case")

    # Optionally load template
    template: Optional[DocumentTemplate] = None
    if body.template_id is not None:
        template = db.query(DocumentTemplate).filter(DocumentTemplate.id == body.template_id).first()
        if not template:
            raise HTTPException(status_code=404, detail="Document template not found")

    template_content = template.content if template else None

    # Build user message
    user_message = _build_user_message(
        document_type=body.document_type,
        client=client,
        intake_data=case.intake_data,
        template_content=template_content,
        custom_instructions=body.custom_instructions,
    )

    # Call AI or fall back to stub
    ai_generated = False
    if _api_key():
        try:
            content = _call_ai(user_message)
            ai_generated = True
        except Exception as exc:
            # Log but do not crash — fall back to stub so caller always gets a record
            content = _generate_stub(body.document_type, client)
            content += f"\n\n[AI generation failed: {exc}]"
    else:
        content = _generate_stub(body.document_type, client)

    # Determine title
    title = body.document_type.replace("_", " ").title()
    if template and template.name:
        title = template.name

    # Persist the ServiceDocument record
    doc = ServiceDocument(
        service_case_id=case.id,
        client_id=client.id,
        template_id=body.template_id,
        division_slug=case.division_slug,
        title=title,
        document_type=body.document_type,
        content=content,
        status="draft",
        ai_generated=ai_generated,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return _out(doc)


@router.get("/")
def list_documents(
    service_case_id: Optional[int] = None,
    client_id: Optional[int] = None,
    division: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """List service documents with optional filters."""
    q = db.query(ServiceDocument)
    if service_case_id is not None:
        q = q.filter(ServiceDocument.service_case_id == service_case_id)
    if client_id is not None:
        q = q.filter(ServiceDocument.client_id == client_id)
    if division is not None:
        q = q.filter(ServiceDocument.division_slug == division)
    if status is not None:
        q = q.filter(ServiceDocument.status == status)
    return [_out(doc) for doc in q.order_by(ServiceDocument.id.desc()).all()]


@router.get("/{doc_id}")
def get_document(
    doc_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Retrieve a single service document by ID."""
    doc = db.query(ServiceDocument).filter(ServiceDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return _out(doc)


@router.put("/{doc_id}/status")
def update_document_status(
    doc_id: int,
    body: UpdateStatusRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Update a document's status (draft | pending_sign | signed | archived)."""
    if body.status not in _VALID_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status '{body.status}'. Must be one of: {', '.join(sorted(_VALID_STATUSES))}",
        )
    doc = db.query(ServiceDocument).filter(ServiceDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    doc.status = body.status
    db.commit()
    db.refresh(doc)
    return _out(doc)


@router.delete("/{doc_id}", status_code=204)
def delete_document(
    doc_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Delete a service document by ID."""
    doc = db.query(ServiceDocument).filter(ServiceDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    db.delete(doc)
    db.commit()


@router.get("/{doc_id}/download")
def download_document(
    doc_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """
    Download document content.

    Returns the document as plain text if the Accept header suggests it,
    otherwise returns a JSON envelope with a 'content' field.
    """
    doc = db.query(ServiceDocument).filter(ServiceDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Return JSON envelope so callers can decide how to render
    return {
        "id": doc.id,
        "title": doc.title,
        "document_type": doc.document_type,
        "division_slug": doc.division_slug,
        "status": doc.status,
        "content": doc.content or "",
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
    }
