"""Tests for Memory, Context, and Knowledge APIs (Phase 8)."""
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
# Memory — Collections
# ===========================================================================

@pytest.mark.asyncio
async def test_memory_collection_create(client: AsyncClient, db):
    user = await create_user(db, "mc1@example.com")
    resp = await client.post("/api/v1/memory/collections", json={"name": "ProjectAlpha", "description": "Research memory"}, headers=auth(user))
    assert resp.status_code == 201
    assert resp.json()["name"] == "ProjectAlpha"


@pytest.mark.asyncio
async def test_memory_collection_duplicate(client: AsyncClient, db):
    user = await create_user(db, "mc2@example.com")
    await client.post("/api/v1/memory/collections", json={"name": "DupCol"}, headers=auth(user))
    assert (await client.post("/api/v1/memory/collections", json={"name": "DupCol"}, headers=auth(user))).status_code == 409


@pytest.mark.asyncio
async def test_memory_collection_list(client: AsyncClient, db):
    user = await create_user(db, "mc3@example.com")
    await client.post("/api/v1/memory/collections", json={"name": "ColA"}, headers=auth(user))
    await client.post("/api/v1/memory/collections", json={"name": "ColB"}, headers=auth(user))
    resp = await client.get("/api/v1/memory/collections", headers=auth(user))
    names = [c["name"] for c in resp.json()]
    assert "ColA" in names and "ColB" in names


# ===========================================================================
# Memory — Tags
# ===========================================================================

@pytest.mark.asyncio
async def test_memory_tag_crud(client: AsyncClient, db):
    user = await create_user(db, "mt1@example.com")
    resp = await client.post("/api/v1/memory/tags", json={"name": "important", "color": "#ff0000"}, headers=auth(user))
    assert resp.status_code == 201
    assert resp.json()["color"] == "#ff0000"
    tags = (await client.get("/api/v1/memory/tags", headers=auth(user))).json()
    assert any(t["name"] == "important" for t in tags)


# ===========================================================================
# Memory — Entries
# ===========================================================================

@pytest.mark.asyncio
async def test_memory_entry_create_and_get(client: AsyncClient, db):
    user = await create_user(db, "me1@example.com")
    entry = (await client.post("/api/v1/memory/entries", json={"title": "FastAPI tip", "content": "Use Depends()", "content_type": "text"}, headers=auth(user))).json()
    assert entry["title"] == "FastAPI tip"
    resp = await client.get(f"/api/v1/memory/entries/{entry['id']}", headers=auth(user))
    assert resp.status_code == 200
    assert resp.json()["content"] == "Use Depends()"


@pytest.mark.asyncio
async def test_memory_entry_update_and_deactivate(client: AsyncClient, db):
    user = await create_user(db, "me2@example.com")
    entry = (await client.post("/api/v1/memory/entries", json={"title": "Old title", "content": "old"}, headers=auth(user))).json()
    updated = (await client.patch(f"/api/v1/memory/entries/{entry['id']}", json={"title": "New title"}, headers=auth(user))).json()
    assert updated["title"] == "New title"
    assert (await client.delete(f"/api/v1/memory/entries/{entry['id']}", headers=auth(user))).status_code == 204
    entries = (await client.get("/api/v1/memory/entries", headers=auth(user))).json()
    assert not any(e["id"] == entry["id"] for e in entries)


@pytest.mark.asyncio
async def test_memory_entry_not_found(client: AsyncClient, db):
    user = await create_user(db, "me3@example.com")
    assert (await client.get("/api/v1/memory/entries/99999", headers=auth(user))).status_code == 404


@pytest.mark.asyncio
async def test_memory_entry_search(client: AsyncClient, db):
    user = await create_user(db, "me4@example.com")
    await client.post("/api/v1/memory/entries", json={"title": "Python tips", "content": "Use list comprehensions"}, headers=auth(user))
    await client.post("/api/v1/memory/entries", json={"title": "Go patterns", "content": "Use channels"}, headers=auth(user))
    results = (await client.get("/api/v1/memory/search?q=python", headers=auth(user))).json()
    assert len(results) == 1
    assert results[0]["title"] == "Python tips"


