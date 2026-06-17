"""Tests for organization endpoints."""
import pytest


def test_list_orgs_authenticated(client):
    r = client.get("/api/organizations/")
    assert r.status_code == 200


def test_create_and_get_org(client):
    r = client.post("/api/organizations/", json={"name": "Test Firm", "email": "firm@test.com"})
    assert r.status_code == 201
    org_id = r.json()["id"]
    r2 = client.get(f"/api/organizations/{org_id}")
    assert r2.status_code == 200
    assert r2.json()["name"] == "Test Firm"


def test_get_nonexistent_org(client):
    r = client.get("/api/organizations/99999")
    assert r.status_code == 404
