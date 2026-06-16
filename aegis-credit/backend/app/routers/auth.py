"""Authentication router — register, login, user management."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.models import User
from app.services.auth_service import hash_password, verify_password, create_access_token
from app.dependencies import get_current_user, require_admin

router = APIRouter(prefix="/api/auth", tags=["auth"])


class UserCreate(BaseModel):
    username: str
    email: str
    full_name: Optional[str] = ""
    password: str
    role: Optional[str] = "investigator"


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str]
    role: str
    is_active: bool

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None


def _out(u: User) -> dict:
    return {
        "id": u.id,
        "username": u.username,
        "email": u.email,
        "full_name": u.full_name,
        "role": u.role,
        "is_active": u.is_active,
    }


@router.post("/register", status_code=201)
def register(
    data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Register a new user.  Requires admin role UNLESS no users exist yet (bootstrap)."""
    user_count = db.query(User).count()
    if user_count > 0 and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required to create users")

    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    role = data.role or "investigator"
    # First user is always admin
    if user_count == 0:
        role = "admin"

    user = User(
        username=data.username,
        email=data.email,
        full_name=data.full_name or "",
        hashed_password=hash_password(data.password),
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _out(user)


@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Authenticate with username + password, return a JWT bearer token."""
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password or ""):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Account is disabled")

    token = create_access_token({"sub": user.username, "role": user.role})
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role,
        "username": user.username,
    }


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    """Return current user info."""
    return _out(current_user)


@router.get("/users")
def list_users(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """List all users (admin only)."""
    return [_out(u) for u in db.query(User).order_by(User.id).all()]


@router.patch("/users/{user_id}")
def update_user(
    user_id: int,
    data: UserUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Update a user's role or active status (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    if data.role is not None:
        user.role = data.role
    if data.is_active is not None:
        user.is_active = data.is_active
    db.commit()
    db.refresh(user)
    return _out(user)
