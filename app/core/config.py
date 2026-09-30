"""Application settings loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

APP_DIR = Path(__file__).resolve().parent.parent
BASE_DIR = APP_DIR.parent


class Settings(BaseSettings):
    """Typed configuration for the whole application."""

    model_config = SettingsConfigDict(
        env_file=(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Application
    APP_NAME: str = "Cafetería API"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    VERSION: str = "1.0.0"

    # Database
    DATABASE_URL: str = "sqlite:///./cafeteria.db"
    DATABASE_ECHO: bool = False

    # Security
    SECRET_KEY: SecretStr = SecretStr("insecure-development-key-change-me")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: list[str] = Field(default_factory=lambda: ["http://localhost:8000"])

    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    # Web panel
    COOKIE_NAME: str = "cafeteria_session"
    SESSION_COOKIE_SECURE: bool = False

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        """Allow a comma separated string for CORS_ORIGINS."""
        if isinstance(value, str) and not value.strip().startswith("["):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def templates_dir(self) -> Path:
        """Absolute path to the Jinja2 templates directory."""
        return APP_DIR / "web" / "templates"

    @property
    def static_dir(self) -> Path:
        """Absolute path to the static assets directory."""
        return APP_DIR / "web" / "static"

    @property
    def is_production(self) -> bool:
        """True when running with ENVIRONMENT=production."""
        return self.ENVIRONMENT.lower() == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached application settings."""
    return Settings()
