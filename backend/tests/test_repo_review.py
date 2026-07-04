"""Tests for Repo Review Pipeline (Phase 10)."""
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
# Review CRUD
# ===========================================================================

@pytest.mark.asyncio
async def test_review_create(client: AsyncClient, db):
    user = await create_user(db, "rr1@example.com")
    resp = await client.post("/api/v1/repo-reviews", json={"repo_url": "https://github.com/org/repo", "repo_name": "org/repo", "branch": "main"}, headers=auth(user))
    assert resp.status_code == 201
    data = resp.json()
    assert data["repo_name"] == "org/repo"
    assert data["status"] == "pending"
    assert data["classification"] is None


@pytest.mark.asyncio
async def test_review_list_and_get(client: AsyncClient, db):
    user = await create_user(db, "rr2@example.com")
    review = (await client.post("/api/v1/repo-reviews", json={"repo_url": "https://github.com/org/lib", "repo_name": "org/lib"}, headers=auth(user))).json()
    resp = await client.get(f"/api/v1/repo-reviews/{review['id']}", headers=auth(user))
    assert resp.status_code == 200
    listed = (await client.get("/api/v1/repo-reviews", headers=auth(user))).json()
    assert any(r["repo_name"] == "org/lib" for r in listed)


@pytest.mark.asyncio
async def test_review_status_update(client: AsyncClient, db):
    user = await create_user(db, "rr3@example.com")
    review = (await client.post("/api/v1/repo-reviews", json={"repo_url": "https://github.com/x/y", "repo_name": "x/y"}, headers=auth(user))).json()
    updated = (await client.patch(f"/api/v1/repo-reviews/{review['id']}/status", json={"status": "running"}, headers=auth(user))).json()
    assert updated["status"] == "running"


@pytest.mark.asyncio
async def test_review_filter_by_status(client: AsyncClient, db):
    user = await create_user(db, "rr4@example.com")
    await client.post("/api/v1/repo-reviews", json={"repo_url": "https://github.com/a/b", "repo_name": "a/b"}, headers=auth(user))
    r = (await client.post("/api/v1/repo-reviews", json={"repo_url": "https://github.com/c/d", "repo_name": "c/d"}, headers=auth(user))).json()
    await client.patch(f"/api/v1/repo-reviews/{r['id']}/status", json={"status": "completed", "classification": "use_directly", "overall_score": 0.95}, headers=auth(user))
    completed = (await client.get("/api/v1/repo-reviews?status=completed", headers=auth(user))).json()
    assert all(rv["status"] == "completed" for rv in completed)


@pytest.mark.asyncio
async def test_review_not_found(client: AsyncClient, db):
    user = await create_user(db, "rr5@example.com")
    assert (await client.get("/api/v1/repo-reviews/99999", headers=auth(user))).status_code == 404


# ===========================================================================
# Review Stages (5-stage pipeline)
# ===========================================================================

@pytest.mark.asyncio
async def test_review_stages_pipeline(client: AsyncClient, db):
    user = await create_user(db, "rs1@example.com")
    review = (await client.post("/api/v1/repo-reviews", json={"repo_url": "https://github.com/e/f", "repo_name": "e/f"}, headers=auth(user))).json()

    for stage_type, verdict, score in [
        ("license", "pass", 1.0),
        ("security", "warn", 0.7),
        ("dependency", "pass", 0.9),
        ("capability", "pass", 0.85),
        ("integration", "fail", 0.3),
    ]:
        s = (await client.post(f"/api/v1/repo-reviews/{review['id']}/stages", json={"stage_type": stage_type, "verdict": verdict, "score": score, "notes": f"{stage_type} stage done"}, headers=auth(user))).json()
        assert s["verdict"] == verdict

    stages = (await client.get(f"/api/v1/repo-reviews/{review['id']}/stages", headers=auth(user))).json()
    assert len(stages) == 5
    # Stages should be returned in pipeline order
    stage_types = [s["stage_type"] for s in stages]
    assert stage_types == ["license", "security", "dependency", "capability", "integration"]


# ===========================================================================
# Review Findings
# ===========================================================================

