from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.dependencies import get_current_notary
from app.models import NotaryProfile

router = APIRouter(prefix="/api/profile", tags=["profile"])


class ProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    license_number: Optional[str] = None
    license_state: Optional[str] = None
    license_expires: Optional[str] = None


def _profile_dict(n: NotaryProfile) -> dict:
    return {
        "id": n.id,
        "first_name": n.first_name,
        "last_name": n.last_name,
        "email": n.email,
        "phone": n.phone,
        "license_number": n.license_number,
        "license_state": n.license_state,
        "license_expires": n.license_expires,
        "is_active": bool(n.is_active),
        "created_at": n.created_at.isoformat() if n.created_at else None,
    }


@router.get("/me")
def get_me(notary: NotaryProfile = Depends(get_current_notary)):
    return _profile_dict(notary)


@router.patch("/me")
def update_me(
    body: ProfileUpdate,
    notary: NotaryProfile = Depends(get_current_notary),
    db: Session = Depends(get_db),
):
    if body.first_name is not None:
        notary.first_name = body.first_name
    if body.last_name is not None:
        notary.last_name = body.last_name
    if body.phone is not None:
        notary.phone = body.phone
    if body.license_number is not None:
        notary.license_number = body.license_number
    if body.license_state is not None:
        notary.license_state = body.license_state.upper()
    if body.license_expires is not None:
        notary.license_expires = body.license_expires
    db.commit()
    db.refresh(notary)
    return _profile_dict(notary)
