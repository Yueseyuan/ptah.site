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


def test_add_finding_to_dispute(client):
    # Setup: client → case → tradeline → finding → dispute round
    cr = client.post("/api/clients/", json={"first_name": "Dispute", "last_name": "Link", "email": "dl@test.invalid"})
    assert cr.status_code == 201
    cas = client.post("/api/cases/", json={"client_id": cr.json()["id"]})
    assert cas.status_code == 201
    cid = cas.json()["id"]

    # Create a finding
    f = client.post("/api/findings/", json={
        "case_id": cid, "finding_type": "collection", "severity": "high",
        "title": "COL-001: Known Debt Buyer", "description": "Test finding",
        "fcra_section": "FCRA §623",
    })
    assert f.status_code == 201
    fid = f.json()["id"]

    # Create a dispute round
    r = client.post("/api/disputes/rounds/", json={
        "case_id": cid, "round_number": 1, "bureau": "experian", "status": "draft",
    })
    assert r.status_code in (200, 201), r.text
    rid = r.json()["id"]

    # Add finding to dispute round
    resp = client.post("/api/disputes/add-finding", json={
        "finding_id": fid, "round_id": rid,
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["round_id"] == rid
    assert data["finding_id"] == fid

    # Finding status should now be "in_dispute"
    f2 = client.get(f"/api/findings/case/{cid}")
    assert f2.status_code == 200
    updated = next((x for x in f2.json() if x["id"] == fid), None)
    assert updated["status"] == "in_dispute"


def test_list_cases_by_client(client):
    cr = client.post("/api/clients/", json={"first_name": "Filter", "last_name": "Test", "email": "ft@test.invalid"})
    assert cr.status_code == 201
    cid = cr.json()["id"]
    c1 = client.post("/api/cases/", json={"client_id": cid, "goal": "Case A"})
    c2 = client.post("/api/cases/", json={"client_id": cid, "goal": "Case B"})
    assert c1.status_code == 201 and c2.status_code == 201
    r = client.get(f"/api/cases/?client_id={cid}")
    assert r.status_code == 200
    cases = r.json()
    assert len(cases) == 2
    assert all(c["client_id"] == cid for c in cases)


def test_analyze_all(client):
    cr = client.post("/api/clients/", json={"first_name": "AllEngine", "last_name": "Test", "email": "ae@test.invalid"})
    assert cr.status_code == 201
    cas = client.post("/api/cases/", json={"client_id": cr.json()["id"]})
    assert cas.status_code == 201
    cid = cas.json()["id"]
    # Run analyze-all with no data — should return empty findings, not error
    r = client.post(f"/api/cases/{cid}/analyze-all")
    assert r.status_code == 200
    data = r.json()
    assert "total_findings" in data
    assert isinstance(data["total_findings"], int)
