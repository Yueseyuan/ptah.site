import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models import EvidenceItem
from app.config import settings

router = APIRouter(prefix="/api/evidence", tags=["evidence"])

EVIDENCE_DIR = "evidence_files"


def _out(e: EvidenceItem) -> dict:
    return {
        "id": e.id,
        "case_id": e.case_id,
        "evidence_type": e.evidence_type,
        "title": e.title,
        "description": e.description,
        "file_path": e.file_path,
        "source": e.source,
        "collected_at": e.collected_at,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }


@router.get("/case/{case_id}")
def list_evidence(case_id: int, db: Session = Depends(get_db)):
    return [_out(e) for e in db.query(EvidenceItem).filter(EvidenceItem.case_id == case_id).all()]


@router.post("/case/{case_id}/upload")
async def upload_evidence(
    case_id: int,
    title: str = Form(...),
    evidence_type: str = Form("correspondence"),
    source: str = Form(""),
    collected_at: str = Form(""),
    description: str = Form(""),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    os.makedirs(EVIDENCE_DIR, exist_ok=True)
    safe_name = f"case_{case_id}_{file.filename}"
    file_path = os.path.join(EVIDENCE_DIR, safe_name)
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    item = EvidenceItem(
        case_id=case_id,
        evidence_type=evidence_type,
        title=title,
        description=description,
        file_path=file_path,
        source=source,
        collected_at=collected_at,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _out(item)


class EvidenceCreate(BaseModel):
    case_id: int
    evidence_type: str = "correspondence"
    title: str
    description: Optional[str] = None
    source: Optional[str] = None
    collected_at: Optional[str] = None


@router.post("/")
def create_evidence(data: EvidenceCreate, db: Session = Depends(get_db)):
    item = EvidenceItem(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return _out(item)


@router.delete("/{evidence_id}", status_code=204)
def delete_evidence(evidence_id: int, db: Session = Depends(get_db)):
    e = db.query(EvidenceItem).filter(EvidenceItem.id == evidence_id).first()
    if not e:
        raise HTTPException(404, "Evidence not found")
    db.delete(e)
    db.commit()
