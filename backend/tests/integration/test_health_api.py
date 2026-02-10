"""Integration tests for health endpoint — mocked service checks."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


class TestHealthEndpoint:
    async def test_all_healthy(self, client: AsyncClient):
        with patch(
            "app.services.ollama_service.OllamaService.check_health",
            new_callable=AsyncMock,
            return_value=True,
        ), patch(
            "app.services.comfyui_service.ComfyUIService.check_health",
            new_callable=AsyncMock,
            return_value=True,
        ):
            resp = await client.get("/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "ok"
            assert data["services"]["ollama"] == "ok"
            assert data["services"]["comfyui"] == "ok"
            assert "version" in data

    async def test_ollama_down(self, client: AsyncClient):
        with patch(
            "app.services.ollama_service.OllamaService.check_health",
            new_callable=AsyncMock,
            return_value=False,
        ), patch(
            "app.services.comfyui_service.ComfyUIService.check_health",
            new_callable=AsyncMock,
            return_value=True,
        ):
            resp = await client.get("/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "degraded"
            assert data["services"]["ollama"] == "unavailable"

    async def test_both_down(self, client: AsyncClient):
        with patch(
            "app.services.ollama_service.OllamaService.check_health",
            new_callable=AsyncMock,
            return_value=False,
        ), patch(
            "app.services.comfyui_service.ComfyUIService.check_health",
            new_callable=AsyncMock,
            return_value=False,
        ):
            resp = await client.get("/health")
            data = resp.json()
            assert data["status"] == "degraded"
            assert data["services"]["ollama"] == "unavailable"
            assert data["services"]["comfyui"] == "unavailable"
