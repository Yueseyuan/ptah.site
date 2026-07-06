from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models import AegisClient
from app.dependencies import get_current_user, require_admin
from app.models import User

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


class ClientOut(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: Optional[str]
    phone: Optional[str]
    address: Optional[str]
    city: Optional[str]
    state: Optional[str]
    zip_code: Optional[str]
    dob: Optional[str]
    ssn_last4: Optional[str]
    notes: Optional[str]
    created_at: Optional[str]

    class Config:
        from_attributes = True


def _out(c: AegisClient) -> dict:
    return {
        "id": c.id,
        "first_name": c.first_name,
        "last_name": c.last_name,
        "email": c.email,
        "phone": c.phone,
        "address": c.address,
        "city": c.city,
        "state": c.state,
        "zip_code": c.zip_code,
        "dob": c.dob,
        "ssn_last4": c.ssn_last4,
        "notes": c.notes,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


@router.get("/")
def list_clients(db: Session = Depends(get_db)):
    return [_out(c) for c in db.query(AegisClient).order_by(AegisClient.id.desc()).all()]


@router.post("/", status_code=201)
def create_client(data: ClientCreate, db: Session = Depends(get_db)):
    client = AegisClient(**data.model_dump())
    db.add(client)
    db.commit()
    db.refresh(client)
    return _out(client)


@router.get("/search")
def search_clients(q: str = "", db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    """Search clients by name, email, or SSN last4."""
    if not q or len(q) < 2:
        return []
    q_lower = f"%{q.lower()}%"
    results = db.query(AegisClient).filter(
        (func.lower(AegisClient.first_name + ' ' + AegisClient.last_name).like(q_lower)) |
        (func.lower(AegisClient.email).like(q_lower)) |
        (AegisClient.ssn_last4.like(f"%{q}%"))
    ).limit(20).all()
    return [_out(c) for c in results]


@router.get("/{client_id}")
def get_client(client_id: int, db: Session = Depends(get_db)):
    client = db.query(AegisClient).filter(AegisClient.id == client_id).first()
    if not client:
        raise HTTPException(404, "Client not found")
    return _out(client)


@router.post("/admin/merge", include_in_schema=False)
def merge_clients(
    keep_id: int,
    delete_id: int,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin utility: re-point all child records from delete_id → keep_id, then delete delete_id."""
    keep = db.query(AegisClient).filter(AegisClient.id == keep_id).first()
    drop = db.query(AegisClient).filter(AegisClient.id == delete_id).first()
    if not keep:
        raise HTTPException(404, f"Client {keep_id} not found")
    if not drop:
        raise HTTPException(404, f"Client {delete_id} not found")

    tables = [
        "aegis_cases", "court_records", "client_documents", "service_cases",
        "service_documents", "appointments", "service_invoices",
        "attorney_referrals", "notary_logs",
    ]
    moved = {}
    for table in tables:
        try:
            result = db.execute(
                text(f"UPDATE {table} SET client_id = :keep WHERE client_id = :drop"),
                {"keep": keep_id, "drop": delete_id},
            )
            moved[table] = result.rowcount
        except Exception as exc:
            moved[table] = f"skipped ({exc})"

    db.delete(drop)
    db.commit()
    return {"merged_into": keep_id, "deleted": delete_id, "rows_moved": moved}


@router.delete("/admin/delete/{client_id}", include_in_schema=False)
def delete_client(
    client_id: int,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin utility: hard-delete a client and all their child records."""
    client = db.query(AegisClient).filter(AegisClient.id == client_id).first()
    if not client:
        raise HTTPException(404, f"Client {client_id} not found")

    tables = [
        "aegis_cases", "court_records", "client_documents", "service_cases",
        "service_documents", "appointments", "service_invoices",
        "attorney_referrals", "notary_logs",
    ]
    deleted = {}
    for table in tables:
        try:
            result = db.execute(
                text(f"DELETE FROM {table} WHERE client_id = :id"),
                {"id": client_id},
            )
            deleted[table] = result.rowcount
        except Exception as exc:
            deleted[table] = f"skipped ({exc})"

    db.delete(client)
    db.commit()
    return {"deleted_client": client_id, "child_rows_deleted": deleted}


@router.put("/{client_id}")
def update_client(client_id: int, data: ClientCreate, db: Session = Depends(get_db)):
    client = db.query(AegisClient).filter(AegisClient.id == client_id).first()
    if not client:
        raise HTTPException(404, "Client not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(client, k, v)
    db.commit()
    db.refresh(client)
    return _out(client)
