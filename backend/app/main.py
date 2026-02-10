import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api import stories, nodes, entities
from app.api.websocket import router as ws_router
from app.core.config import get_settings
from app.core.exceptions import (
    GenerationError,
    ServiceTimeoutError,
    ServiceUnavailableError,
    StoryForgeError,
)

logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title="StoryForge 2.0",
    description="AI-powered interactive storytelling with dynamic illustrations",
    version="0.1.0",
)


# --- Global exception handlers ---

@app.exception_handler(ServiceUnavailableError)
async def service_unavailable_handler(request: Request, exc: ServiceUnavailableError):
    logger.error("Service unavailable: %s", exc)
    return JSONResponse(
        status_code=503,
        content={
            "detail": str(exc),
            "service": exc.service,
            "error_type": "service_unavailable",
        },
    )


@app.exception_handler(ServiceTimeoutError)
async def service_timeout_handler(request: Request, exc: ServiceTimeoutError):
    logger.error("Service timeout: %s", exc)
    return JSONResponse(
        status_code=504,
        content={
            "detail": str(exc),
            "service": exc.service,
            "error_type": "service_timeout",
        },
    )


@app.exception_handler(GenerationError)
async def generation_error_handler(request: Request, exc: GenerationError):
    logger.error("Generation error: %s", exc)
    return JSONResponse(
        status_code=502,
        content={
            "detail": str(exc),
            "service": exc.service,
            "error_type": "generation_error",
        },
    )


@app.exception_handler(StoryForgeError)
async def storyforge_error_handler(request: Request, exc: StoryForgeError):
    logger.error("StoryForge error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={
            "detail": str(exc),
            "error_type": "internal_error",
        },
    )


# --- Routers ---

app.include_router(stories.router)
app.include_router(nodes.router)
app.include_router(entities.router)
app.include_router(ws_router)

# Serve generated images
app.mount("/static", StaticFiles(directory=settings.static_dir), name="static")

# Serve frontend assets (CSS, JS)
frontend_dir = Path(settings.frontend_dir)
if frontend_dir.exists():
    app.mount("/app", StaticFiles(directory=str(frontend_dir)), name="frontend")


@app.get("/health")
async def health_check():
    """Health check with optional service status.

    Returns basic health immediately. Service checks run concurrently
    and report status without blocking startup.
    """
    import asyncio
    from app.services.ollama_service import OllamaService
    from app.services.comfyui_service import ComfyUIService

    ollama_svc = OllamaService()
    comfyui_svc = ComfyUIService()

    ollama_ok, comfyui_ok = await asyncio.gather(
        ollama_svc.check_health(),
        comfyui_svc.check_health(),
    )

    services = {
        "ollama": "ok" if ollama_ok else "unavailable",
        "comfyui": "ok" if comfyui_ok else "unavailable",
    }

    all_ok = ollama_ok and comfyui_ok
    return {
        "status": "ok" if all_ok else "degraded",
        "version": "0.1.0",
        "services": services,
    }


@app.get("/")
async def root():
    """Serve the frontend SPA."""
    index = frontend_dir / "index.html"
    return FileResponse(str(index), media_type="text/html")
