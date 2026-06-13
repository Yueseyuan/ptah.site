from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from app.database import get_db
from app.models import Client, AuditLog
from app.auth import get_current_user

router = APIRouter(prefix="/api/clients", tags=["clients"])


class ClientCreate(BaseModel):
    first_name: str
    last_name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = "SC"
    zip_code: Optional[str] = None
    dob: Optional[str] = None
    ssn_last4: Optional[str] = None
    notes: Optional[str] = None


class ClientUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
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

    class Config:
        from_attributes = True


@router.get("/", response_model=List[ClientOut])
def list_clients(
    search: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = db.query(Client)
    if search:
        like = f"%{search}%"
        q = q.filter(
            Client.first_name.ilike(like)
            | Client.last_name.ilike(like)
            | Client.email.ilike(like)
            | Client.phone.ilike(like)
        )
    return q.order_by(Client.last_name).offset(skip).limit(limit).all()


@router.post("/", response_model=ClientOut, status_code=201)
def create_client(
    payload: ClientCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # Validate SSN last 4 if provided
    if payload.ssn_last4 and (not payload.ssn_last4.isdigit() or len(payload.ssn_last4) != 4):
        raise HTTPException(status_code=422, detail="ssn_last4 must be exactly 4 digits")

    client = Client(**payload.model_dump())
    db.add(client)
    db.commit()
    db.refresh(client)

    log = AuditLog(
        user_id=current_user.id,
        action="create_client",
        resource_type="client",
        resource_id=client.id,
        details=f"{client.first_name} {client.last_name}",
    )
    db.add(log)
    db.commit()

    return client


@router.get("/{client_id}", response_model=ClientOut)
def get_client(
    client_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@router.patch("/{client_id}", response_model=ClientOut)
def update_client(
    client_id: int,
    payload: ClientUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    updates = payload.model_dump(exclude_unset=True)
    if "ssn_last4" in updates and updates["ssn_last4"]:
        if not updates["ssn_last4"].isdigit() or len(updates["ssn_last4"]) != 4:
            raise HTTPException(status_code=422, detail="ssn_last4 must be exactly 4 digits")

    for key, val in updates.items():
        setattr(client, key, val)

    db.commit()
    db.refresh(client)

    log = AuditLog(
        user_id=current_user.id,
        action="update_client",
        resource_type="client",
        resource_id=client_id,
        details=str(list(updates.keys())),
    )
    db.add(log)
    db.commit()

    return client


@router.delete("/{client_id}", status_code=204)
def delete_client(
    client_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    db.delete(client)

    log = AuditLog(
        user_id=current_user.id,
        action="delete_client",
        resource_type="client",
        resource_id=client_id,
        details=f"{client.first_name} {client.last_name}",
    )
    db.add(log)
    db.commit()
