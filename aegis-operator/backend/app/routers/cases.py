"""Operator case management — all queries run inside op_{slug} schema."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.dependencies import require_staff_any
from app.models import OpCase, OpCaseNote

router = APIRouter(prefix="/api/cases", tags=["cases"])


class CaseCreate(BaseModel):
    client_id: int
    case_number: str
    status: str = "intake"
    goal: Optional[str] = None
    notes: Optional[str] = None
    assigned_to: Optional[str] = None


class CaseUpdate(BaseModel):
    status: Optional[str] = None
    goal: Optional[str] = None
    notes: Optional[str] = None
    assigned_to: Optional[str] = None


class NoteCreate(BaseModel):
    content: str


def _case_out(c: OpCase) -> dict:
    return {
        "id": c.id,
        "case_number": c.case_number,
        "client_id": c.client_id,
        "status": c.status,
        "goal": c.goal,
        "notes": c.notes,
        "assigned_to": c.assigned_to,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }


def _note_out(n: OpCaseNote) -> dict:
    return {
        "id": n.id,
        "case_id": n.case_id,
        "author": n.author,
        "content": n.content,
        "created_at": n.created_at.isoformat() if n.created_at else None,
    }


@router.get("")
def list_cases(
    client_id: Optional[int] = None,
    status: Optional[str] = None,
    ctx: dict = Depends(require_staff_any),
):
    db: Session = ctx["db"]
    q = db.query(OpCase)
    if client_id:
        q = q.filter(OpCase.client_id == client_id)
    if status:
        q = q.filter(OpCase.status == status)
    return [_case_out(c) for c in q.order_by(OpCase.id.desc()).limit(100).all()]


@router.post("", status_code=201)
def create_case(data: CaseCreate, ctx: dict = Depends(require_staff_any)):
    db: Session = ctx["db"]
    if ctx["role"] == "readonly":
        raise HTTPException(403, "Read-only staff cannot create cases")
    case = OpCase(**data.model_dump())
    db.add(case)
    db.commit()
    db.refresh(case)
    return _case_out(case)


@router.get("/{case_id}")
def get_case(case_id: int, ctx: dict = Depends(require_staff_any)):
    db: Session = ctx["db"]
    c = db.query(OpCase).filter(OpCase.id == case_id).first()
    if not c:
        raise HTTPException(404, "Case not found")
    return _case_out(c)


@router.patch("/{case_id}")
def update_case(case_id: int, data: CaseUpdate, ctx: dict = Depends(require_staff_any)):
    db: Session = ctx["db"]
    if ctx["role"] == "readonly":
        raise HTTPException(403, "Read-only staff cannot edit cases")
    c = db.query(OpCase).filter(OpCase.id == case_id).first()
    if not c:
        raise HTTPException(404, "Case not found")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(c, k, v)
    db.commit()
    db.refresh(c)
    return _case_out(c)


@router.get("/{case_id}/notes")
def list_notes(case_id: int, ctx: dict = Depends(require_staff_any)):
    db: Session = ctx["db"]
    notes = db.query(OpCaseNote).filter(OpCaseNote.case_id == case_id).order_by(OpCaseNote.id).all()
    return [_note_out(n) for n in notes]


@router.post("/{case_id}/notes", status_code=201)
def add_note(case_id: int, data: NoteCreate, ctx: dict = Depends(require_staff_any)):
    db: Session = ctx["db"]
    note = OpCaseNote(case_id=case_id, author=str(ctx["staff_id"]), content=data.content)
    db.add(note)
    db.commit()
    db.refresh(note)
    return _note_out(note)
