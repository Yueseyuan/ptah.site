"""Auth endpoint tests."""
import pytest


def test_register_first_user_becomes_admin(client):
    r = client.post("/api/auth/register", json={
        "username": "admin_test",
        "email": "admin_test@example.com",
        "password": "TestPass123!",
        "full_name": "Admin Test",
    })
    assert r.status_code == 201
    data = r.json()
    assert data["username"] == "admin_test"
    assert data["role"] == "admin"


def test_login_returns_token(client):
    r = client.post(
        "/api/auth/login",
        data={"username": "admin_test", "password": "TestPass123!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client):
    r = client.post(
        "/api/auth/login",
        data={"username": "admin_test", "password": "wrongpassword"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert r.status_code == 401


def test_register_duplicate_username(client):
    r = client.post("/api/auth/register", json={
        "username": "admin_test",
        "email": "other@example.com",
        "password": "TestPass123!",
    })
    assert r.status_code == 400


def test_get_me_dev_mode(client):
    r = client.get("/api/auth/me")
    assert r.status_code == 200
