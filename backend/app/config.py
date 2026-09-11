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
    LLM_PROVIDER: str = "auto"  # auto | gemini | groq
    LLM_MODEL: str = ""
    STORAGE_BACKEND: str = "local"
    S3_BUCKET: str = ""
    REDIS_URL: str = ""
    RATE_LIMIT_PER_MIN: int = 60
    # F3.3 — document encryption at rest (Fernet key, base64). Auto-generated
    # from JWT_SECRET if unset so local dev works; set explicitly in prod.
    DOC_ENCRYPTION_KEY: str = ""
    # F3.12 — production hardening flag. Default False (safe for prod);
    # set DEBUG=true in backend/.env for local development.
    DEBUG: bool = False
    # F3.4 — allow disabling rate limiting in tests.
    RATE_LIMIT_ENABLED: bool = True
    # F3.9 — when true, uploads enqueue a job for the worker instead of running
    # the pipeline inline. Default false keeps the synchronous MVP behavior.
    ASYNC_INGEST: bool = False
    # F3.12 — allowed CORS origins, comma-separated. Default is the local dev
    # frontend; set to your deployed frontend origin(s) in prod, e.g.
    #   CORS_ORIGINS=https://app.example.com,https://www.example.com
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    def cors_origins(self) -> list[str]:
        """Parse CORS_ORIGINS into a clean list of allowed origins."""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()

# F3.1 — fail fast if the JWT signing secret is empty/trivially short. Signing
# tokens with "" is a critical auth weakness; refuse to start rather than do it
# silently. Threshold kept at 8 to not break existing dev secrets; production
# should use a 32+ char random secret (documented in threat-model.md).
if not settings.JWT_SECRET or len(settings.JWT_SECRET) < 8:
    import os as _os
    if _os.environ.get("LIFEOS_ALLOW_INSECURE") != "1":
        raise RuntimeError(
            "JWT_SECRET is missing or too short (<8 chars). Set a strong "
            "JWT_SECRET in backend/.env (32+ random chars recommended). "
            "(Set LIFEOS_ALLOW_INSECURE=1 to bypass for local testing only.)"
        )
