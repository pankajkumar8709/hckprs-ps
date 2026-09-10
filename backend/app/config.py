"""Application settings, loaded from backend/.env (Section 0.5)."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    DATABASE_URL: str = ""
    JWT_SECRET: str = ""
    JWT_ACCESS_EXPIRE_MIN: int = 15
    JWT_REFRESH_EXPIRE_DAYS: int = 7
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gemini-flash-latest"
    STORAGE_BACKEND: str = "local"
    S3_BUCKET: str = ""
    REDIS_URL: str = ""
    RATE_LIMIT_PER_MIN: int = 60


settings = Settings()
