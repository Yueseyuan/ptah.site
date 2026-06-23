from datetime import datetime

from pydantic import BaseModel

from app.models.audit import AuditEventType


class AuditLogOut(BaseModel):
    id: int
    event_type: AuditEventType
    user_id: int | None
    resource_type: str | None
    resource_id: str | None
    detail: dict | None
    ip_address: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogList(BaseModel):
    items: list[AuditLogOut]
    total: int
    page: int
    limit: int