@pytest.mark.asyncio
async def test_review_findings(client: AsyncClient, db):
    user = await create_user(db, "rf1@example.com")
    review = (await client.post("/api/v1/repo-reviews", json={"repo_url": "https://github.com/g/h", "repo_name": "g/h"}, headers=auth(user))).json()
    stage = (await client.post(f"/api/v1/repo-reviews/{review['id']}/stages", json={"stage_type": "security", "verdict": "warn"}, headers=auth(user))).json()

    f1 = (await client.post(f"/api/v1/repo-reviews/{review['id']}/stages/{stage['id']}/findings", json={"severity": "HIGH", "category": "injection", "title": "SQL injection risk", "file_path": "src/db.py", "line_number": 42, "remediation": "Use parameterized queries"}, headers=auth(user))).json()
    assert f1["severity"] == "HIGH"
    assert f1["line_number"] == 42

    f2 = (await client.post(f"/api/v1/repo-reviews/{review['id']}/stages/{stage['id']}/findings", json={"severity": "LOW", "category": "style", "title": "Missing type hints"}, headers=auth(user))).json()
    assert f2["severity"] == "LOW"

    # List per stage
    findings = (await client.get(f"/api/v1/repo-reviews/{review['id']}/stages/{stage['id']}/findings", headers=auth(user))).json()
    assert len(findings) == 2

    # List all findings for review (filtered by severity)
    highs = (await client.get(f"/api/v1/repo-reviews/{review['id']}/findings?severity=HIGH", headers=auth(user))).json()
    assert len(highs) == 1
    assert highs[0]["title"] == "SQL injection risk"


# ===========================================================================
# Review Report (4-way classification)
# ===========================================================================

@pytest.mark.asyncio
async def test_review_report_generate_and_get(client: AsyncClient, db):
    user = await create_user(db, "rep1@example.com")
    review = (await client.post("/api/v1/repo-reviews", json={"repo_url": "https://github.com/i/j", "repo_name": "i/j"}, headers=auth(user))).json()

    # Add stages
    for st in ["license", "security", "dependency", "capability", "integration"]:
        await client.post(f"/api/v1/repo-reviews/{review['id']}/stages", json={"stage_type": st, "verdict": "pass", "score": 0.9}, headers=auth(user))

    # Generate report
    report = (await client.post(f"/api/v1/repo-reviews/{review['id']}/report", json={
        "classification": "use_directly",
        "overall_score": 0.9,
        "executive_summary": "This repo is production-ready.",
        "stage_scores": {"license": 1.0, "security": 0.9, "dependency": 0.85, "capability": 0.9, "integration": 0.95},
        "recommendations": ["Pin dependency versions"],
        "blockers": [],
        "format": "markdown",
        "content": "# Review Report\n\nAll stages passed.",
    }, headers=auth(user))).json()
    assert report["classification"] == "use_directly"
    assert report["overall_score"] == 0.9
    assert report["recommendations"] == ["Pin dependency versions"]

    # Get report
    fetched = (await client.get(f"/api/v1/repo-reviews/{review['id']}/report", headers=auth(user))).json()
    assert fetched["id"] == report["id"]

    # Verify review now has classification set
    updated_review = (await client.get(f"/api/v1/repo-reviews/{review['id']}", headers=auth(user))).json()
    assert updated_review["classification"] == "use_directly"
    assert updated_review["overall_score"] == 0.9


@pytest.mark.asyncio
async def test_review_report_duplicate(client: AsyncClient, db):
    user = await create_user(db, "rep2@example.com")
    review = (await client.post("/api/v1/repo-reviews", json={"repo_url": "https://github.com/k/l", "repo_name": "k/l"}, headers=auth(user))).json()
    payload = {"classification": "modify_first", "overall_score": 0.6, "stage_scores": {}}
    await client.post(f"/api/v1/repo-reviews/{review['id']}/report", json=payload, headers=auth(user))
    # Second generate should 409
    resp = await client.post(f"/api/v1/repo-reviews/{review['id']}/report", json=payload, headers=auth(user))
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_review_report_not_found(client: AsyncClient, db):
    user = await create_user(db, "rep3@example.com")
    review = (await client.post("/api/v1/repo-reviews", json={"repo_url": "https://github.com/m/n", "repo_name": "m/n"}, headers=auth(user))).json()
    assert (await client.get(f"/api/v1/repo-reviews/{review['id']}/report", headers=auth(user))).status_code == 404


@pytest.mark.asyncio
async def test_review_filter_by_classification(client: AsyncClient, db):
    user = await create_user(db, "rep4@example.com")
    r1 = (await client.post("/api/v1/repo-reviews", json={"repo_url": "https://github.com/o/p", "repo_name": "o/p"}, headers=auth(user))).json()
    r2 = (await client.post("/api/v1/repo-reviews", json={"repo_url": "https://github.com/q/r", "repo_name": "q/r"}, headers=auth(user))).json()
    await client.post(f"/api/v1/repo-reviews/{r1['id']}/report", json={"classification": "do_not_use", "overall_score": 0.1, "stage_scores": {}}, headers=auth(user))
    await client.post(f"/api/v1/repo-reviews/{r2['id']}/report", json={"classification": "reference_only", "overall_score": 0.5, "stage_scores": {}}, headers=auth(user))
    # Update review status/classification
    await client.patch(f"/api/v1/repo-reviews/{r1['id']}/status", json={"status": "completed", "classification": "do_not_use"}, headers=auth(user))
    results = (await client.get("/api/v1/repo-reviews?classification=do_not_use", headers=auth(user))).json()
    assert all(rv["classification"] == "do_not_use" for rv in results)