@pytest.mark.asyncio
async def test_memory_entry_filter_by_collection(client: AsyncClient, db):
    user = await create_user(db, "me5@example.com")
    col = (await client.post("/api/v1/memory/collections", json={"name": "FilterCol"}, headers=auth(user))).json()
    await client.post("/api/v1/memory/entries", json={"title": "In collection", "content": "x", "collection_id": col["id"]}, headers=auth(user))
    await client.post("/api/v1/memory/entries", json={"title": "No collection", "content": "y"}, headers=auth(user))
    results = (await client.get(f"/api/v1/memory/entries?collection_id={col['id']}", headers=auth(user))).json()
    assert len(results) == 1
    assert results[0]["title"] == "In collection"


# ===========================================================================
# Memory — Tags on Entries
# ===========================================================================

@pytest.mark.asyncio
async def test_memory_entry_tag_attach_detach(client: AsyncClient, db):
    user = await create_user(db, "met1@example.com")
    entry = (await client.post("/api/v1/memory/entries", json={"title": "Tagged", "content": "content"}, headers=auth(user))).json()
    tag = (await client.post("/api/v1/memory/tags", json={"name": "mytag"}, headers=auth(user))).json()
    # Attach
    resp = await client.post(f"/api/v1/memory/entries/{entry['id']}/tags/{tag['id']}", headers=auth(user))
    assert resp.status_code == 201
    # Idempotent
    resp2 = await client.post(f"/api/v1/memory/entries/{entry['id']}/tags/{tag['id']}", headers=auth(user))
    assert resp2.status_code == 201
    # List
    tags = (await client.get(f"/api/v1/memory/entries/{entry['id']}/tags", headers=auth(user))).json()
    assert any(t["name"] == "mytag" for t in tags)
    # Detach
    assert (await client.delete(f"/api/v1/memory/entries/{entry['id']}/tags/{tag['id']}", headers=auth(user))).status_code == 204
    tags_after = (await client.get(f"/api/v1/memory/entries/{entry['id']}/tags", headers=auth(user))).json()
    assert not any(t["name"] == "mytag" for t in tags_after)


# ===========================================================================
# Memory — Versions
# ===========================================================================

@pytest.mark.asyncio
async def test_memory_entry_versions(client: AsyncClient, db):
    user = await create_user(db, "mv1@example.com")
    entry = (await client.post("/api/v1/memory/entries", json={"title": "Versioned", "content": "v0"}, headers=auth(user))).json()
    ver1 = (await client.post(f"/api/v1/memory/entries/{entry['id']}/versions", json={"content": "v1", "change_summary": "First"}, headers=auth(user))).json()
    assert ver1["version_number"] == 1
    ver2 = (await client.post(f"/api/v1/memory/entries/{entry['id']}/versions", json={"content": "v2", "change_summary": "Second"}, headers=auth(user))).json()
    assert ver2["version_number"] == 2
    versions = (await client.get(f"/api/v1/memory/entries/{entry['id']}/versions", headers=auth(user))).json()
    assert len(versions) == 2


# ===========================================================================
# Memory — Links
# ===========================================================================

@pytest.mark.asyncio
async def test_memory_links(client: AsyncClient, db):
    user = await create_user(db, "ml1@example.com")
    e1 = (await client.post("/api/v1/memory/entries", json={"title": "A", "content": "a"}, headers=auth(user))).json()
    e2 = (await client.post("/api/v1/memory/entries", json={"title": "B", "content": "b"}, headers=auth(user))).json()
    link = (await client.post("/api/v1/memory/links", json={"source_entry_id": e1["id"], "target_entry_id": e2["id"], "link_type": "related"}, headers=auth(user))).json()
    assert link["link_type"] == "related"
    links = (await client.get(f"/api/v1/memory/links?entry_id={e1['id']}", headers=auth(user))).json()
    assert len(links) == 1


# ===========================================================================
# Context — Packages
# ===========================================================================

