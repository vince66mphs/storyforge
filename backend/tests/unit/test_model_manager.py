"""Tests for ModelManager — mocked httpx calls."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.model_manager import ModelManager


@pytest.fixture
def mm():
    return ModelManager()


class TestGenerationLock:
    async def test_lock_is_semaphore(self, mm):
        """Verify the generation lock is a semaphore with max 1."""
        assert mm.generation_lock._value == 1

    async def test_lock_serializes(self, mm):
        """Acquire the lock and verify it blocks."""
        await mm.generation_lock.acquire()
        # Should not be acquirable again without release
        assert not mm.generation_lock._value
        mm.generation_lock.release()


class TestEnsureLoaded:
    async def test_successful_preload(self, mm):
        with patch("httpx.AsyncClient") as MockClient:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            await mm.ensure_loaded("phi4:latest", keep_alive="24h")
            mock_client.post.assert_called_once()
            call_kwargs = mock_client.post.call_args
            assert "phi4:latest" in str(call_kwargs)

    async def test_preload_failure_logged_not_raised(self, mm):
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.ConnectError("refused")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            # Should not raise
            await mm.ensure_loaded("phi4:latest")


class TestUnload:
    async def test_successful_unload(self, mm):
        with patch("httpx.AsyncClient") as MockClient:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            await mm.unload("phi4:latest")
            call_json = mock_client.post.call_args.kwargs.get(
                "json", mock_client.post.call_args[1].get("json", {})
            )
            assert call_json.get("keep_alive") == 0

    async def test_unload_failure_silent(self, mm):
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post.side_effect = Exception("fail")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            await mm.unload("phi4:latest")  # Should not raise


class TestListLoaded:
    async def test_returns_models(self, mm):
        with patch("httpx.AsyncClient") as MockClient:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "models": [{"name": "phi4:latest"}]
            }
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            result = await mm.list_loaded()
            assert result == [{"name": "phi4:latest"}]

    async def test_returns_empty_on_failure(self, mm):
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.side_effect = Exception("fail")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            result = await mm.list_loaded()
            assert result == []
