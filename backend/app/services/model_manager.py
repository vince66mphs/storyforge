"""VRAM-aware model lifecycle manager for Ollama.

Provides a generation semaphore to serialize requests (prevents VRAM
contention on a single-user app) and helpers to preload/unload models.
"""

import asyncio
import logging

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class ModelManager:
    """Manages Ollama model loading and generation concurrency."""

    def __init__(self):
        self.generation_lock = asyncio.Semaphore(1)
        settings = get_settings()
        self._ollama_host = settings.ollama_host

    async def ensure_loaded(self, model: str, keep_alive: str = "24h") -> None:
        """Send a zero-token request to preload a model into VRAM."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self._ollama_host}/api/generate",
                    json={"model": model, "prompt": "", "keep_alive": keep_alive},
                    timeout=120.0,
                )
                if resp.status_code == 200:
                    logger.info("Model %s loaded (keep_alive=%s)", model, keep_alive)
                else:
                    logger.warning("Failed to preload %s: %d", model, resp.status_code)
        except Exception as e:
            logger.warning("Failed to preload %s: %s", model, e)

    async def unload(self, model: str) -> None:
        """Unload a model from VRAM via keep_alive=0."""
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{self._ollama_host}/api/generate",
                    json={"model": model, "prompt": "", "keep_alive": 0},
                    timeout=30.0,
                )
                logger.info("Unloaded model %s", model)
        except Exception as e:
            logger.warning("Failed to unload %s: %s", model, e)

    async def list_loaded(self) -> list[dict]:
        """Query Ollama for currently loaded models."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self._ollama_host}/api/ps",
                    timeout=10.0,
                )
                if resp.status_code == 200:
                    return resp.json().get("models", [])
        except Exception as e:
            logger.warning("Failed to list loaded models: %s", e)
        return []