@pytest.mark.asyncio
async def test_context_package_crud(client: AsyncClient, db):
    user = await create_user(db, "cp1@example.com")
    pkg = (await client.post("/api/v1/context/packages", json={"name": "TaskCtx", "max_tokens": 4096}, headers=auth(user))).json()
    assert pkg["max_tokens"] == 4096
    assert pkg["status"] == "stale"
    # Get
    resp = await client.get(f"/api/v1/context/packages/{pkg['id']}", headers=auth(user))
    assert resp.status_code == 200
    # Update
    updated = (await client.patch(f"/api/v1/context/packages/{pkg['id']}", json={"status": "ready"}, headers=auth(user))).json()
    assert updated["status"] == "ready"
    # Deactivate
    assert (await client.delete(f"/api/v1/context/packages/{pkg['id']}", headers=auth(user))).status_code == 204


@pytest.mark.asyncio
async def test_context_package_not_found(client: AsyncClient, db):
    user = await create_user(db, "cp2@example.com")
    assert (await client.get("/api/v1/context/packages/99999", headers=auth(user))).status_code == 404


# ===========================================================================
# Context — Sources
# ===========================================================================

@pytest.mark.asyncio
async def test_context_sources(client: AsyncClient, db):
    user = await create_user(db, "cs1@example.com")
    pkg = (await client.post("/api/v1/context/packages", json={"name": "SrcCtx"}, headers=auth(user))).json()
    src = (await client.post(f"/api/v1/context/packages/{pkg['id']}/sources", json={"source_type": "memory", "source_id": "42", "priority": 8}, headers=auth(user))).json()
    assert src["source_type"] == "memory"
    assert src["priority"] == 8
    sources = (await client.get(f"/api/v1/context/packages/{pkg['id']}/sources", headers=auth(user))).json()
    assert len(sources) == 1


# ===========================================================================
# Context — Rebuild Runs
# ===========================================================================

@pytest.mark.asyncio
async def test_context_rebuild(client: AsyncClient, db):
    user = await create_user(db, "cr1@example.com")
    pkg = (await client.post("/api/v1/context/packages", json={"name": "RebuildCtx"}, headers=auth(user))).json()
    run = (await client.post(f"/api/v1/context/packages/{pkg['id']}/rebuild", headers=auth(user))).json()
    assert run["status"] == "pending"
    rebuilds = (await client.get(f"/api/v1/context/packages/{pkg['id']}/rebuilds", headers=auth(user))).json()
    assert len(rebuilds) == 1


# ===========================================================================
# Context — Project States
# ===========================================================================

@pytest.mark.asyncio
async def test_project_state(client: AsyncClient, db):
    user = await create_user(db, "ps1@example.com")
    state = (await client.post("/api/v1/context/states", json={"project_name": "apex", "state_type": "snapshot", "data": {"version": "0.7.0"}, "description": "Phase 7 done"}, headers=auth(user))).json()
    assert state["project_name"] == "apex"
    assert state["data"]["version"] == "0.7.0"
    states = (await client.get("/api/v1/context/states?project_name=apex", headers=auth(user))).json()
    assert len(states) == 1


# ===========================================================================
# Context — Decision Records
# ===========================================================================

@pytest.mark.asyncio
async def test_decision_record_crud(client: AsyncClient, db):
    user = await create_user(db, "dr1@example.com")
    rec = (await client.post("/api/v1/context/decisions", json={"title": "Use SQLite for dev", "context": "Local-first", "decision": "Chosen SQLite", "tags": ["database", "local"]}, headers=auth(user))).json()
    assert rec["status"] == "proposed"
    assert rec["tags"] == ["database", "local"]
    # Get
    resp = await client.get(f"/api/v1/context/decisions/{rec['id']}", headers=auth(user))
    assert resp.status_code == 200
    # Update
    updated = (await client.patch(f"/api/v1/context/decisions/{rec['id']}", json={"status": "accepted"}, headers=auth(user))).json()
    assert updated["status"] == "accepted"
    assert updated["updated_by_id"] == user.id
    # List
    decisions = (await client.get("/api/v1/context/decisions", headers=auth(user))).json()
    assert any(d["title"] == "Use SQLite for dev" for d in decisions)


# ===========================================================================
# Knowledge — Nodes
# ===========================================================================

