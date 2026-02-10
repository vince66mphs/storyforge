import logging
from collections.abc import AsyncIterator

import httpx
from ollama import AsyncClient, ResponseError

from app.core.config import get_settings
from app.core.exceptions import (
    GenerationError,
    ModelNotFoundError,
    ServiceTimeoutError,
    ServiceUnavailableError,
)

logger = logging.getLogger(__name__)

SERVICE_NAME = "Ollama"


class OllamaService:
    """Service for interacting with Ollama LLM and embedding models."""

    def __init__(self):
        settings = get_settings()
        self.client = AsyncClient(host=settings.ollama_host)
        self.default_model = settings.ollama_model
        self.embed_model = "nomic-embed-text:latest"

    async def generate(
        self,
        prompt: str,
        system: str = "",
        model: str | None = None,
        keep_alive: str | None = None,
    ) -> str:
        """Generate a complete text response.

        Args:
            prompt: The user prompt.
            system: Optional system prompt to set context/personality.
            model: Model name override (defaults to config ollama_model).

        Returns:
            The full generated text.

        Raises:
            ServiceUnavailableError: If Ollama cannot be reached.
            ServiceTimeoutError: If the request times out.
            GenerationError: If generation fails for other reasons.
        """
        model = model or self.default_model
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        logger.info("Generating with model=%s, prompt_len=%d", model, len(prompt))
        kwargs: dict = {"model": model, "messages": messages}
        if keep_alive is not None:
            kwargs["keep_alive"] = keep_alive
        try:
            response = await self.client.chat(**kwargs)
        except httpx.ConnectError as e:
            raise ServiceUnavailableError(SERVICE_NAME, str(e)) from e
        except httpx.TimeoutException as e:
            raise ServiceTimeoutError(SERVICE_NAME, timeout=0, detail=str(e)) from e
        except ResponseError as e:
            if "not found" in str(e).lower():
                raise ModelNotFoundError(model, str(e)) from e
            raise GenerationError(SERVICE_NAME, str(e)) from e
        except Exception as e:
            raise GenerationError(SERVICE_NAME, str(e)) from e

        content = response.message.content
        logger.info("Generated %d chars", len(content))
        return content

    async def generate_stream(
        self,
        prompt: str,
        system: str = "",
        model: str | None = None,
        keep_alive: str | None = None,
    ) -> AsyncIterator[str]:
        """Stream text generation token by token.

        Args:
            prompt: The user prompt.
            system: Optional system prompt.
            model: Model name override.

        Yields:
            Text chunks as they are generated.

        Raises:
            ServiceUnavailableError: If Ollama cannot be reached.
            ServiceTimeoutError: If the request times out.
            GenerationError: If generation fails for other reasons.
        """
        model = model or self.default_model
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        logger.info("Streaming with model=%s, prompt_len=%d", model, len(prompt))
        kwargs: dict = {"model": model, "messages": messages, "stream": True}
        if keep_alive is not None:
            kwargs["keep_alive"] = keep_alive
        try:
            stream = await self.client.chat(**kwargs)
        except httpx.ConnectError as e:
            raise ServiceUnavailableError(SERVICE_NAME, str(e)) from e
        except httpx.TimeoutException as e:
            raise ServiceTimeoutError(SERVICE_NAME, timeout=0, detail=str(e)) from e
        except ResponseError as e:
            if "not found" in str(e).lower():
                raise ModelNotFoundError(model, str(e)) from e
            raise GenerationError(SERVICE_NAME, str(e)) from e
        except Exception as e:
            raise GenerationError(SERVICE_NAME, str(e)) from e

        try:
            async for chunk in stream:
                if chunk.message.content:
                    yield chunk.message.content
        except httpx.ConnectError as e:
            raise ServiceUnavailableError(SERVICE_NAME, f"connection lost during streaming: {e}") from e
        except httpx.TimeoutException as e:
            raise ServiceTimeoutError(SERVICE_NAME, timeout=0, detail=f"stream timed out: {e}") from e
        except Exception as e:
            raise GenerationError(SERVICE_NAME, f"stream failed: {e}") from e

    async def create_embedding(self, text: str) -> list[float]:
        """Create a 768-dimensional embedding vector.

        Args:
            text: The text to embed.

        Returns:
            A list of 768 floats.

        Raises:
            ServiceUnavailableError: If Ollama cannot be reached.
            GenerationError: If embedding fails.
        """
        try:
            response = await self.client.embed(model=self.embed_model, input=text)
        except httpx.ConnectError as e:
            raise ServiceUnavailableError(SERVICE_NAME, str(e)) from e
        except httpx.TimeoutException as e:
            raise ServiceTimeoutError(SERVICE_NAME, timeout=0, detail=str(e)) from e
        except ResponseError as e:
            if "not found" in str(e).lower():
                raise ModelNotFoundError(self.embed_model, str(e)) from e
            raise GenerationError(SERVICE_NAME, f"embedding failed: {e}") from e
        except Exception as e:
            raise GenerationError(SERVICE_NAME, f"embedding failed: {e}") from e
        return response.embeddings[0]

    async def check_health(self) -> bool:
        """Check if Ollama is reachable.

        Returns:
            True if Ollama responds, False otherwise.
        """
        try:
            async with httpx.AsyncClient() as client:
                settings = get_settings()
                resp = await client.get(f"{settings.ollama_host}/api/tags", timeout=5.0)
                return resp.status_code == 200
        except Exception:
            return False
