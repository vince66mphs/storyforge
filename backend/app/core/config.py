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

    # ComfyUI
    comfyui_host: str = "http://localhost:8188"

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
