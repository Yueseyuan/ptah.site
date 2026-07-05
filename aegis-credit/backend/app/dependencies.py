"""FastAPI dependency functions for authentication and authorization."""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.services.auth_service import decode_access_token
from app.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

_DEV_ADMIN = User(
    id=0,
    username="dev_admin",
    email="dev@aegis.local",
    full_name="Dev Admin",
    role="admin",
    is_active=True,
)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Decode the JWT and return the matching User.

    When DEV_NO_AUTH is True, return a fake admin without checking the token.
    """
    if settings.DEV_NO_AUTH:
        import os as _os
        if _os.environ.get("RAILWAY_ENVIRONMENT") == "production":
            import warnings
            warnings.warn("[SECURITY] DEV_NO_AUTH=True in Railway production — ignoring", stacklevel=2)
        else:
            return _DEV_ADMIN

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username: str = payload.get("sub", "")
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    user = db.query(User).filter(User.username == username).first()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require the current user to have the 'admin' role."""
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


def require_staff(current_user: User = Depends(get_current_user)) -> User:
    """Require a staff role (admin, investigator, reviewer, readonly). Blocks portal clients."""
    if current_user.role == "client":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Staff access required")
    return current_user


def get_portal_client(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the AegisClient linked to the logged-in portal user."""
    from app.models import AegisClient
    if current_user.role not in ("client", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Portal access only")
    client = db.query(AegisClient).filter(AegisClient.portal_user_id == current_user.id).first()
    if not client and current_user.role != "admin":
        raise HTTPException(status_code=404, detail="No client profile linked to this account")
    return client
