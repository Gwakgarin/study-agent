"""Typed application settings, loaded from environment variables / .env."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str | None = None

    embedding_model: str = "text-embedding-3-small"
    chat_model: str = "gpt-4o-mini"
    quiz_model: str = "gpt-4o-mini"

    chunk_size: int = 800
    chunk_overlap: int = 100

    cors_origins: list[str] = ["http://localhost:5173"]

    db_path: Path = PROJECT_ROOT / "data" / "tracker.db"


settings = Settings()
