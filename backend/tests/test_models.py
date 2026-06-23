from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from httpx import AsyncClient

from app.core.security import create_access_token, hash_password
from app.models.user import User
from app.providers.anthropic import AnthropicProvider
from app.providers.base import Message
from app.providers.ollama import OllamaProvider
from app.providers.openai_compat import LlamaCppProvider, OpenAICompatProvider, OpenAIProvider
from app.providers.registry import ProviderRegistry, reset_registry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def mock_response(json_data: dict, status_code: int = 200) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    return resp


def mock_client(get_resp=None, post_resp=None) -> AsyncMock:
    client = AsyncMock(spec=httpx.AsyncClient)
    if get_resp is not None:
        client.get.return_value = get_resp
    if post_resp is not None:
        client.post.return_value = post_resp
    return client


async def create_user(db, email="user@example.com", is_admin=False) -> User:
    user = User(email=email, hashed_password=hash_password("pass"), is_admin=is_admin)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


def auth(user: User) -> dict:
    return {"Authorization": f"Bearer {create_access_token({'sub': str(user.id)})}"}


# ---------------------------------------------------------------------------
# Ollama provider
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ollama_health_success():
    provider = OllamaProvider("http://localhost:11434", client=mock_client(
        get_resp=mock_response({"models": []})
    ))
    assert await provider.health() is True


@pytest.mark.asyncio
async def test_ollama_health_failure():
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get.side_effect = httpx.ConnectError("refused")
    provider = OllamaProvider("http://localhost:11434", client=client)
    assert await provider.health() is False


@pytest.mark.asyncio
async def test_ollama_list_models():
    provider = OllamaProvider("http://localhost:11434", client=mock_client(
        get_resp=mock_response({"models": [
            {"name": "llama3:8b", "details": {"context_length": 8192}},
            {"name": "mistral:7b", "details": {}},
        ]})
    ))
    models = await provider.list_models()
    assert len(models) == 2
    assert models[0].id == "llama3:8b"
    assert models[0].provider == "ollama"
    assert models[0].context_length == 8192


@pytest.mark.asyncio
async def test_ollama_list_models_on_error():
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get.side_effect = httpx.ConnectError("refused")
    provider = OllamaProvider("http://localhost:11434", client=client)
    assert await provider.list_models() == []


@pytest.mark.asyncio
async def test_ollama_complete():
    post_resp = mock_response({
        "model": "llama3:8b",
        "message": {"role": "assistant", "content": "Hello there!"},
        "done": True,
    })
    provider = OllamaProvider("http://localhost:11434", client=mock_client(post_resp=post_resp))
    result = await provider.complete([Message("user", "Hi")], model="llama3:8b")
    assert result.content == "Hello there!"
    assert result.model == "llama3:8b"
    assert result.provider == "ollama"


# ---------------------------------------------------------------------------
# OpenAI-compatible provider
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_openai_compat_health_success():
    provider = OpenAICompatProvider("test", "http://localhost:1234", client=mock_client(
        get_resp=mock_response({"data": []})
    ))
    assert await provider.health() is True


@pytest.mark.asyncio
async def test_openai_compat_health_failure():
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get.side_effect = httpx.ConnectError("refused")
    provider = OpenAICompatProvider("test", "http://localhost:1234", client=client)
    assert await provider.health() is False


@pytest.mark.asyncio
async def test_openai_compat_list_models():
    provider = OpenAICompatProvider("lmstudio", "http://localhost:1234", client=mock_client(
        get_resp=mock_response({"data": [
            {"id": "mistral-7b-instruct"},
            {"id": "codellama-13b"},
        ]})
    ))
    models = await provider.list_models()
    assert len(models) == 2
    assert models[0].id == "mistral-7b-instruct"
    assert models[0].provider == "lmstudio"


