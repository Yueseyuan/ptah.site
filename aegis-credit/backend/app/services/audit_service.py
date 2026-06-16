"""Audit logging service."""
from sqlalchemy.orm import Session
from app.models import AuditLog


def log_action(
    db: Session,
    action: str,
    resource_type: str,
    resource_id: int = None,
    detail: str = None,
    user_id: int = None,
    username: str = None,
    ip: str = None,
) -> None:
    """Record an audit log entry and commit it."""
    entry = AuditLog(
        user_id=user_id,
        username=username or "system",
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        detail=detail,
        ip_address=ip,
    )
    db.add(entry)
    db.commit()
