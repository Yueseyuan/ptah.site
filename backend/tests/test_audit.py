import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.security import create_access_token, hash_password
from app.models.audit import AuditEventType, AuditLog
from app.models.user import User
from app.services.audit import log_event


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def create_user(db, email: str = "user@example.com", password: str = "pass123", is_admin: bool = False) -> User:
    user = User(email=email, hashed_password=hash_password(password), is_admin=is_admin)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


def auth_header(user: User) -> dict:
    return {"Authorization": f"Bearer {create_access_token({'sub': str(user.id)})}"}


# ---------------------------------------------------------------------------
# log_event service
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_log_event_creates_entry(db):
    user = await create_user(db)
    entry = await log_event(db, AuditEventType.LOGIN, user_id=user.id, ip_address="127.0.0.1")
    await db.commit()

    result = await db.execute(select(AuditLog).where(AuditLog.id == entry.id))
    saved = result.scalar_one()
    assert saved.event_type == AuditEventType.LOGIN
    assert saved.user_id == user.id
    assert saved.ip_address == "127.0.0.1"


@pytest.mark.asyncio
async def test_log_event_system_event_no_user(db):
    entry = await log_event(db, AuditEventType.SYSTEM_CHANGE, detail={"action": "config_update"})
    await db.commit()

    result = await db.execute(select(AuditLog).where(AuditLog.id == entry.id))
    saved = result.scalar_one()
    assert saved.event_type == AuditEventType.SYSTEM_CHANGE
    assert saved.user_id is None
    assert saved.detail == {"action": "config_update"}


@pytest.mark.asyncio
async def test_all_event_types_valid(db):
    for event_type in AuditEventType:
        entry = await log_event(db, event_type)
        await db.commit()
        assert entry.event_type == event_type


# ---------------------------------------------------------------------------
# Login auto-logging
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_creates_audit_log(client: AsyncClient, db):
    await create_user(db, email="audit@example.com", password="pass123")
    await client.post("/api/v1/auth/login", json={"email": "audit@example.com", "password": "pass123"})

    result = await db.execute(select(AuditLog).where(AuditLog.event_type == AuditEventType.LOGIN))
    log = result.scalar_one_or_none()
    assert log is not None
    assert log.event_type == AuditEventType.LOGIN


@pytest.mark.asyncio
async def test_failed_login_does_not_create_audit_log(client: AsyncClient, db):
    await create_user(db, email="target@example.com", password="correct")
    await client.post("/api/v1/auth/login", json={"email": "target@example.com", "password": "wrong"})

    result = await db.execute(select(AuditLog).where(AuditLog.event_type == AuditEventType.LOGIN))
    log = result.scalar_one_or_none()
    assert log is None


# ---------------------------------------------------------------------------
# GET /api/v1/audit — admin only
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_audit_logs_as_admin(client: AsyncClient, db):
    admin = await create_user(db, email="admin@example.com", is_admin=True)
    await log_event(db, AuditEventType.UPLOAD, user_id=admin.id)
    await db.commit()

    response = await client.get("/api/v1/audit", headers=auth_header(admin))
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_get_audit_logs_as_regular_user_forbidden(client: AsyncClient, db):
    user = await create_user(db)
    response = await client.get("/api/v1/audit", headers=auth_header(user))
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_audit_logs_unauthenticated(client: AsyncClient):
    response = await client.get("/api/v1/audit")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_audit_logs_filter_by_event_type(client: AsyncClient, db):
    admin = await create_user(db, email="admin2@example.com", is_admin=True)
    await log_event(db, AuditEventType.UPLOAD, user_id=admin.id)
    await log_event(db, AuditEventType.AGENT_RUN, user_id=admin.id)
    await db.commit()

    response = await client.get("/api/v1/audit?event_type=upload", headers=auth_header(admin))
    assert response.status_code == 200
    data = response.json()
    assert all(item["event_type"] == "upload" for item in data["items"])


@pytest.mark.asyncio
async def test_get_audit_logs_filter_by_user_id(client: AsyncClient, db):
    admin = await create_user(db, email="admin3@example.com", is_admin=True)
    other = await create_user(db, email="other@example.com")
    await log_event(db, AuditEventType.TOOL_RUN, user_id=admin.id)
    await log_event(db, AuditEventType.TOOL_RUN, user_id=other.id)
    await db.commit()

    response = await client.get(f"/api/v1/audit?user_id={admin.id}", headers=auth_header(admin))
    assert response.status_code == 200
    data = response.json()
    assert all(item["user_id"] == admin.id for item in data["items"])


@pytest.mark.asyncio
async def test_get_audit_logs_pagination(client: AsyncClient, db):
    admin = await create_user(db, email="admin4@example.com", is_admin=True)
    for _ in range(5):
        await log_event(db, AuditEventType.PROMPT_RUN, user_id=admin.id)
    await db.commit()

    response = await client.get("/api/v1/audit?page=1&limit=3", headers=auth_header(admin))
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 3
    assert data["total"] >= 5
    assert data["page"] == 1
    assert data["limit"] == 3
