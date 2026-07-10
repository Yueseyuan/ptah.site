"""Operator client management — all queries run inside op_{slug} schema."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional

from app.dependencies import get_current_staff, require_staff_any
from app.models import OpClient

router = APIRouter(prefix="/api/clients", tags=["clients"])


class ClientCreate(BaseModel):
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: str = "SC"
    zip_code: Optional[str] = None
    dob: Optional[str] = None
    ssn_last4: Optional[str] = None
    notes: Optional[str] = None


def _out(c: OpClient) -> dict:
    return {
        "id": c.id, "first_name": c.first_name, "last_name": c.last_name,
        "email": c.email, "phone": c.phone, "address": c.address,
        "city": c.city, "state": c.state, "zip_code": c.zip_code,
        "dob": c.dob, "ssn_last4": c.ssn_last4, "notes": c.notes,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


@router.get("/")
def list_clients(
    search: Optional[str] = None,
    ctx: dict = Depends(require_staff_any),
):
    db: Session = ctx["db"]
    q = db.query(OpClient)
    if search:
        s = f"%{search.lower()}%"
        q = q.filter(
            func.lower(OpClient.first_name + " " + OpClient.last_name).like(s) |
            func.lower(OpClient.email).like(s)
        )
    return [_out(c) for c in q.order_by(OpClient.id.desc()).all()]


@router.post("/", status_code=201)
def create_client(data: ClientCreate, ctx: dict = Depends(require_staff_any)):
    db: Session = ctx["db"]
    if ctx["role"] == "readonly":
        raise HTTPException(403, "Read-only staff cannot create clients")
    client = OpClient(**data.model_dump())
    db.add(client)
    db.commit()
    db.refresh(client)
    return _out(client)


@router.get("/{client_id}")
def get_client(client_id: int, ctx: dict = Depends(require_staff_any)):
    db: Session = ctx["db"]
    c = db.query(OpClient).filter(OpClient.id == client_id).first()
    if not c:
        raise HTTPException(404, "Client not found")
    return _out(c)


@router.put("/{client_id}")
def update_client(client_id: int, data: ClientCreate, ctx: dict = Depends(require_staff_any)):
    db: Session = ctx["db"]
    if ctx["role"] == "readonly":
        raise HTTPException(403, "Read-only staff cannot edit clients")
    c = db.query(OpClient).filter(OpClient.id == client_id).first()
    if not c:
        raise HTTPException(404, "Client not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(c, k, v)
    db.commit()
    db.refresh(c)
    return _out(c)
