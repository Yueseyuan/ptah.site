"""Tests for Skill, Prompt, and Tool registries (Phase 7)."""
import pytest
from httpx import AsyncClient

from app.core.security import create_access_token, hash_password
from app.models.user import User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def create_user(db, email="user@example.com") -> User:
    user = User(email=email, hashed_password=hash_password("pass"))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


def auth(user: User) -> dict:
    return {"Authorization": f"Bearer {create_access_token({'sub': str(user.id)})}"}


# ===========================================================================
# Skill Registry
# ===========================================================================

@pytest.mark.asyncio
async def test_skill_create(client: AsyncClient, db):
    user = await create_user(db, "sk1@example.com")
    resp = await client.post("/api/v1/skills", json={"name": "WebScraper", "description": "Scrapes web pages"}, headers=auth(user))
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "WebScraper"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_skill_duplicate_name(client: AsyncClient, db):
    user = await create_user(db, "sk2@example.com")
    await client.post("/api/v1/skills", json={"name": "Unique"}, headers=auth(user))
    resp = await client.post("/api/v1/skills", json={"name": "Unique"}, headers=auth(user))
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_skill_list(client: AsyncClient, db):
    user = await create_user(db, "sk3@example.com")
    await client.post("/api/v1/skills", json={"name": "SkillA"}, headers=auth(user))
    await client.post("/api/v1/skills", json={"name": "SkillB"}, headers=auth(user))
    resp = await client.get("/api/v1/skills", headers=auth(user))
    names = [s["name"] for s in resp.json()]
    assert "SkillA" in names and "SkillB" in names


@pytest.mark.asyncio
async def test_skill_get_and_update(client: AsyncClient, db):
    user = await create_user(db, "sk4@example.com")
    skill = (await client.post("/api/v1/skills", json={"name": "Updatable"}, headers=auth(user))).json()
    resp = await client.patch(f"/api/v1/skills/{skill['id']}", json={"description": "New desc"}, headers=auth(user))
    assert resp.status_code == 200
    assert resp.json()["description"] == "New desc"


@pytest.mark.asyncio
async def test_skill_not_found(client: AsyncClient, db):
    user = await create_user(db, "sk5@example.com")
    assert (await client.get("/api/v1/skills/99999", headers=auth(user))).status_code == 404


@pytest.mark.asyncio
async def test_skill_deactivate(client: AsyncClient, db):
    user = await create_user(db, "sk6@example.com")
    skill = (await client.post("/api/v1/skills", json={"name": "ToKill"}, headers=auth(user))).json()
    resp = await client.delete(f"/api/v1/skills/{skill['id']}", headers=auth(user))
    assert resp.status_code == 204
    names = [s["name"] for s in (await client.get("/api/v1/skills", headers=auth(user))).json()]
    assert "ToKill" not in names


@pytest.mark.asyncio
async def test_skill_version_and_run(client: AsyncClient, db):
    user = await create_user(db, "sk7@example.com")
    skill = (await client.post("/api/v1/skills", json={"name": "Versioned"}, headers=auth(user))).json()
    ver = (await client.post(f"/api/v1/skills/{skill['id']}/versions", json={"version": "1.0.0", "is_current": True}, headers=auth(user))).json()
    assert ver["is_current"] is True
    run = (await client.post(f"/api/v1/skills/{skill['id']}/runs", json={"input": {"x": 1}}, headers=auth(user))).json()
    assert run["status"] == "pending"


@pytest.mark.asyncio
async def test_skill_category_crud(client: AsyncClient, db):
    user = await create_user(db, "sk8@example.com")
    cat = (await client.post("/api/v1/skills/categories", json={"name": "automation"}, headers=auth(user))).json()
    assert cat["name"] == "automation"
    cats = (await client.get("/api/v1/skills/categories", headers=auth(user))).json()
    assert any(c["name"] == "automation" for c in cats)


