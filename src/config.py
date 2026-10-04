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

    # The OpenAI SDK already retries connection errors, 429 and 5xx with backoff.
    openai_timeout_seconds: float = 30.0
    openai_max_retries: int = 2
    max_tool_rounds: int = 6

    chunk_size: int = 800
    chunk_overlap: int = 100

    cors_origins: list[str] = ["http://localhost:5173"]

    # When set, every request except the health check needs HTTP Basic auth with this
    # password (any username). Keeps a public deployment from spending the OpenAI key.
    access_password: str | None = None

    # Accounts. With signup_code set, only people who know it can create an account.
    signup_code: str | None = None
    # Send the login cookie over HTTPS only (on for the Fly.io deployment).
    cookie_secure: bool = False

    # Per-user limits that keep one account from using up the OpenAI budget or disk.
    chat_limit_per_hour: int = 30
    max_upload_mb: int = 5
    max_notes_per_project: int = 20

    db_path: Path = PROJECT_ROOT / "data" / "tracker.db"


settings = Settings()
