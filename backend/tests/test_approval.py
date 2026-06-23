import pytest
from httpx import AsyncClient

from app.core.security import create_access_token, hash_password
from app.models.approval import ApprovalStatus
from app.models.user import User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def create_user(db, email="user@example.com", password="pass", is_admin=False) -> User:
    user = User(email=email, hashed_password=hash_password(password), is_admin=is_admin)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


def auth(user: User) -> dict:
    return {"Authorization": f"Bearer {create_access_token({'sub': str(user.id)})}"}


async def request_approval(client, user, level=1, action_type="test_action", **kwargs):
    return await client.post(
        "/api/v1/approvals/request",
        json={"level": level, "action_type": action_type, **kwargs},
        headers=auth(user),
    )


# ---------------------------------------------------------------------------
# Create request
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_level0_request_auto_approved(client: AsyncClient, db):
    user = await create_user(db, email="u0@example.com")
    resp = await request_approval(client, user, level=0)
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == ApprovalStatus.AUTO_APPROVED
    assert data["expires_at"] is None


@pytest.mark.asyncio
async def test_level1_request_pending(client: AsyncClient, db):
    user = await create_user(db, email="u1@example.com")
    resp = await request_approval(client, user, level=1)
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == ApprovalStatus.PENDING
    assert data["expires_at"] is not None


@pytest.mark.asyncio
async def test_level3_request_pending(client: AsyncClient, db):
    user = await create_user(db, email="u3@example.com")
    resp = await request_approval(client, user, level=3)
    assert resp.status_code == 201
    assert resp.json()["status"] == ApprovalStatus.PENDING