@pytest.mark.asyncio
async def test_skill_risk_policy(client: AsyncClient, db):
    user = await create_user(db, "sk9@example.com")
    skill = (await client.post("/api/v1/skills", json={"name": "RiskySkill"}, headers=auth(user))).json()
    resp = await client.post(f"/api/v1/skills/{skill['id']}/risk-policies", json={"required_approval_level": 2}, headers=auth(user))
    assert resp.status_code == 201
    assert resp.json()["required_approval_level"] == 2


# ===========================================================================
# Prompt Registry
# ===========================================================================

@pytest.mark.asyncio
async def test_prompt_create(client: AsyncClient, db):
    user = await create_user(db, "pr1@example.com")
    resp = await client.post("/api/v1/prompts", json={"name": "SummaryPrompt", "template_type": "chat"}, headers=auth(user))
    assert resp.status_code == 201
    assert resp.json()["template_type"] == "chat"


@pytest.mark.asyncio
async def test_prompt_duplicate(client: AsyncClient, db):
    user = await create_user(db, "pr2@example.com")
    await client.post("/api/v1/prompts", json={"name": "DupPrompt"}, headers=auth(user))
    assert (await client.post("/api/v1/prompts", json={"name": "DupPrompt"}, headers=auth(user))).status_code == 409


@pytest.mark.asyncio
async def test_prompt_list_and_get(client: AsyncClient, db):
    user = await create_user(db, "pr3@example.com")
    tmpl = (await client.post("/api/v1/prompts", json={"name": "GetMe"}, headers=auth(user))).json()
    resp = await client.get(f"/api/v1/prompts/{tmpl['id']}", headers=auth(user))
    assert resp.status_code == 200
    assert resp.json()["name"] == "GetMe"


@pytest.mark.asyncio
async def test_prompt_version_with_variables(client: AsyncClient, db):
    user = await create_user(db, "pr4@example.com")
    tmpl = (await client.post("/api/v1/prompts", json={"name": "VarPrompt"}, headers=auth(user))).json()
    ver = (await client.post(
        f"/api/v1/prompts/{tmpl['id']}/versions",
        json={"version": "1.0.0", "system_prompt": "You are {{role}}.", "user_template": "Do {{task}}.", "variables": ["role", "task"], "is_current": True},
        headers=auth(user),
    )).json()
    assert ver["variables"] == ["role", "task"]
    assert ver["is_current"] is True


@pytest.mark.asyncio
async def test_prompt_run_and_evaluation(client: AsyncClient, db):
    user = await create_user(db, "pr5@example.com")
    tmpl = (await client.post("/api/v1/prompts", json={"name": "EvalPrompt"}, headers=auth(user))).json()
    ver = (await client.post(f"/api/v1/prompts/{tmpl['id']}/versions", json={"version": "1.0.0"}, headers=auth(user))).json()

    run = (await client.post(f"/api/v1/prompts/{tmpl['id']}/runs", json={"variables_used": {"role": "assistant"}, "version_id": ver["id"]}, headers=auth(user))).json()
    assert run["status"] == "pending"

    ev = (await client.post(
        f"/api/v1/prompts/{tmpl['id']}/versions/{ver['id']}/evaluations",
        json={"score": 0.92, "notes": "Very accurate", "tags": ["accurate", "concise"]},
        headers=auth(user),
    )).json()
    assert ev["score"] == 0.92
    assert ev["tags"] == ["accurate", "concise"]


@pytest.mark.asyncio
async def test_prompt_deactivate(client: AsyncClient, db):
    user = await create_user(db, "pr6@example.com")
    tmpl = (await client.post("/api/v1/prompts", json={"name": "KillMe"}, headers=auth(user))).json()
    assert (await client.delete(f"/api/v1/prompts/{tmpl['id']}", headers=auth(user))).status_code == 204
    names = [t["name"] for t in (await client.get("/api/v1/prompts", headers=auth(user))).json()]
    assert "KillMe" not in names