@pytest.mark.asyncio
async def test_openai_compat_complete():
    post_resp = mock_response({
        "id": "cmpl-1",
        "model": "mistral-7b",
        "choices": [{"message": {"role": "assistant", "content": "42"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 1},
    })
    provider = OpenAICompatProvider("test", "http://localhost:1234", client=mock_client(post_resp=post_resp))
    result = await provider.complete([Message("user", "What is 6 * 7?")], model="mistral-7b")
    assert result.content == "42"
    assert result.input_tokens == 10
    assert result.output_tokens == 1


@pytest.mark.asyncio
async def test_llamacpp_name():
    p = LlamaCppProvider("http://localhost:8080")
    assert p.name == "llamacpp"


# ---------------------------------------------------------------------------
# Anthropic provider
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_anthropic_health_with_key():
    provider = AnthropicProvider(api_key="sk-test")
    assert await provider.health() is True


@pytest.mark.asyncio
async def test_anthropic_health_no_key():
    provider = AnthropicProvider(api_key="")
    assert await provider.health() is False


@pytest.mark.asyncio
async def test_anthropic_list_models_static():
    provider = AnthropicProvider(api_key="sk-test")
    models = await provider.list_models()
    assert len(models) == 3
    assert any(m.id == "claude-sonnet-4-6" for m in models)


@pytest.mark.asyncio
async def test_anthropic_complete():
    post_resp = mock_response({
        "id": "msg-1",
        "model": "claude-sonnet-4-6",
        "content": [{"type": "text", "text": "Hello!"}],
        "usage": {"input_tokens": 5, "output_tokens": 2},
    })
    provider = AnthropicProvider("sk-test", client=mock_client(post_resp=post_resp))
    result = await provider.complete(
        [Message("system", "You are helpful."), Message("user", "Hi")],
        model="claude-sonnet-4-6",
    )
    assert result.content == "Hello!"
    assert result.provider == "anthropic"
    assert result.input_tokens == 5


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

def test_registry_register_and_get():
    registry = ProviderRegistry()
    p = OllamaProvider("http://localhost:11434")
    registry.register(p)
    assert registry.get("ollama") is p
    assert "ollama" in registry.names()


def test_registry_get_missing():
    registry = ProviderRegistry()
    assert registry.get("nonexistent") is None


def test_registry_all():
    registry = ProviderRegistry()
    registry.register(OllamaProvider("http://a"))
    registry.register(LlamaCppProvider("http://b"))
    assert len(registry.all()) == 2


# ---------------------------------------------------------------------------
# Models endpoints
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_providers_endpoint(client: AsyncClient, db):
    user = await create_user(db)
    with patch("app.api.v1.endpoints.models.get_registry") as mock_reg:
        mock_provider = MagicMock()
        mock_provider.name = "ollama"
        mock_provider.health = AsyncMock(return_value=True)
        mock_provider.list_models = AsyncMock(return_value=[])
        mock_reg.return_value.all.return_value = [mock_provider]

        resp = await client.get("/api/v1/models/providers", headers=auth(user))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "ollama"
        assert data[0]["healthy"] is True


@pytest.mark.asyncio
async def test_get_provider_endpoint(client: AsyncClient, db):
    user = await create_user(db, email="m2@example.com")
    with patch("app.api.v1.endpoints.models.get_registry") as mock_reg:
        from app.providers.base import ModelInfo
        mock_provider = MagicMock()
        mock_provider.name = "ollama"
        mock_provider.health = AsyncMock(return_value=True)
        mock_provider.list_models = AsyncMock(return_value=[
            ModelInfo(id="llama3:8b", name="llama3:8b", provider="ollama")
        ])
        mock_reg.return_value.get.return_value = mock_provider

        resp = await client.get("/api/v1/models/providers/ollama", headers=auth(user))
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "ollama"
        assert len(data["models"]) == 1


@pytest.mark.asyncio
async def test_get_unknown_provider_404(client: AsyncClient, db):
    user = await create_user(db, email="m3@example.com")
    with patch("app.api.v1.endpoints.models.get_registry") as mock_reg:
        mock_reg.return_value.get.return_value = None
        resp = await client.get("/api/v1/models/providers/unknown", headers=auth(user))
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_all_models_endpoint(client: AsyncClient, db):
    user = await create_user(db, email="m4@example.com")
    with patch("app.api.v1.endpoints.models.get_registry") as mock_reg:
        from app.providers.base import ModelInfo
        mock_provider = MagicMock()
        mock_provider.health = AsyncMock(return_value=True)
        mock_provider.list_models = AsyncMock(return_value=[
            ModelInfo(id="llama3:8b", name="llama3:8b", provider="ollama"),
        ])
        mock_reg.return_value.all.return_value = [mock_provider]

        resp = await client.get("/api/v1/models", headers=auth(user))
        assert resp.status_code == 200
        assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_models_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/v1/models")
    assert resp.status_code == 401
