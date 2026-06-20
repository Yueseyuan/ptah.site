from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional

from app.database import get_db
from app.models import User, AuditLog
from app.auth import verify_password, hash_password, create_access_token, get_current_user
from app.config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: Optional[str] = "staff"


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool

    class Config:
        from_attributes = True


class TokenOut(BaseModel):
    access_token: str
    token_type: str
    user: UserOut


@router.post("/token", response_model=TokenOut)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    log = AuditLog(user_id=user.id, action="login", resource_type="user", resource_id=user.id)
    db.add(log)
    db.commit()

    return {"access_token": token, "token_type": "bearer", "user": user}


@router.post("/register", response_model=UserOut, status_code=201)
def register(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Only admins can register new users
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    log = AuditLog(
        user_id=current_user.id,
        action="create_user",
        resource_type="user",
        resource_id=user.id,
        details=f"Created user {user.email} with role {user.role}",
    )
    db.add(log)
    db.commit()

    return user


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/setup-admin", response_model=UserOut, status_code=201)
def setup_first_admin(payload: UserCreate, db: Session = Depends(get_db)):
    """One-time endpoint to create the first admin. Disabled once any user exists."""
    if db.query(User).count() > 0:
        raise HTTPException(status_code=403, detail="Setup already complete")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role="admin",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
