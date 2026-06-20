from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models import AegisClient
from app.dependencies import get_current_user
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


@router.get("/{client_id}")
def get_client(client_id: int, db: Session = Depends(get_db)):
    client = db.query(AegisClient).filter(AegisClient.id == client_id).first()
    if not client:
        raise HTTPException(404, "Client not found")
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
