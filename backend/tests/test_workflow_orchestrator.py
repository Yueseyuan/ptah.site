"""Tests for Workflow Engine and Orchestrator APIs (Phase 9)."""
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
# Workflow CRUD
# ===========================================================================

@pytest.mark.asyncio
async def test_workflow_create(client: AsyncClient, db):
    user = await create_user(db, "wf1@example.com")
    resp = await client.post("/api/v1/workflows", json={"name": "DataPipeline", "description": "ETL flow"}, headers=auth(user))
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "DataPipeline"
    assert data["status"] == "draft"


@pytest.mark.asyncio
async def test_workflow_list_and_get(client: AsyncClient, db):
    user = await create_user(db, "wf2@example.com")
    wf = (await client.post("/api/v1/workflows", json={"name": "GetMe"}, headers=auth(user))).json()
    resp = await client.get(f"/api/v1/workflows/{wf['id']}", headers=auth(user))
    assert resp.status_code == 200
    assert resp.json()["name"] == "GetMe"
    listed = (await client.get("/api/v1/workflows", headers=auth(user))).json()
    assert any(w["name"] == "GetMe" for w in listed)


@pytest.mark.asyncio
async def test_workflow_update_and_deactivate(client: AsyncClient, db):
    user = await create_user(db, "wf3@example.com")
    wf = (await client.post("/api/v1/workflows", json={"name": "UpdateMe"}, headers=auth(user))).json()
    updated = (await client.patch(f"/api/v1/workflows/{wf['id']}", json={"status": "active"}, headers=auth(user))).json()
    assert updated["status"] == "active"
    assert (await client.delete(f"/api/v1/workflows/{wf['id']}", headers=auth(user))).status_code == 204
    workflows = (await client.get("/api/v1/workflows", headers=auth(user))).json()
    assert not any(w["id"] == wf["id"] for w in workflows)


@pytest.mark.asyncio
async def test_workflow_not_found(client: AsyncClient, db):
    user = await create_user(db, "wf4@example.com")
    assert (await client.get("/api/v1/workflows/99999", headers=auth(user))).status_code == 404


# ===========================================================================
# Workflow Steps
# ===========================================================================

@pytest.mark.asyncio
async def test_workflow_steps(client: AsyncClient, db):
    user = await create_user(db, "ws1@example.com")
    wf = (await client.post("/api/v1/workflows", json={"name": "SteppedFlow"}, headers=auth(user))).json()
    s1 = (await client.post(f"/api/v1/workflows/{wf['id']}/steps", json={"name": "Fetch", "step_type": "tool", "order_index": 0}, headers=auth(user))).json()
    assert s1["step_type"] == "tool"
    s2 = (await client.post(f"/api/v1/workflows/{wf['id']}/steps", json={"name": "Process", "step_type": "agent", "order_index": 1, "depends_on_step_ids": [s1["id"]]}, headers=auth(user))).json()
    assert s2["depends_on_step_ids"] == [s1["id"]]
    steps = (await client.get(f"/api/v1/workflows/{wf['id']}/steps", headers=auth(user))).json()
    assert len(steps) == 2
    # Deactivate a step
    assert (await client.delete(f"/api/v1/workflows/{wf['id']}/steps/{s1['id']}", headers=auth(user))).status_code == 204
    steps_after = (await client.get(f"/api/v1/workflows/{wf['id']}/steps", headers=auth(user))).json()
    assert len(steps_after) == 1


# ===========================================================================
# Workflow Runs
# ===========================================================================

@pytest.mark.asyncio
async def test_workflow_run(client: AsyncClient, db):
    user = await create_user(db, "wr1@example.com")
    wf = (await client.post("/api/v1/workflows", json={"name": "RunnableFlow"}, headers=auth(user))).json()
    run = (await client.post(f"/api/v1/workflows/{wf['id']}/runs", json={"input": {"data": "test"}}, headers=auth(user))).json()
    assert run["status"] == "pending"
    assert run["input"]["data"] == "test"
    runs = (await client.get(f"/api/v1/workflows/{wf['id']}/runs", headers=auth(user))).json()
    assert len(runs) == 1
    # Get run by ID
    fetched = (await client.get(f"/api/v1/workflows/{wf['id']}/runs/{run['id']}", headers=auth(user))).json()
    assert fetched["id"] == run["id"]
    # Events (empty initially)
    events = (await client.get(f"/api/v1/workflows/{wf['id']}/runs/{run['id']}/events", headers=auth(user))).json()
    assert isinstance(events, list)


