"""Configuration from the repository .env, overridden by process environment."""

from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
    )

    database_url: SecretStr | None = None
    ai_service_url: str | None = None
    ai_health_url: str | None = None
    ai_wake_url: str | None = None
    ai_api_key: SecretStr | None = None
    ai_timeout_s: float = Field(default=8.0, gt=0, le=120, allow_inf_nan=False)
    ai_wake_rate_limit_s: int = Field(default=60, ge=1, le=3600)
    ai_warmup_grace_s: int = Field(default=15, ge=0, le=600)
    cors_allow_origins: str = (
        "http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:4173,http://localhost:4173"
    )
