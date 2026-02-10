from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://vince:password@localhost:5432/storyforge"

    # Ollama
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "dolphin-mistral:7b"

    # Writer models per content mode
    writer_model_unrestricted: str = "dolphin-mistral:7b"
    writer_model_safe: str = "dolphin-mistral:7b"

    # MoA (Mixture of Agents) — Planner/Writer split
    planner_model: str = "phi4:latest"
    moa_enabled: bool = True
    planner_keep_alive: str = "24h"
    writer_keep_alive: str = "24h"

    # ComfyUI
    comfyui_host: str = "http://localhost:8188"

    # Illustration (IP-Adapter scene images)
    ipadapter_enabled: bool = True
    ipadapter_weight: float = 0.7
    scene_image_width: int = 1024
    scene_image_height: int = 576

    # Application
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"

    # Paths
    static_dir: str = "/home/vince/storyforge/static"
    export_dir: str = "/home/vince/storyforge/exports"
    workflow_dir: str = "/home/vince/storyforge/workflows"
    frontend_dir: str = "/home/vince/storyforge/frontend"

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
