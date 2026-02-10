"""Tests for ComfyUIService — mocked httpx calls."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.core.exceptions import (
    GenerationError,
    ServiceTimeoutError,
    ServiceUnavailableError,
)
from app.services.comfyui_service import ComfyUIService


@pytest.fixture
def svc(tmp_path):
    service = ComfyUIService()
    service.static_dir = tmp_path / "images"
    service.static_dir.mkdir()
    service.poll_interval = 0.01  # Speed up polling in tests
    service.timeout = 0.1
    return service


def _mock_http_client(responses: list):
    """Build a mock httpx.AsyncClient that returns responses in order."""
    client = AsyncMock()
    client.post = AsyncMock(side_effect=responses[:])
    client.get = AsyncMock(side_effect=responses[:])
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return client


# ── queue_workflow ────────────────────────────────────────────────────

class TestQueueWorkflow:
    async def test_successful_queue(self, svc):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"prompt_id": "abc123"}
        mock_resp.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            result = await svc.queue_workflow({"test": "workflow"})
            assert result == "abc123"

    async def test_connect_error(self, svc):
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.ConnectError("refused")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            with pytest.raises(ServiceUnavailableError):
                await svc.queue_workflow({"test": "workflow"})

    async def test_timeout_error(self, svc):
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.TimeoutException("timeout")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            with pytest.raises(ServiceTimeoutError):
                await svc.queue_workflow({"test": "workflow"})

    async def test_http_error(self, svc):
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_resp = MagicMock()
            mock_resp.status_code = 400
            mock_resp.text = "Bad request"
            mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                "error", request=MagicMock(), response=mock_resp
            )
            mock_client.post.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            with pytest.raises(GenerationError):
                await svc.queue_workflow({"test": "workflow"})


# ── get_image ─────────────────────────────────────────────────────────

class TestGetImage:
    async def test_successful_retrieval(self, svc):
        with patch("httpx.AsyncClient") as MockClient:
            mock_resp = MagicMock()
            mock_resp.content = b"\x89PNG_fake_image"
            mock_resp.raise_for_status = MagicMock()
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            result = await svc.get_image("test.png")
            assert result == b"\x89PNG_fake_image"

    async def test_connect_error(self, svc):
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.ConnectError("refused")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            with pytest.raises(ServiceUnavailableError):
                await svc.get_image("test.png")


# ── _wait_for_completion ──────────────────────────────────────────────

class TestWaitForCompletion:
    async def test_immediate_completion(self, svc):
        output_data = {"outputs": {"9": {"images": [{"filename": "out.png"}]}}}

        with patch("httpx.AsyncClient") as MockClient:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"abc123": output_data}
            mock_resp.raise_for_status = MagicMock()
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            result = await svc._wait_for_completion("abc123")
            assert result == output_data

    async def test_timeout(self, svc):
        with patch("httpx.AsyncClient") as MockClient:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {}  # Never ready
            mock_resp.raise_for_status = MagicMock()
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            with pytest.raises(ServiceTimeoutError):
                await svc._wait_for_completion("abc123")

    async def test_error_status(self, svc):
        error_data = {
            "status": {"status_str": "error", "messages": "Node failed"},
        }

        with patch("httpx.AsyncClient") as MockClient:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"abc123": error_data}
            mock_resp.raise_for_status = MagicMock()
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            with pytest.raises(GenerationError):
                await svc._wait_for_completion("abc123")


# ── _save_output_image ────────────────────────────────────────────────

class TestSaveOutputImage:
    async def test_saves_image(self, svc):
        output = {
            "outputs": {
                "9": {"images": [{"filename": "result.png", "subfolder": ""}]}
            }
        }
        svc.get_image = AsyncMock(return_value=b"\x89PNG_data")

        result = await svc._save_output_image("prompt1", output)
        assert "prompt1_result.png" == result
        assert (svc.static_dir / "prompt1_result.png").read_bytes() == b"\x89PNG_data"

    async def test_no_images_raises(self, svc):
        output = {"outputs": {}}
        with pytest.raises(GenerationError):
            await svc._save_output_image("prompt1", output)


# ── upload_image ──────────────────────────────────────────────────────

class TestUploadImage:
    async def test_successful_upload(self, svc, tmp_path):
        img_file = tmp_path / "test.png"
        img_file.write_bytes(b"fake_png")

        with patch("httpx.AsyncClient") as MockClient:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"name": "test.png"}
            mock_resp.raise_for_status = MagicMock()
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            result = await svc.upload_image(str(img_file))
            assert result == "test.png"

    async def test_connect_error(self, svc, tmp_path):
        img_file = tmp_path / "test.png"
        img_file.write_bytes(b"fake_png")

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.ConnectError("refused")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            with pytest.raises(ServiceUnavailableError):
                await svc.upload_image(str(img_file))


# ── check_health ──────────────────────────────────────────────────────

class TestCheckHealth:
    async def test_healthy(self, svc):
        with patch("httpx.AsyncClient") as MockClient:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            assert await svc.check_health() is True

    async def test_unhealthy(self, svc):
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.side_effect = Exception("down")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            assert await svc.check_health() is False
