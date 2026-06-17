"""Case management endpoint tests."""
import pytest


@pytest.fixture(scope="module")
def client_id(client):
    r = client.post("/api/clients/", json={
        "first_name": "Jane",
        "last_name": "Doe",
        "email": "jane@example.com",
    })
    assert r.status_code == 201
    return r.json()["id"]


def test_list_cases_empty(client):
    r = client.get("/api/cases/")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_create_case(client, client_id):
    r = client.post("/api/cases/", json={
        "client_id": client_id,
        "goal": "Remove inaccurate charge-off from Equifax",
    })
    assert r.status_code == 201
    data = r.json()
    assert "case_number" in data
    assert data["status"] == "intake"


def test_get_case(client, client_id):
    create = client.post("/api/cases/", json={"client_id": client_id})
    case_id = create.json()["id"]
    r = client.get(f"/api/cases/{case_id}")
    assert r.status_code == 200
    assert r.json()["id"] == case_id


def test_update_case_status(client, client_id):
    create = client.post("/api/cases/", json={"client_id": client_id})
    case_id = create.json()["id"]
    r = client.patch(f"/api/cases/{case_id}", json={"status": "active"})
    assert r.status_code == 200
    assert r.json()["status"] == "active"


def test_organizations_crud(client):
    r = client.post("/api/organizations/", json={"name": "Test Firm LLC", "email": "firm@example.com"})
    assert r.status_code == 201
    org_id = r.json()["id"]

    r = client.get(f"/api/organizations/{org_id}")
    assert r.status_code == 200
    assert r.json()["name"] == "Test Firm LLC"

    r = client.patch(f"/api/organizations/{org_id}", json={"phone": "555-1234"})
    assert r.status_code == 200
    assert r.json()["phone"] == "555-1234"


def test_metro2_findings_empty(client, client_id):
    create = client.post("/api/cases/", json={"client_id": client_id})
    case_id = create.json()["id"]
    r = client.get(f"/api/metro2/case/{case_id}")
    assert r.status_code == 200
    assert r.json() == []


def test_analytics_summary(client):
    resp = client.get("/api/analytics/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_cases" in data
    assert "total_findings" in data


def test_global_search(client):
    resp = client.get("/api/search/", params={"q": "ae"})
    assert resp.status_code == 200
    data = resp.json()
    assert "clients" in data and "cases" in data


def test_case_export(client):
    # Create a case first
    cr = client.post("/api/clients/", json={"first_name": "Export", "last_name": "Test", "email": "export@test.invalid"})
    assert cr.status_code == 201
    cas = client.post("/api/cases/", json={"client_id": cr.json()["id"]})
    assert cas.status_code == 201
    cid = cas.json()["id"]
    resp = client.get(f"/api/cases/{cid}/export")
    assert resp.status_code == 200
    data = resp.json()
    assert data["case"]["id"] == cid
    assert "findings" in data
    assert "system" in data
