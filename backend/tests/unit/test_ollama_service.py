"""Tests for OllamaService — mocked AsyncClient."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from ollama import ResponseError

from app.core.exceptions import (
    GenerationError,
    ModelNotFoundError,
    ServiceTimeoutError,
    ServiceUnavailableError,
)
from app.services.ollama_service import OllamaService


@pytest.fixture
def svc(mock_ollama_client):
    service = OllamaService()
    service.client = mock_ollama_client
    return service


# ── generate ──────────────────────────────────────────────────────────

class TestGenerate:
    async def test_basic_generation(self, svc, mock_ollama_client):
        result = await svc.generate("Hello")
        assert result == "Generated text content"
        mock_ollama_client.chat.assert_called_once()

    async def test_with_system_prompt(self, svc, mock_ollama_client):
        await svc.generate("Hello", system="You are helpful")
        call_kwargs = mock_ollama_client.chat.call_args
        messages = call_kwargs.kwargs["messages"]
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

    async def test_custom_model(self, svc, mock_ollama_client):
        await svc.generate("Hello", model="phi4:latest")
        call_kwargs = mock_ollama_client.chat.call_args
        assert call_kwargs.kwargs["model"] == "phi4:latest"

    async def test_keep_alive_passed(self, svc, mock_ollama_client):
        await svc.generate("Hello", keep_alive="24h")
        call_kwargs = mock_ollama_client.chat.call_args
        assert call_kwargs.kwargs["keep_alive"] == "24h"

    async def test_connect_error_raises_unavailable(self, svc, mock_ollama_client):
        mock_ollama_client.chat.side_effect = httpx.ConnectError("refused")
        with pytest.raises(ServiceUnavailableError):
            await svc.generate("Hello")

    async def test_timeout_raises_timeout_error(self, svc, mock_ollama_client):
        mock_ollama_client.chat.side_effect = httpx.TimeoutException("timeout")
        with pytest.raises(ServiceTimeoutError):
            await svc.generate("Hello")

    async def test_model_not_found_error(self, svc, mock_ollama_client):
        mock_ollama_client.chat.side_effect = ResponseError("model 'foo' not found")
        with pytest.raises(ModelNotFoundError) as exc_info:
            await svc.generate("Hello", model="foo:latest")
        assert exc_info.value.model_name == "foo:latest"

    async def test_other_response_error_raises_generation_error(self, svc, mock_ollama_client):
        mock_ollama_client.chat.side_effect = ResponseError("bad model")
        with pytest.raises(GenerationError):
            await svc.generate("Hello")

    async def test_generic_error_raises_generation_error(self, svc, mock_ollama_client):
        mock_ollama_client.chat.side_effect = RuntimeError("unexpected")
        with pytest.raises(GenerationError):
            await svc.generate("Hello")


# ── generate_stream ───────────────────────────────────────────────────

class TestGenerateStream:
    async def test_stream_yields_chunks(self, svc, mock_ollama_client):
        chunk1 = MagicMock()
        chunk1.message.content = "Hello "
        chunk2 = MagicMock()
        chunk2.message.content = "world"

        async def mock_stream():
            yield chunk1
            yield chunk2

        mock_ollama_client.chat.return_value = mock_stream()

        chunks = []
        async for c in svc.generate_stream("Hello"):
            chunks.append(c)
        assert chunks == ["Hello ", "world"]

    async def test_stream_connect_error(self, svc, mock_ollama_client):
        mock_ollama_client.chat.side_effect = httpx.ConnectError("refused")
        with pytest.raises(ServiceUnavailableError):
            async for _ in svc.generate_stream("Hello"):
                pass

    async def test_stream_model_not_found(self, svc, mock_ollama_client):
        mock_ollama_client.chat.side_effect = ResponseError("model 'x' not found")
        with pytest.raises(ModelNotFoundError):
            async for _ in svc.generate_stream("Hello", model="x"):
                pass

    async def test_stream_skips_empty_chunks(self, svc, mock_ollama_client):
        chunk1 = MagicMock()
        chunk1.message.content = "data"
        chunk2 = MagicMock()
        chunk2.message.content = ""

        async def mock_stream():
            yield chunk1
            yield chunk2

        mock_ollama_client.chat.return_value = mock_stream()

        chunks = []
        async for c in svc.generate_stream("Hello"):
            chunks.append(c)
        assert chunks == ["data"]


# ── create_embedding ──────────────────────────────────────────────────

class TestCreateEmbedding:
    async def test_returns_embedding_vector(self, svc, mock_ollama_client):
        result = await svc.create_embedding("test text")
        assert len(result) == 768
        mock_ollama_client.embed.assert_called_once()

    async def test_connect_error(self, svc, mock_ollama_client):
        mock_ollama_client.embed.side_effect = httpx.ConnectError("refused")
        with pytest.raises(ServiceUnavailableError):
            await svc.create_embedding("test")

    async def test_embed_model_not_found(self, svc, mock_ollama_client):
        mock_ollama_client.embed.side_effect = ResponseError("model 'nomic' not found")
        with pytest.raises(ModelNotFoundError):
            await svc.create_embedding("test")

    async def test_response_error(self, svc, mock_ollama_client):
        mock_ollama_client.embed.side_effect = ResponseError("fail")
        with pytest.raises(GenerationError):
            await svc.create_embedding("test")


# ── check_health ──────────────────────────────────────────────────────

class TestCheckHealth:
    async def test_healthy(self, svc):
        with patch("httpx.AsyncClient") as MockClient:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_resp
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_instance
            assert await svc.check_health() is True

    async def test_unhealthy(self, svc):
        with patch("httpx.AsyncClient") as MockClient:
            mock_instance = AsyncMock()
            mock_instance.get.side_effect = httpx.ConnectError("refused")
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_instance
            assert await svc.check_health() is False
