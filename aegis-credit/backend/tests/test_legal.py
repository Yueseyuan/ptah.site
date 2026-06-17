"""Tests for legal knowledge engine endpoints and legal update workflow."""
import pytest


def test_list_federal_laws(client):
    r = client.get("/api/legal/federal")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_search_legal(client):
    r = client.get("/api/legal/search?q=fair")
    assert r.status_code == 200
    data = r.json()
    assert "federal_laws" in data


def test_list_state_laws(client):
    r = client.get("/api/legal/state")
    assert r.status_code == 200


def test_list_guidance(client):
    r = client.get("/api/legal/guidance")
    assert r.status_code == 200


def test_create_federal_law(client):
    r = client.post("/api/legal/federal", json={
        "short_name": "TEST",
        "title": "Test Statute",
        "citation": "15 U.S.C. § 9999",
        "section": "§9999",
        "summary": "Test statute for testing purposes",
        "category": "test",
    })
    assert r.status_code == 201
    assert r.json()["short_name"] == "TEST"


def test_create_state_law(client):
    r = client.post("/api/legal/state", json={
        "state": "SC",
        "statute": "SC Test Law",
        "citation": "SC Code § 99-1",
        "topic": "test",
        "summary": "Test state law",
    })
    assert r.status_code == 201


def test_create_case_law(client):
    r = client.post("/api/legal/cases", json={
        "case_name": "Test v. Bureau",
        "citation": "123 F.3d 456",
        "court": "9th Circuit",
        "jurisdiction": "Federal",
        "year": 2024,
        "topic": "FCRA accuracy",
        "holding_summary": "Test holding",
        "legal_principle": "Test principle",
    })
    assert r.status_code == 201


def test_legal_updates_workflow(client):
    # Submit update
    r = client.post("/api/legal-updates/", json={
        "update_type": "federal",
        "title": "Test Update",
        "summary": "Test legal update",
        "proposed_changes": '{"short_name": "TEST2", "title": "Test2", "citation": "15 U.S.C. § 9998", "summary": "test", "category": "test"}',
    })
    assert r.status_code == 201
    update_id = r.json()["id"]

    # List updates
    r = client.get("/api/legal-updates/")
    assert r.status_code == 200

    # Approve update
    r = client.post(f"/api/legal-updates/{update_id}/approve")
    assert r.status_code == 200
    assert r.json()["status"] == "approved"