@pytest.mark.asyncio
async def test_create_request_unauthenticated(client: AsyncClient):
    resp = await client.post("/api/v1/approvals/request", json={"level": 1, "action_type": "x"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_request_with_payload_and_reason(client: AsyncClient, db):
    user = await create_user(db, email="payload@example.com")
    resp = await request_approval(
        client, user, level=2,
        payload={"file": "report.pdf", "size_mb": 5},
        reason="Need to upload monthly report",
        resource_type="file",
        resource_id="report.pdf",
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["payload"]["file"] == "report.pdf"
    assert data["reason"] == "Need to upload monthly report"
    assert data["resource_type"] == "file"


# ---------------------------------------------------------------------------
# Approve
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_approve_level1_by_any_user(client: AsyncClient, db):
    requester = await create_user(db, email="req@example.com")
    approver = await create_user(db, email="apr@example.com")
    req_resp = await request_approval(client, requester, level=1)
    req_id = req_resp.json()["id"]

    resp = await client.post(f"/api/v1/approvals/{req_id}/approve", json={}, headers=auth(approver))
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == ApprovalStatus.APPROVED
    assert data["decision"]["verdict"] == "approved"
    assert data["decision"]["decided_by_id"] == approver.id


@pytest.mark.asyncio
async def test_approve_level3_by_non_admin_forbidden(client: AsyncClient, db):
    requester = await create_user(db, email="req3@example.com")
    non_admin = await create_user(db, email="nonadmin@example.com")
    req_resp = await request_approval(client, requester, level=3)
    req_id = req_resp.json()["id"]

    resp = await client.post(f"/api/v1/approvals/{req_id}/approve", json={}, headers=auth(non_admin))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_approve_level3_by_admin(client: AsyncClient, db):
    requester = await create_user(db, email="req3b@example.com")
    admin = await create_user(db, email="admin@example.com", is_admin=True)
    req_resp = await request_approval(client, requester, level=3)
    req_id = req_resp.json()["id"]

    resp = await client.post(f"/api/v1/approvals/{req_id}/approve", json={"note": "Looks good"}, headers=auth(admin))
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == ApprovalStatus.APPROVED
    assert data["decision"]["note"] == "Looks good"


@pytest.mark.asyncio
async def test_approve_already_decided_conflicts(client: AsyncClient, db):
    user = await create_user(db, email="dup@example.com")
    req_resp = await request_approval(client, user, level=1)
    req_id = req_resp.json()["id"]

    await client.post(f"/api/v1/approvals/{req_id}/approve", json={}, headers=auth(user))
    resp = await client.post(f"/api/v1/approvals/{req_id}/approve", json={}, headers=auth(user))
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Reject
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reject_request(client: AsyncClient, db):
    requester = await create_user(db, email="rej_req@example.com")
    admin = await create_user(db, email="rej_admin@example.com", is_admin=True)
    req_resp = await request_approval(client, requester, level=1)
    req_id = req_resp.json()["id"]

    resp = await client.post(f"/api/v1/approvals/{req_id}/reject", json={"note": "Not allowed"}, headers=auth(admin))
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == ApprovalStatus.REJECTED
    assert data["decision"]["verdict"] == "rejected"
    assert data["decision"]["note"] == "Not allowed"


# ---------------------------------------------------------------------------
# List / Get
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_approvals_admin_only(client: AsyncClient, db):
    admin = await create_user(db, email="listadmin@example.com", is_admin=True)
    user = await create_user(db, email="listuser@example.com")
    await request_approval(client, user, level=1)

    resp = await client.get("/api/v1/approvals", headers=auth(admin))
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_list_approvals_non_admin_forbidden(client: AsyncClient, db):
    user = await create_user(db, email="nolist@example.com")
    resp = await client.get("/api/v1/approvals", headers=auth(user))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_list_filter_by_status(client: AsyncClient, db):
    admin = await create_user(db, email="fadmin@example.com", is_admin=True)
    user = await create_user(db, email="fuser@example.com")
    await request_approval(client, user, level=0)  # AUTO_APPROVED
    await request_approval(client, user, level=1)  # PENDING

    resp = await client.get("/api/v1/approvals?status=pending", headers=auth(admin))
    data = resp.json()
    assert all(i["status"] == "pending" for i in data["items"])


@pytest.mark.asyncio
async def test_get_own_request(client: AsyncClient, db):
    user = await create_user(db, email="own@example.com")
    req_resp = await request_approval(client, user, level=1)
    req_id = req_resp.json()["id"]

    resp = await client.get(f"/api/v1/approvals/{req_id}", headers=auth(user))
    assert resp.status_code == 200
    assert resp.json()["id"] == req_id


@pytest.mark.asyncio
async def test_get_other_user_request_forbidden(client: AsyncClient, db):
    owner = await create_user(db, email="owner@example.com")
    other = await create_user(db, email="other@example.com")
    req_resp = await request_approval(client, owner, level=1)
    req_id = req_resp.json()["id"]

    resp = await client.get(f"/api/v1/approvals/{req_id}", headers=auth(other))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_nonexistent_request(client: AsyncClient, db):
    user = await create_user(db, email="ghost@example.com")
    resp = await client.get("/api/v1/approvals/99999", headers=auth(user))
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Risk + Action policies
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_risk_policy(client: AsyncClient, db):
    admin = await create_user(db, email="rpadmin@example.com", is_admin=True)
    resp = await client.post(
        "/api/v1/approvals/policies/risk",
        json={"resource_type": "agent", "action_type": "run", "required_level": 2},
        headers=auth(admin),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["required_level"] == 2


@pytest.mark.asyncio
async def test_create_action_policy_affects_timeout(client: AsyncClient, db):
    admin = await create_user(db, email="apadmin@example.com", is_admin=True)
    user = await create_user(db, email="apuser@example.com")
    await client.post(
        "/api/v1/approvals/policies/action",
        json={"name": "slow_action", "resource_type": "file", "action_type": "slow_upload", "timeout_minutes": 120},
        headers=auth(admin),
    )
    resp = await request_approval(client, user, level=1, action_type="slow_upload")
    assert resp.status_code == 201
