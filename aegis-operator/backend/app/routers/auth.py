"""Operator portal auth — register operator + login staff."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
import re

from app.database import get_public_db, provision_operator_schema
from app.models import Operator, OpStaff
from app.services.auth_service import hash_password, verify_password, create_token
from app.dependencies import get_current_staff

router = APIRouter(prefix="/api/auth", tags=["auth"])

_SLUG_RE = re.compile(r"^[a-z][a-z0-9\-]{1,30}$")


class OperatorRegister(BaseModel):
    company_name: str
    slug: str           # becomes the schema suffix: op_{slug}
    email: str
    owner_username: str
    owner_password: str
    owner_full_name: Optional[str] = ""


class StaffCreate(BaseModel):
    username: str
    email: str
    full_name: Optional[str] = ""
    password: str
    role: Optional[str] = "staff"


@router.post("/register-operator", status_code=201)
def register_operator(data: OperatorRegister, db: Session = Depends(get_public_db)):
    """Register a new operator company and provision their schema."""
    slug = data.slug.lower().strip()
    if not _SLUG_RE.match(slug):
        raise HTTPException(400, "Slug must be 2-31 lowercase letters, digits, or hyphens")

    if db.query(Operator).filter(Operator.slug == slug).first():
        raise HTTPException(409, "Operator slug already taken")
    if db.query(Operator).filter(Operator.email == data.email).first():
        raise HTTPException(409, "Email already registered")

    schema_name = provision_operator_schema(slug, db)

    # Create the operator record in public schema
    op = Operator(
        slug=slug,
        schema_name=schema_name,
        name=data.company_name,
        email=data.email,
        is_active=True,
    )
    db.add(op)
    db.flush()

    # Create the owner staff account in the operator's own schema
    db.execute(text(f"SET LOCAL search_path TO {schema_name}, public"))
    owner = OpStaff(
        username=data.owner_username,
        email=data.email,
        hashed_password=hash_password(data.owner_password),
        full_name=data.owner_full_name or "",
        role="owner",
        is_active=True,
    )
    db.add(owner)
    db.commit()
    db.refresh(op)

    return {
        "operator_id": op.id,
        "slug": op.slug,
        "schema": schema_name,
        "message": f"Operator '{data.company_name}' registered. Login at /api/auth/login with slug={slug}",
    }


@router.post("/login")
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_public_db),
):
    """Login as operator staff. Username format: {username}@{operator-slug}
    e.g. alice@acme-credit
    """
    if "@" not in form.username:
        raise HTTPException(400, "Username must be in the format: username@operator-slug")

    raw_user, slug = form.username.rsplit("@", 1)
    slug = slug.strip().lower()

    op = db.query(Operator).filter(Operator.slug == slug, Operator.is_active == True).first()
    if not op:
        raise HTTPException(401, "Unknown operator or account disabled")

    # Switch to operator schema and find staff
    db.execute(text(f"SET LOCAL search_path TO {op.schema_name}, public"))
    staff = db.query(OpStaff).filter(
        OpStaff.username == raw_user.strip(),
        OpStaff.is_active == True,
    ).first()

    if not staff or not verify_password(form.password, staff.hashed_password):
        raise HTTPException(401, "Invalid credentials")

    token = create_token({
        "sub": staff.username,
        "sub_id": staff.id,
        "operator_slug": slug,
        "operator_id": op.id,
        "role": staff.role,
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": staff.role,
        "username": staff.username,
        "operator": op.name,
        "operator_slug": slug,
    }


@router.get("/me")
def me(ctx: dict = Depends(get_current_staff)):
    return {
        "username": ctx["role"],  # placeholder — real impl queries OpStaff
        "role": ctx["role"],
        "operator_slug": ctx["operator_slug"],
    }


@router.post("/staff", status_code=201)
def create_staff(
    data: StaffCreate,
    ctx: dict = Depends(get_current_staff),
):
    """Add a staff member to the operator account. Requires owner or admin."""
    if ctx["role"] not in ("owner", "admin"):
        raise HTTPException(403, "Only owner or admin can add staff")

    db: Session = ctx["db"]
    if db.query(OpStaff).filter(OpStaff.username == data.username).first():
        raise HTTPException(409, "Username already taken")
    if db.query(OpStaff).filter(OpStaff.email == data.email).first():
        raise HTTPException(409, "Email already registered")

    staff = OpStaff(
        username=data.username,
        email=data.email,
        full_name=data.full_name or "",
        hashed_password=hash_password(data.password),
        role=data.role or "staff",
        is_active=True,
    )
    db.add(staff)
    db.commit()
    db.refresh(staff)
    return {"id": staff.id, "username": staff.username, "role": staff.role}
