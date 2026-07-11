"""Application configuration loaded from environment variables.

Uses pydantic-settings for type-safe configuration management.
All settings can be overridden via environment variables or a .env file.
"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """DocSprint application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Database ---
    DATABASE_URL: str = "postgresql+psycopg2://docsprint:docsprint@localhost:5432/docsprint"

    # --- Redis ---
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- Auth ---
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days
    ALGORITHM: str = "HS256"

    # --- Storage ---
    UPLOAD_DIR: str = "./data/uploads"
    RESULT_DIR: str = "./data/results"
    MAX_FILE_SIZE_MB: int = 20

    # --- Billing ---
    FREE_TIER_PAGES: int = 10
    STARTER_PAGES: int = 500
    PRO_PAGES: int = 2000

    # --- Model ---
    MODEL_ID: str = "Qwen/Qwen3.5-0.8B"
    MODEL_QUANTIZE_4BIT: bool = True

    # --- Environment ---
    DEV_MODE: bool = False  # When True, process documents synchronously (no Redis worker needed)
    RATE_LIMIT_ENABLED: bool = True
    FREE_RATE_LIMIT: int = 100  # requests per minute
    PRO_RATE_LIMIT: int = 1000

    # --- CORS ---
    CORS_ORIGINS: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS_ORIGINS into a list of allowed origins."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def upload_path(self) -> Path:
        """Resolved upload directory path."""
        p = Path(self.UPLOAD_DIR).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def result_path(self) -> Path:
        """Resolved results directory path."""
        p = Path(self.RESULT_DIR).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p


settings = Settings()