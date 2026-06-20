import json
import os
from typing import List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models import Case, Client, Document, AuditLog
from app.auth import get_current_user
from app.services.doc_generator import generate as gen_doc, available_documents

router = APIRouter(prefix="/api/documents", tags=["documents"])


class DocumentGenerateRequest(BaseModel):
    case_id: int
    document_type: str
    extra_data: Optional[dict] = None


class DocumentOut(BaseModel):
    id: int
    case_id: int
    document_type: str
    label: Optional[str]
    file_path: Optional[str]
    pdf_path: Optional[str]
    status: str
    esign_provider: Optional[str]
    esign_envelope_id: Optional[str]

    class Config:
        from_attributes = True


@router.get("/types")
def list_document_types():
    """List available document types by division."""
    return available_documents()


@router.post("/generate", response_model=DocumentOut, status_code=201)
def generate_document(
    payload: DocumentGenerateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    case = db.query(Case).filter(Case.id == payload.case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    client = db.query(Client).filter(Client.id == case.client_id).first()
    intake_data = json.loads(case.intake_data or "{}")

    doc_data = {
        "client_id": client.id,
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
        **intake_data,
        **(payload.extra_data or {}),
    }

    try:
        result = gen_doc(payload.document_type, doc_data)
        paths = result if isinstance(result, list) else [result]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document generation failed: {str(e)}")

    documents = []
    for path in paths:
        label = os.path.basename(path).split("_")[0].replace("-", " ").title()
        doc = Document(
            case_id=payload.case_id,
            document_type=payload.document_type,
            label=payload.document_type.replace("_", " ").title(),
            file_path=path,
            status="draft",
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        documents.append(doc)

        log = AuditLog(
            user_id=current_user.id,
            action="generate_document",
            resource_type="document",
            resource_id=doc.id,
            details=f"type={payload.document_type}",
        )
        db.add(log)

    db.commit()

    # Auto-convert first doc to PDF in background
    if documents:
        background_tasks.add_task(_convert_to_pdf, documents[0].id)

    return documents[0]


def _convert_to_pdf(doc_id: int):
    from app.services.pdf_generator import docx_to_pdf

    db = None
    try:
        from app.database import SessionLocal
        db = SessionLocal()
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if doc and doc.file_path and doc.file_path.endswith(".docx"):
            pdf = docx_to_pdf(doc.file_path)
            if pdf:
                doc.pdf_path = pdf
                db.commit()
    except Exception:
        pass
    finally:
        if db:
            db.close()


@router.get("/", response_model=List[DocumentOut])
def list_documents(
    case_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = db.query(Document)
    if case_id:
        q = q.filter(Document.case_id == case_id)
    if status:
        q = q.filter(Document.status == status)
    return q.order_by(Document.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/{doc_id}", response_model=DocumentOut)
def get_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.get("/{doc_id}/download")
def download_document(
    doc_id: int,
    fmt: str = Query("docx", pattern="^(docx|pdf)$"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if fmt == "pdf":
        path = doc.pdf_path
        media_type = "application/pdf"
    else:
        path = doc.file_path
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"{fmt.upper()} file not available")

    filename = os.path.basename(path)
    log = AuditLog(
        user_id=current_user.id,
        action="download_document",
        resource_type="document",
        resource_id=doc_id,
        details=f"format={fmt}",
    )
    db.add(log)
    db.commit()

    return FileResponse(path, media_type=media_type, filename=filename)


@router.patch("/{doc_id}/status")
def update_document_status(
    doc_id: int,
    status: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    valid = {"draft", "pending_signature", "signed", "archived"}
    if status not in valid:
        raise HTTPException(status_code=422, detail=f"Invalid status. Must be one of: {valid}")

    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    doc.status = status
    if status == "signed":
        from datetime import datetime
        doc.signed_at = datetime.utcnow()

    db.commit()
    db.refresh(doc)

    log = AuditLog(
        user_id=current_user.id,
        action="update_document_status",
        resource_type="document",
        resource_id=doc_id,
        details=f"status={status}",
    )
    db.add(log)
    db.commit()

    return {"id": doc_id, "status": doc.status}


@router.post("/{doc_id}/send-for-signature")
def send_for_signature(
    doc_id: int,
    signer_email: str,
    signer_name: str,
    provider: str = Query("dropbox_sign", pattern="^(dropbox_sign|docusign)$"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = doc.pdf_path or doc.file_path
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=400, detail="Document file not available for signing")

    envelope_id = None

    if provider == "dropbox_sign":
        envelope_id = _send_dropbox_sign(file_path, signer_email, signer_name, doc)
    elif provider == "docusign":
        envelope_id = _send_docusign(file_path, signer_email, signer_name, doc)

    if envelope_id:
        doc.esign_provider = provider
        doc.esign_envelope_id = envelope_id
        doc.status = "pending_signature"
        db.commit()

        log = AuditLog(
            user_id=current_user.id,
            action="send_for_signature",
            resource_type="document",
            resource_id=doc_id,
            details=f"provider={provider}, envelope={envelope_id}",
        )
        db.add(log)
        db.commit()

    return {"doc_id": doc_id, "envelope_id": envelope_id, "provider": provider, "status": doc.status}


def _send_dropbox_sign(file_path: str, signer_email: str, signer_name: str, doc: Document):
    import httpx
    from app.config import settings

    if not settings.DROPBOX_SIGN_API_KEY:
        raise HTTPException(status_code=503, detail="Dropbox Sign not configured")

    with open(file_path, "rb") as f:
        file_content = f.read()

    filename = os.path.basename(file_path)
    import base64
    file_b64 = base64.b64encode(file_content).decode()

    payload = {
        "title": doc.label or doc.document_type,
        "subject": f"Please sign: {doc.label or doc.document_type}",
        "message": "Please review and sign the attached document from Cruel & Associates.",
        "signers": [{"email_address": signer_email, "name": signer_name, "order": 0}],
        "files": [{"name": filename, "file_base64": file_b64}],
        "test_mode": 1,
    }

    try:
        resp = httpx.post(
            "https://api.hellosign.com/v3/signature_request/send",
            auth=(settings.DROPBOX_SIGN_API_KEY, ""),
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get("signature_request", {}).get("signature_request_id")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Dropbox Sign error: {str(e)}")


def _send_docusign(file_path: str, signer_email: str, signer_name: str, doc: Document):
    # DocuSign integration stub — requires OAuth token setup
    raise HTTPException(status_code=501, detail="DocuSign integration not yet implemented. Use Dropbox Sign.")
