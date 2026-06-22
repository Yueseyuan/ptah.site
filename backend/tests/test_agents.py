import pytest
from httpx import AsyncClient

from app.core.security import create_access_token, hash_password
from app.models.agent import AgentCapabilityType, AgentRunStatus
from app.models.user import User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def create_user(db, email="user@example.com", is_admin=False) -> User:
    user = User(email=email, hashed_password=hash_password("pass"), is_admin=is_admin)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


def auth(user: User) -> dict:
    return {"Authorization": f"Bearer {create_access_token({'sub': str(user.id)})}"}


async def make_agent(client, user, name="TestAgent") -> dict:
    resp = await client.post("/api/v1/agents", json={"name": name}, headers=auth(user))
    assert resp.status_code == 201
    return resp.json()


# ---------------------------------------------------------------------------
# Agent CRUD
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_agent(client: AsyncClient, db):
    user = await create_user(db, "a1@example.com")
    resp = await client.post("/api/v1/agents", json={"name": "ResearchBot", "description": "Finds stuff"}, headers=auth(user))
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "ResearchBot"
    assert data["is_active"] is True
    assert data["created_by_id"] == user.id


@pytest.mark.asyncio
async def test_create_agent_duplicate_name(client: AsyncClient, db):
    user = await create_user(db, "a2@example.com")
    await make_agent(client, user, "Unique")
    resp = await client.post("/api/v1/agents", json={"name": "Unique"}, headers=auth(user))
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_create_agent_unauthenticated(client: AsyncClient):
    resp = await client.post("/api/v1/agents", json={"name": "X"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_agents(client: AsyncClient, db):
    user = await create_user(db, "a3@example.com")
    await make_agent(client, user, "AgentA")
    await make_agent(client, user, "AgentB")
    resp = await client.get("/api/v1/agents", headers=auth(user))
    assert resp.status_code == 200
    names = [a["name"] for a in resp.json()]
    assert "AgentA" in names
    assert "AgentB" in names


@pytest.mark.asyncio
async def test_get_agent(client: AsyncClient, db):
    user = await create_user(db, "a4@example.com")
    agent = await make_agent(client, user, "GetMe")
    resp = await client.get(f"/api/v1/agents/{agent['id']}", headers=auth(user))
    assert resp.status_code == 200
    assert resp.json()["name"] == "GetMe"


@pytest.mark.asyncio
async def test_get_agent_not_found(client: AsyncClient, db):
    user = await create_user(db, "a5@example.com")
    resp = await client.get("/api/v1/agents/99999", headers=auth(user))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_agent(client: AsyncClient, db):
    user = await create_user(db, "a6@example.com")
    agent = await make_agent(client, user, "OldName")
    resp = await client.patch(
        f"/api/v1/agents/{agent['id']}",
        json={"name": "NewName", "description": "Updated"},
        headers=auth(user),
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "NewName"


@pytest.mark.asyncio
async def test_deactivate_agent(client: AsyncClient, db):
    user = await create_user(db, "a7@example.com")
    agent = await make_agent(client, user, "ToDeactivate")
    resp = await client.delete(f"/api/v1/agents/{agent['id']}", headers=auth(user))
    assert resp.status_code == 204

    # Should not appear in active-only list
    list_resp = await client.get("/api/v1/agents", headers=auth(user))
    names = [a["name"] for a in list_resp.json()]
    assert "ToDeactivate" not in names

    # But appears when fetched directly
    get_resp = await client.get(f"/api/v1/agents/{agent['id']}", headers=auth(user))
    assert get_resp.json()["is_active"] is False


# ---------------------------------------------------------------------------
# Versions
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_version(client: AsyncClient, db):
    user = await create_user(db, "v1@example.com")
    agent = await make_agent(client, user, "VersionedAgent")
    resp = await client.post(
        f"/api/v1/agents/{agent['id']}/versions",
        json={"version": "1.0.0", "system_prompt": "You are helpful.", "model_provider": "ollama", "model_id": "llama3:8b", "is_current": True},
        headers=auth(user),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["version"] == "1.0.0"
    assert data["is_current"] is True


@pytest.mark.asyncio
async def test_list_versions(client: AsyncClient, db):
    user = await create_user(db, "v2@example.com")
    agent = await make_agent(client, user, "MultiVersion")
    for v in ["1.0.0", "1.1.0", "2.0.0"]:
        await client.post(f"/api/v1/agents/{agent['id']}/versions", json={"version": v}, headers=auth(user))
    resp = await client.get(f"/api/v1/agents/{agent['id']}/versions", headers=auth(user))
    assert resp.status_code == 200
    assert len(resp.json()) == 3


@pytest.mark.asyncio
async def test_set_current_unsets_previous(client: AsyncClient, db):
    user = await create_user(db, "v3@example.com")
    agent = await make_agent(client, user, "CurrentSwap")
    await client.post(f"/api/v1/agents/{agent['id']}/versions", json={"version": "1.0.0", "is_current": True}, headers=auth(user))
    await client.post(f"/api/v1/agents/{agent['id']}/versions", json={"version": "2.0.0", "is_current": True}, headers=auth(user))

    resp = await client.get(f"/api/v1/agents/{agent['id']}/versions", headers=auth(user))
    current = [v for v in resp.json() if v["is_current"]]
    assert len(current) == 1
    assert current[0]["version"] == "2.0.0"


# ---------------------------------------------------------------------------
# Capabilities
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_add_capability(client: AsyncClient, db):
    user = await create_user(db, "c1@example.com")
    agent = await make_agent(client, user, "CapAgent")
    resp = await client.post(f"/api/v1/agents/{agent['id']}/capabilities/research", headers=auth(user))
    assert resp.status_code == 201
    assert resp.json()["capability_type"] == "research"


@pytest.mark.asyncio
async def test_add_duplicate_capability_is_idempotent(client: AsyncClient, db):
    user = await create_user(db, "c2@example.com")
    agent = await make_agent(client, user, "IdempotentCap")
    await client.post(f"/api/v1/agents/{agent['id']}/capabilities/code", headers=auth(user))
    resp = await client.post(f"/api/v1/agents/{agent['id']}/capabilities/code", headers=auth(user))
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_list_and_remove_capabilities(client: AsyncClient, db):
    user = await create_user(db, "c3@example.com")
    agent = await make_agent(client, user, "MultiCap")
    for cap in ["research", "code", "review"]:
        await client.post(f"/api/v1/agents/{agent['id']}/capabilities/{cap}", headers=auth(user))

    list_resp = await client.get(f"/api/v1/agents/{agent['id']}/capabilities", headers=auth(user))
    assert len(list_resp.json()) == 3

    await client.delete(f"/api/v1/agents/{agent['id']}/capabilities/code", headers=auth(user))
    list_resp2 = await client.get(f"/api/v1/agents/{agent['id']}/capabilities", headers=auth(user))
    types = [c["capability_type"] for c in list_resp2.json()]
    assert "code" not in types
    assert len(types) == 2


@pytest.mark.asyncio
async def test_all_capability_types_valid(client: AsyncClient, db):
    user = await create_user(db, "c4@example.com")
    agent = await make_agent(client, user, "AllCaps")
    for cap in AgentCapabilityType:
        resp = await client.post(f"/api/v1/agents/{agent['id']}/capabilities/{cap.value}", headers=auth(user))
        assert resp.status_code == 201


# ---------------------------------------------------------------------------
# Runs
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_run(client: AsyncClient, db):
    user = await create_user(db, "r1@example.com")
    agent = await make_agent(client, user, "RunAgent")
    resp = await client.post(
        f"/api/v1/agents/{agent['id']}/runs",
        json={"input": {"query": "Summarize this"}, "model_provider": "ollama", "model_id": "llama3:8b"},
        headers=auth(user),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == AgentRunStatus.PENDING
    assert data["agent_id"] == agent["id"]
    assert data["triggered_by_id"] == user.id


@pytest.mark.asyncio
async def test_list_runs(client: AsyncClient, db):
    user = await create_user(db, "r2@example.com")
    agent = await make_agent(client, user, "MultiRun")
    for _ in range(3):
        await client.post(f"/api/v1/agents/{agent['id']}/runs", json={}, headers=auth(user))
    resp = await client.get(f"/api/v1/agents/{agent['id']}/runs", headers=auth(user))
    assert resp.status_code == 200
    assert len(resp.json()) == 3


@pytest.mark.asyncio
async def test_get_run_detail(client: AsyncClient, db):
    user = await create_user(db, "r3@example.com")
    agent = await make_agent(client, user, "DetailRun")
    run_resp = await client.post(f"/api/v1/agents/{agent['id']}/runs", json={}, headers=auth(user))
    run_id = run_resp.json()["id"]

    resp = await client.get(f"/api/v1/agents/runs/{run_id}", headers=auth(user))
    assert resp.status_code == 200
    assert resp.json()["id"] == run_id
    assert "events" in resp.json()


@pytest.mark.asyncio
async def test_get_run_not_found(client: AsyncClient, db):
    user = await create_user(db, "r4@example.com")
    resp = await client.get("/api/v1/agents/runs/99999", headers=auth(user))
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Risk policies
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_risk_policy(client: AsyncClient, db):
    user = await create_user(db, "rp1@example.com")
    agent = await make_agent(client, user, "RiskyAgent")
    resp = await client.post(
        f"/api/v1/agents/{agent['id']}/risk-policies",
        json={"required_approval_level": 2, "capability_type": "automation", "description": "Needs human check"},
        headers=auth(user),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["required_approval_level"] == 2
    assert data["capability_type"] == "automation"


@pytest.mark.asyncio
async def test_list_risk_policies(client: AsyncClient, db):
    user = await create_user(db, "rp2@example.com")
    agent = await make_agent(client, user, "PolicyAgent")
    await client.post(f"/api/v1/agents/{agent['id']}/risk-policies", json={"required_approval_level": 1}, headers=auth(user))
    await client.post(f"/api/v1/agents/{agent['id']}/risk-policies", json={"required_approval_level": 3, "capability_type": "code"}, headers=auth(user))
    resp = await client.get(f"/api/v1/agents/{agent['id']}/risk-policies", headers=auth(user))
    assert resp.status_code == 200
    assert len(resp.json()) == 2
