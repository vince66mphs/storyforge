"""Custom exception hierarchy for StoryForge services."""


class StoryForgeError(Exception):
    """Base exception for all StoryForge errors."""


class ServiceUnavailableError(StoryForgeError):
    """Raised when an external service (Ollama, ComfyUI) cannot be reached."""

    def __init__(self, service: str, detail: str = ""):
        self.service = service
        self.detail = detail
        msg = f"{service} is unavailable"
        if detail:
            msg += f": {detail}"
        super().__init__(msg)


class ServiceTimeoutError(StoryForgeError):
    """Raised when an external service request times out."""

    def __init__(self, service: str, timeout: float, detail: str = ""):
        self.service = service
        self.timeout = timeout
        self.detail = detail
        msg = f"{service} request timed out after {timeout}s"
        if detail:
            msg += f": {detail}"
        super().__init__(msg)


class GenerationError(StoryForgeError):
    """Raised when text or image generation fails."""

    def __init__(self, service: str, detail: str = ""):
        self.service = service
        self.detail = detail
        msg = f"{service} generation failed"
        if detail:
            msg += f": {detail}"
        super().__init__(msg)


class ModelNotFoundError(GenerationError):
    """Raised when a requested model is not available in Ollama."""

    def __init__(self, model_name: str, detail: str = ""):
        self.model_name = model_name
        super().__init__(
            "Ollama",
            detail or f"model '{model_name}' not found — run: ollama pull {model_name}",
        )