# ===========================================================================
# Tool Registry
# ===========================================================================

@pytest.mark.asyncio
async def test_tool_create(client: AsyncClient, db):
    user = await create_user(db, "tl1@example.com")
    resp = await client.post("/api/v1/tools", json={"name": "WebSearch", "tool_type": "api"}, headers=auth(user))
    assert resp.status_code == 201
    assert resp.json()["tool_type"] == "api"


@pytest.mark.asyncio
async def test_tool_duplicate(client: AsyncClient, db):
    user = await create_user(db, "tl2@example.com")
    await client.post("/api/v1/tools", json={"name": "DupTool"}, headers=auth(user))
    assert (await client.post("/api/v1/tools", json={"name": "DupTool"}, headers=auth(user))).status_code == 409


@pytest.mark.asyncio
async def test_tool_version_with_schema(client: AsyncClient, db):
    user = await create_user(db, "tl3@example.com")
    tool = (await client.post("/api/v1/tools", json={"name": "Calculator"}, headers=auth(user))).json()
    schema = {"type": "object", "properties": {"a": {"type": "number"}, "b": {"type": "number"}}, "required": ["a", "b"]}
    ver = (await client.post(
        f"/api/v1/tools/{tool['id']}/versions",
        json={"version": "1.0.0", "parameters_schema": schema, "is_current": True},
        headers=auth(user),
    )).json()
    assert ver["parameters_schema"]["properties"]["a"]["type"] == "number"


@pytest.mark.asyncio
async def test_tool_run(client: AsyncClient, db):
    user = await create_user(db, "tl4@example.com")
    tool = (await client.post("/api/v1/tools", json={"name": "RunTool"}, headers=auth(user))).json()
    run = (await client.post(f"/api/v1/tools/{tool['id']}/runs", json={"input": {"query": "hello"}}, headers=auth(user))).json()
    assert run["status"] == "pending"
    assert run["input"]["query"] == "hello"

    runs = (await client.get(f"/api/v1/tools/{tool['id']}/runs", headers=auth(user))).json()
    assert len(runs) == 1


@pytest.mark.asyncio
async def test_tool_permission_public(client: AsyncClient, db):
    user = await create_user(db, "tl5@example.com")
    tool = (await client.post("/api/v1/tools", json={"name": "PublicTool"}, headers=auth(user))).json()
    perm = (await client.post(f"/api/v1/tools/{tool['id']}/permissions", json={"is_public": True}, headers=auth(user))).json()
    assert perm["is_public"] is True

    perms = (await client.get(f"/api/v1/tools/{tool['id']}/permissions", headers=auth(user))).json()
    assert len(perms) == 1


@pytest.mark.asyncio
async def test_tool_deactivate(client: AsyncClient, db):
    user = await create_user(db, "tl6@example.com")
    tool = (await client.post("/api/v1/tools", json={"name": "GoneTool"}, headers=auth(user))).json()
    assert (await client.delete(f"/api/v1/tools/{tool['id']}", headers=auth(user))).status_code == 204
    names = [t["name"] for t in (await client.get("/api/v1/tools", headers=auth(user))).json()]
    assert "GoneTool" not in names


@pytest.mark.asyncio
async def test_tool_risk_policy(client: AsyncClient, db):
    user = await create_user(db, "tl7@example.com")
    tool = (await client.post("/api/v1/tools", json={"name": "DangerTool"}, headers=auth(user))).json()
    resp = await client.post(f"/api/v1/tools/{tool['id']}/risk-policies", json={"required_approval_level": 3, "description": "Dangerous"}, headers=auth(user))
    assert resp.status_code == 201
    assert resp.json()["required_approval_level"] == 3


@pytest.mark.asyncio
async def test_tool_not_found(client: AsyncClient, db):
    user = await create_user(db, "tl8@example.com")
    assert (await client.get("/api/v1/tools/99999", headers=auth(user))).status_code == 404
