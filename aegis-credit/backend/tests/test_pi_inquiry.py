"""Tests for personal info and inquiry analysis endpoints."""
import pytest


def test_list_personal_info_empty(client):
    # Create a case first
    c = client.post("/api/clients/", json={"first_name": "PI", "last_name": "Test", "email": "pi@test.com"})
    client_id = c.json()["id"]
    case = client.post("/api/cases/", json={"client_id": client_id})
    case_id = case.json()["id"]

    r = client.get(f"/api/personal-info/case/{case_id}")
    assert r.status_code == 200
    assert r.json() == []


def test_pi_analyze_no_data(client):
    c = client.post("/api/clients/", json={"first_name": "PI2", "last_name": "Test", "email": "pi2@test.com"})
    case = client.post("/api/cases/", json={"client_id": c.json()["id"]})
    case_id = case.json()["id"]

    r = client.post(f"/api/personal-info/case/{case_id}/analyze")
    assert r.status_code == 200
    data = r.json()
    assert data["records_analyzed"] == 0


def test_list_inquiries_empty(client):
    c = client.post("/api/clients/", json={"first_name": "INQ", "last_name": "Test", "email": "inq@test.com"})
    case = client.post("/api/cases/", json={"client_id": c.json()["id"]})
    case_id = case.json()["id"]

    r = client.get(f"/api/inquiries/case/{case_id}")
    assert r.status_code == 200
    assert r.json() == []


def test_create_inquiry(client):
    c = client.post("/api/clients/", json={"first_name": "INQ2", "last_name": "Test", "email": "inq2@test.com"})
    case = client.post("/api/cases/", json={"client_id": c.json()["id"]})
    case_id = case.json()["id"]

    r = client.post("/api/inquiries/", json={
        "case_id": case_id,
        "bureau": "experian",
        "inquiry_type": "hard",
        "subscriber_name": "CHASE BANK",
        "inquiry_date": "2024-01-15",
    })
    assert r.status_code == 201
    assert r.json()["subscriber_name"] == "CHASE BANK"


def test_inquiry_analyze(client):
    c = client.post("/api/clients/", json={"first_name": "INQ3", "last_name": "Test", "email": "inq3@test.com"})
    case = client.post("/api/cases/", json={"client_id": c.json()["id"]})
    case_id = case.json()["id"]

    # Add 7 hard inquiries to trigger INQ-003
    for i in range(7):
        month = str(i + 1).zfill(2)
        client.post("/api/inquiries/", json={
            "case_id": case_id,
            "bureau": "equifax",
            "inquiry_type": "hard",
            "subscriber_name": f"CREDITOR_{i}",
            "inquiry_date": f"2024-{month}-15",
        })

    r = client.post(f"/api/inquiries/case/{case_id}/analyze")
    assert r.status_code == 200
    data = r.json()
    assert data["inquiries_analyzed"] == 7
    # Should detect high volume (INQ-003)
    assert data["findings_generated"] >= 1


def test_pi_service_rules():
    from app.services.pi_service import run_pi_analysis

    records = [
        {
            "bureau": "experian",
            "current_name": "JOHN DOE",
            "aliases": "[]",
            "current_address": "123 Main St",
            "previous_addresses": "[]",
            "current_employer": "ABC Corp",
            "previous_employers": "[]",
        },
        {
            "bureau": "equifax",
            "current_name": "JANE DOE",  # Different name -> PI-002
            "aliases": "[]",
            "current_address": "456 Oak Ave",  # Different address -> PI-001
            "previous_addresses": "[]",
            "current_employer": "XYZ Inc",    # Different employer -> PI-003
            "previous_employers": "[]",
        },
    ]

    findings = run_pi_analysis(records)
    rule_codes = [f["rule_code"] for f in findings]
    assert "PI-002" in rule_codes
    assert "PI-003" in rule_codes


def test_inquiry_service_rules():
    from app.services.inquiry_service import run_inquiry_analysis

    # 7 hard inquiries on same bureau -> INQ-003
    inquiries = [
        {"bureau": "experian", "inquiry_type": "hard", "subscriber_name": f"CRED_{i}", "inquiry_date": "2024-01-15"}
        for i in range(7)
    ]
    findings = run_inquiry_analysis(inquiries)
    assert any(f["rule_code"] == "INQ-003" for f in findings)