@pytest.mark.asyncio
async def test_knowledge_node_crud(client: AsyncClient, db):
    user = await create_user(db, "kn1@example.com")
    node = (await client.post("/api/v1/knowledge/nodes", json={"title": "FastAPI", "node_type": "concept", "content": "A modern Python web framework", "confidence_score": 0.99}, headers=auth(user))).json()
    assert node["node_type"] == "concept"
    assert node["confidence_score"] == 0.99
    # Get
    resp = await client.get(f"/api/v1/knowledge/nodes/{node['id']}", headers=auth(user))
    assert resp.status_code == 200
    # Update
    updated = (await client.patch(f"/api/v1/knowledge/nodes/{node['id']}", json={"confidence_score": 0.95}, headers=auth(user))).json()
    assert updated["confidence_score"] == 0.95
    # Deactivate
    assert (await client.delete(f"/api/v1/knowledge/nodes/{node['id']}", headers=auth(user))).status_code == 204
    nodes = (await client.get("/api/v1/knowledge/nodes", headers=auth(user))).json()
    assert not any(n["id"] == node["id"] for n in nodes)


@pytest.mark.asyncio
async def test_knowledge_node_filter_by_type(client: AsyncClient, db):
    user = await create_user(db, "kn2@example.com")
    await client.post("/api/v1/knowledge/nodes", json={"title": "Python", "node_type": "concept"}, headers=auth(user))
    await client.post("/api/v1/knowledge/nodes", json={"title": "pip install", "node_type": "procedure"}, headers=auth(user))
    concepts = (await client.get("/api/v1/knowledge/nodes?node_type=concept", headers=auth(user))).json()
    assert all(n["node_type"] == "concept" for n in concepts)


@pytest.mark.asyncio
async def test_knowledge_node_not_found(client: AsyncClient, db):
    user = await create_user(db, "kn3@example.com")
    assert (await client.get("/api/v1/knowledge/nodes/99999", headers=auth(user))).status_code == 404


@pytest.mark.asyncio
async def test_knowledge_search(client: AsyncClient, db):
    user = await create_user(db, "kn4@example.com")
    await client.post("/api/v1/knowledge/nodes", json={"title": "SQLAlchemy ORM", "content": "Python ORM for databases"}, headers=auth(user))
    await client.post("/api/v1/knowledge/nodes", json={"title": "Redis", "content": "In-memory data store"}, headers=auth(user))
    results = (await client.get("/api/v1/knowledge/search?q=orm", headers=auth(user))).json()
    assert len(results) == 1
    assert "SQLAlchemy" in results[0]["title"]


# ===========================================================================
# Knowledge — Edges
# ===========================================================================

@pytest.mark.asyncio
async def test_knowledge_edges(client: AsyncClient, db):
    user = await create_user(db, "ke1@example.com")
    n1 = (await client.post("/api/v1/knowledge/nodes", json={"title": "Dog"}, headers=auth(user))).json()
    n2 = (await client.post("/api/v1/knowledge/nodes", json={"title": "Animal"}, headers=auth(user))).json()
    edge = (await client.post("/api/v1/knowledge/edges", json={"source_node_id": n1["id"], "target_node_id": n2["id"], "edge_type": "is_a", "label": "is a type of"}, headers=auth(user))).json()
    assert edge["edge_type"] == "is_a"
    edges = (await client.get(f"/api/v1/knowledge/edges?node_id={n1['id']}", headers=auth(user))).json()
    assert len(edges) == 1


# ===========================================================================
# Knowledge — Snapshots
# ===========================================================================

@pytest.mark.asyncio
async def test_knowledge_snapshot(client: AsyncClient, db):
    user = await create_user(db, "ks1@example.com")
    await client.post("/api/v1/knowledge/nodes", json={"title": "Node1"}, headers=auth(user))
    await client.post("/api/v1/knowledge/nodes", json={"title": "Node2"}, headers=auth(user))
    snap = (await client.post("/api/v1/knowledge/snapshots", json={"name": "v1-snapshot", "description": "First snapshot"}, headers=auth(user))).json()
    assert snap["name"] == "v1-snapshot"
    assert snap["node_count"] == 2
    snaps = (await client.get("/api/v1/knowledge/snapshots", headers=auth(user))).json()
    assert len(snaps) == 1
