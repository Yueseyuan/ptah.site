from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from jose import jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import NotaryProfile

router = APIRouter(prefix="/api/auth", tags=["auth"])
_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _issue_token(notary_id: int) -> str:
    exp = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": str(notary_id), "role": "notary", "exp": exp},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


class NotaryRegister(BaseModel):
    first_name: str
    last_name: str
    email: str
    password: str
    phone: str = ""
    license_number: str = ""
    license_state: str = ""
    license_expires: str = ""


@router.post("/register")
def register(body: NotaryRegister, db: Session = Depends(get_db)):
    if db.query(NotaryProfile).filter(NotaryProfile.email == body.email).first():
        raise HTTPException(409, "Email already registered")
    notary = NotaryProfile(
        first_name=body.first_name,
        last_name=body.last_name,
        email=body.email,
        hashed_password=_pwd.hash(body.password),
        phone=body.phone,
        license_number=body.license_number,
        license_state=body.license_state.upper() if body.license_state else "",
        license_expires=body.license_expires,
    )
    db.add(notary)
    db.commit()
    db.refresh(notary)
    return {"id": notary.id, "email": notary.email, "access_token": _issue_token(notary.id), "token_type": "bearer"}


@router.post("/login")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    notary = db.query(NotaryProfile).filter(NotaryProfile.email == form.username).first()
    if not notary or not _pwd.verify(form.password, notary.hashed_password):
        raise HTTPException(401, "Invalid credentials")
    if not notary.is_active:
        raise HTTPException(403, "Account inactive")
    return {"access_token": _issue_token(notary.id), "token_type": "bearer"}
