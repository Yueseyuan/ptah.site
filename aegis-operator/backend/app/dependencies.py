"""Auth + schema-routing dependencies for the operator portal.

The JWT payload carries both the staff member's identity AND their operator
slug. Every protected endpoint calls require_operator_staff(), which:
  1. Validates the JWT
  2. Extracts operator_slug from the payload
  3. Sets search_path to op_{slug} for this request's DB session
  4. Returns (staff_row, db_session)

This means the DB session is always scoped to exactly one operator's schema
before any business logic runs. No code anywhere else needs to filter by
operator_id or tenant_id.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import SessionLocal, _safe_schema
from app.config import settings
from app.services.auth_service import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


# ---------------------------------------------------------------------------
# Scoped DB session — sets search_path before yielding
# ---------------------------------------------------------------------------
class OperatorSession:
    """Yields a DB session already scoped to the operator's schema."""

    def __init__(self, slug: str):
        self.schema = _safe_schema(slug)

    def __call__(self):
        db = SessionLocal()
        try:
            db.execute(text(f"SET LOCAL search_path TO {self.schema}, public"))
            yield db
        finally:
            db.close()


def get_public_db():
    db = SessionLocal()
    try:
        if "postgresql" in settings.DATABASE_URL:
            db.execute(text("SET LOCAL search_path TO public"))
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Auth dependencies
# ---------------------------------------------------------------------------
def _decode(token: str | None) -> dict:
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload


def get_current_staff(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_public_db),
):
    """Return (operator_slug, staff_dict) for the current request.

    Validates the JWT and routes the DB session to the correct schema.
    The returned db is scoped — callers should use it directly.
    """
    payload = _decode(token)
    operator_slug: str = payload.get("operator_slug", "")
    staff_id: int = payload.get("sub_id", 0)
    role: str = payload.get("role", "staff")

    if not operator_slug:
        raise HTTPException(status_code=401, detail="Token missing operator context")

    # Re-scope the session to this operator's schema
    schema = _safe_schema(operator_slug)
    db.execute(text(f"SET LOCAL search_path TO {schema}, public"))

    return {
        "operator_slug": operator_slug,
        "staff_id": staff_id,
        "role": role,
        "schema": schema,
        "db": db,
    }


def require_role(*allowed_roles: str):
    """Dependency factory: require staff to have one of the given roles."""
    def _check(ctx: dict = Depends(get_current_staff)) -> dict:
        if ctx["role"] not in allowed_roles:
            raise HTTPException(status_code=403, detail=f"Role '{ctx['role']}' is not allowed here")
        return ctx
    return _check


require_owner_or_admin = require_role("owner", "admin")
require_staff_any      = require_role("owner", "admin", "staff", "readonly")
