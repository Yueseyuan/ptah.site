from datetime import timedelta

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token, hash_password
from app.models.user import User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def create_user(db, email: str = "test@example.com", password: str = "secret123", is_active: bool = True, is_admin: bool = False) -> User:
    user = User(email=email, hashed_password=hash_password(password), is_active=is_active, is_admin=is_admin)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    response = await client.post("/api/v1/auth/register", json={"email": "new@example.com", "password": "password123"})
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "new@example.com"
    assert data["is_active"] is True
    assert data["is_admin"] is False
    assert "id" in data
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, db):
    await create_user(db, email="dup@example.com")
    response = await client.post("/api/v1/auth/register", json={"email": "dup@example.com", "password": "password123"})
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_register_invalid_email(client: AsyncClient):
    response = await client.post("/api/v1/auth/register", json={"email": "not-an-email", "password": "password123"})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, db):
    await create_user(db, email="login@example.com", password="correct_pass")
    response = await client.post("/api/v1/auth/login", json={"email": "login@example.com", "password": "correct_pass"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, db):
    await create_user(db, email="user@example.com", password="correct_pass")
    response = await client.post("/api/v1/auth/login", json={"email": "user@example.com", "password": "wrong_pass"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    response = await client.post("/api/v1/auth/login", json={"email": "ghost@example.com", "password": "irrelevant"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_inactive_user(client: AsyncClient, db):
    await create_user(db, email="inactive@example.com", password="pass", is_active=False)
    response = await client.post("/api/v1/auth/login", json={"email": "inactive@example.com", "password": "pass"})
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_logout(client: AsyncClient, db):
    user = await create_user(db)
    token = create_access_token({"sub": str(user.id)})
    response = await client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_logout_unauthenticated(client: AsyncClient):
    response = await client.post("/api/v1/auth/logout")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Get /me
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_me_authenticated(client: AsyncClient, db):
    user = await create_user(db, email="me@example.com")
    token = create_access_token({"sub": str(user.id)})
    response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@example.com"
    assert data["id"] == user.id


@pytest.mark.asyncio
async def test_get_me_unauthenticated(client: AsyncClient):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_expired_token(client: AsyncClient, db):
    user = await create_user(db)
    token = create_access_token({"sub": str(user.id)}, expires_delta=timedelta(seconds=-1))
    response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_invalid_token(client: AsyncClient):
    response = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer totally.invalid.token"})
    assert response.status_code == 401