# ===========================================================================
# Orchestrator Tasks
# ===========================================================================

@pytest.mark.asyncio
async def test_orchestrator_task_create(client: AsyncClient, db):
    user = await create_user(db, "ot1@example.com")
    resp = await client.post("/api/v1/orchestrator/tasks", json={"title": "Analyze report", "task_type": "analysis", "priority": 8, "required_capabilities": ["research", "document"]}, headers=auth(user))
    assert resp.status_code == 201
    data = resp.json()
    assert data["priority"] == 8
    assert data["status"] == "pending"
    assert data["required_capabilities"] == ["research", "document"]


@pytest.mark.asyncio
async def test_orchestrator_task_list_and_filter(client: AsyncClient, db):
    user = await create_user(db, "ot2@example.com")
    await client.post("/api/v1/orchestrator/tasks", json={"title": "Task A", "task_type": "code"}, headers=auth(user))
    await client.post("/api/v1/orchestrator/tasks", json={"title": "Task B", "task_type": "research"}, headers=auth(user))
    all_tasks = (await client.get("/api/v1/orchestrator/tasks", headers=auth(user))).json()
    assert len(all_tasks) >= 2
    code_tasks = (await client.get("/api/v1/orchestrator/tasks?task_type=code", headers=auth(user))).json()
    assert all(t["task_type"] == "code" for t in code_tasks)


@pytest.mark.asyncio
async def test_orchestrator_task_update(client: AsyncClient, db):
    user = await create_user(db, "ot3@example.com")
    task = (await client.post("/api/v1/orchestrator/tasks", json={"title": "UpdateTask", "task_type": "general"}, headers=auth(user))).json()
    updated = (await client.patch(f"/api/v1/orchestrator/tasks/{task['id']}", json={"status": "running", "priority": 10}, headers=auth(user))).json()
    assert updated["status"] == "running"
    assert updated["priority"] == 10


@pytest.mark.asyncio
async def test_orchestrator_task_not_found(client: AsyncClient, db):
    user = await create_user(db, "ot4@example.com")
    assert (await client.get("/api/v1/orchestrator/tasks/99999", headers=auth(user))).status_code == 404


# ===========================================================================
# Task Assignments
# ===========================================================================

@pytest.mark.asyncio
async def test_task_assignment(client: AsyncClient, db):
    user = await create_user(db, "ta1@example.com")
    task = (await client.post("/api/v1/orchestrator/tasks", json={"title": "AssignMe", "task_type": "code"}, headers=auth(user))).json()
    agent = (await client.post("/api/v1/agents", json={"name": "AgentForTask"}, headers=auth(user))).json()
    assignment = (await client.post(f"/api/v1/orchestrator/tasks/{task['id']}/assignments", json={"agent_id": agent["id"], "score": 0.9}, headers=auth(user))).json()
    assert assignment["agent_id"] == agent["id"]
    assert assignment["score"] == 0.9
    assignments = (await client.get(f"/api/v1/orchestrator/tasks/{task['id']}/assignments", headers=auth(user))).json()
    assert len(assignments) == 1


# ===========================================================================
# Task Dependencies
# ===========================================================================

@pytest.mark.asyncio
async def test_task_dependencies(client: AsyncClient, db):
    user = await create_user(db, "td1@example.com")
    t1 = (await client.post("/api/v1/orchestrator/tasks", json={"title": "First", "task_type": "research"}, headers=auth(user))).json()
    t2 = (await client.post("/api/v1/orchestrator/tasks", json={"title": "Second", "task_type": "code"}, headers=auth(user))).json()
    dep = (await client.post(f"/api/v1/orchestrator/tasks/{t2['id']}/dependencies", json={"depends_on_task_id": t1["id"]}, headers=auth(user))).json()
    assert dep["depends_on_task_id"] == t1["id"]
    deps = (await client.get(f"/api/v1/orchestrator/tasks/{t2['id']}/dependencies", headers=auth(user))).json()
    assert len(deps) == 1


