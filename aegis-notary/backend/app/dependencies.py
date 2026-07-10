from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import NotaryProfile

oauth2 = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_notary(token: str = Depends(oauth2), db: Session = Depends(get_db)) -> NotaryProfile:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        notary_id: int = payload.get("sub")
        if notary_id is None:
            raise HTTPException(401, "Invalid token")
    except JWTError:
        raise HTTPException(401, "Invalid or expired token")

    notary = db.query(NotaryProfile).filter(NotaryProfile.id == int(notary_id)).first()
    if not notary or not notary.is_active:
        raise HTTPException(401, "Notary account not found or inactive")
    return notary
