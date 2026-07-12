"""Authentication router — register, login, user management."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.models import User
from app.services.auth_service import hash_password, verify_password, create_access_token, decode_access_token
from app.dependencies import get_current_user, require_admin, oauth2_scheme
from app.config import settings

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


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = None


class BootstrapAdminRequest(BaseModel):
    full_name: str
    email: str
    password: str


class EmailLoginRequest(BaseModel):
    email: str
    password: str


def _out(u: User) -> dict:
    return {
        "id": u.id,
        "username": u.username,
        "email": u.email,
        "full_name": u.full_name,
        "role": u.role,
        "is_active": u.is_active,
        "created_at": u.created_at.isoformat() if u.created_at else None,
    }


@router.post("/register", status_code=201)
def register(
    data: UserCreate,
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme),
):
    """Register a new user.

    Bootstrap path: if NO admin user exists, the first registration is granted
    admin role with no token required — this lets the owner create the first
    admin account even when portal clients already exist.

    Normal path: requires a valid admin JWT.
    """
    admin_count = db.query(User).filter(User.role == "admin").count()

    if admin_count == 0:
        # Bootstrap: grant admin role to whoever registers first as staff
        role = "admin"
    else:
        # Existing admins present — require a valid admin token
        if not token:
            raise HTTPException(status_code=401, detail="Authentication required")
        payload = decode_access_token(token)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        username: str = payload.get("sub", "")
        caller = db.query(User).filter(User.username == username).first()
        if not caller or caller.role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required to create users")
        role = data.role or "investigator"

    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")


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
    """Authenticate with username or email + password, return a JWT bearer token."""
    if settings.DEV_NO_AUTH:
        token = create_access_token({"sub": "dev_admin", "role": "admin"})
        return {"access_token": token, "token_type": "bearer", "role": "admin", "username": "dev_admin"}
    # Accept username or email in the username field
    user = (
        db.query(User).filter(User.username == form_data.username).first()
        or db.query(User).filter(User.email == form_data.username).first()
    )
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


@router.post("/login-email")
def login_email(data: EmailLoginRequest, db: Session = Depends(get_db)):
    """Email + password login (used by some frontend versions)."""
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.hashed_password or ""):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Account is disabled")
    token = create_access_token({"sub": user.username, "role": user.role})
    return {"access_token": token, "token_type": "bearer", "role": user.role, "username": user.username}


@router.post("/bootstrap-admin", status_code=201)
def bootstrap_admin(data: BootstrapAdminRequest, db: Session = Depends(get_db)):
    """Create the first admin account. Fails if any admin already exists."""
    if db.query(User).filter(User.role == "admin").count() > 0:
        raise HTTPException(status_code=400, detail="An admin account already exists. Use /login instead.")
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    username = data.email.split("@")[0].replace(".", "_").lower()
    # Make username unique if taken
    base = username
    i = 1
    while db.query(User).filter(User.username == username).first():
        username = f"{base}{i}"
        i += 1
    user = User(
        username=username,
        email=data.email,
        full_name=data.full_name,
        hashed_password=hash_password(data.password),
        role="admin",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token({"sub": user.username, "role": "admin"})
    return {"access_token": token, "token_type": "bearer", "role": "admin", "username": user.username}


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    """Return current user info."""
    return _out(current_user)


@router.patch("/me")
def update_me(
    data: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update own profile. Password change requires current_password + new_password."""
    # Re-fetch so we have a session-attached object (DEV_NO_AUTH returns a transient user).
    user = db.query(User).filter(User.id == current_user.id).first()
    if user is None:
        # No persisted user (e.g. DEV_NO_AUTH mode) — validate then return in-memory.
        if data.new_password:
            if not data.current_password:
                raise HTTPException(400, "current_password is required to change password")
            raise HTTPException(400, "Current password is incorrect")
        if data.full_name is not None:
            current_user.full_name = data.full_name
        if data.email is not None:
            current_user.email = data.email
        return _out(current_user)

    if data.new_password:
        if not data.current_password:
            raise HTTPException(400, "current_password is required to change password")
        if not user.hashed_password or not verify_password(data.current_password, user.hashed_password):
            raise HTTPException(400, "Current password is incorrect")
        user.hashed_password = hash_password(data.new_password)
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.email is not None:
        conflict = db.query(User).filter(User.email == data.email, User.id != user.id).first()
        if conflict:
            raise HTTPException(400, "Email already in use")
        user.email = data.email
    db.commit()
    db.refresh(user)
    return _out(user)


@router.get("/users")
def list_users(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """List all users (admin only)."""
    return [_out(u) for u in db.query(User).order_by(User.id).all()]


@router.get("/admin-check")
def admin_check(secret: str, db: Session = Depends(get_db)):
    """List admin accounts. Gated by ADMIN_RESET_SECRET. Use ADMIN_PASSWORD env var to reset passwords."""
    if not settings.ADMIN_RESET_SECRET or secret != settings.ADMIN_RESET_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")
    admins = db.query(User).filter(User.role == "admin").order_by(User.id).all()
    return [{"id": u.id, "username": u.username, "email": u.email, "is_active": u.is_active} for u in admins]


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