# ===========================================================================
# Task Branches + Branch Runs + Result Merges
# ===========================================================================

@pytest.mark.asyncio
async def test_task_branches_and_runs(client: AsyncClient, db):
    user = await create_user(db, "tb1@example.com")
    task = (await client.post("/api/v1/orchestrator/tasks", json={"title": "BranchTask", "task_type": "analysis"}, headers=auth(user))).json()
    branch = (await client.post(f"/api/v1/orchestrator/tasks/{task['id']}/branches", json={"name": "Strategy A", "merge_strategy": "first_success"}, headers=auth(user))).json()
    assert branch["merge_strategy"] == "first_success"
    branches = (await client.get(f"/api/v1/orchestrator/tasks/{task['id']}/branches", headers=auth(user))).json()
    assert len(branches) == 1
    # Branch run
    br = (await client.post(f"/api/v1/orchestrator/branches/{branch['id']}/runs", json={}, headers=auth(user))).json()
    assert br["status"] == "pending"
    runs = (await client.get(f"/api/v1/orchestrator/branches/{branch['id']}/runs", headers=auth(user))).json()
    assert len(runs) == 1
    # Result merge
    merge = (await client.post(f"/api/v1/orchestrator/branches/{branch['id']}/merges", json={"strategy_used": "first_success", "branch_run_ids": [br["id"]], "merged_output": {"result": "done"}}, headers=auth(user))).json()
    assert merge["strategy_used"] == "first_success"
    assert merge["merged_output"]["result"] == "done"


# ===========================================================================
# Orchestrator Runs + Decisions + Plans
# ===========================================================================

@pytest.mark.asyncio
async def test_orchestrator_run_create(client: AsyncClient, db):
    user = await create_user(db, "or1@example.com")
    run = (await client.post("/api/v1/orchestrator/runs", json={"name": "RunAlpha", "input": {"goal": "build feature"}}, headers=auth(user))).json()
    assert run["status"] == "pending"
    assert run["name"] == "RunAlpha"
    runs = (await client.get("/api/v1/orchestrator/runs", headers=auth(user))).json()
    assert any(r["name"] == "RunAlpha" for r in runs)
    fetched = (await client.get(f"/api/v1/orchestrator/runs/{run['id']}", headers=auth(user))).json()
    assert fetched["id"] == run["id"]


@pytest.mark.asyncio
async def test_orchestrator_decisions_and_plans(client: AsyncClient, db):
    user = await create_user(db, "or2@example.com")
    run = (await client.post("/api/v1/orchestrator/runs", json={"name": "PlanRun"}, headers=auth(user))).json()
    # Decision
    decision = (await client.post(f"/api/v1/orchestrator/runs/{run['id']}/decisions", json={"decision_type": "task_routing", "rationale": "High priority"}, headers=auth(user))).json()
    assert decision["decision_type"] == "task_routing"
    decisions = (await client.get(f"/api/v1/orchestrator/runs/{run['id']}/decisions", headers=auth(user))).json()
    assert len(decisions) == 1
    # Plan
    plan = (await client.post(f"/api/v1/orchestrator/runs/{run['id']}/plans", json={"steps": [{"step": 1, "action": "fetch"}, {"step": 2, "action": "analyze"}], "rationale": "Two-step approach"}, headers=auth(user))).json()
    assert plan["is_approved"] is False
    assert len(plan["steps"]) == 2
    # Approve plan
    approved = (await client.post(f"/api/v1/orchestrator/runs/{run['id']}/plans/{plan['id']}/approve", headers=auth(user))).json()
    assert approved["is_approved"] is True
    assert approved["approved_by_id"] == user.id
