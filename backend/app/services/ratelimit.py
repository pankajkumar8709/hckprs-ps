"""F3.4 — rate limiting & API abuse protection (slowapi).

Per-user when the request carries a bearer token (keyed on the JWT subject),
otherwise per-IP. Global default limit + tighter limits on abuse-prone routes
(auth, upload, chat). Limits are read from .env (RATE_LIMIT_PER_MIN) and can be
disabled in tests via RATE_LIMIT_ENABLED=false.
"""
from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from app.config import settings
from app.security import decode_token


def _key(request: Request) -> str:
    """Rate-limit key: user id from a valid bearer token, else client IP."""
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        try:
            payload = decode_token(auth.split(" ", 1)[1], expected_type="access")
            return f"user:{payload.get('sub')}"
        except Exception:
            pass
    return f"ip:{get_remote_address(request)}"


# When disabled (tests), use a key that returns a constant so limits never trip
# would still count — instead we set default_limits empty and rely on enabled flag.
limiter = Limiter(
    key_func=_key,
    default_limits=[f"{settings.RATE_LIMIT_PER_MIN}/minute"] if settings.RATE_LIMIT_ENABLED else [],
    enabled=settings.RATE_LIMIT_ENABLED,
)

# Tighter limits for abuse-prone routes (used as decorators on the endpoints).
AUTH_LIMIT = "10/minute"      # login/register brute-force guard
UPLOAD_LIMIT = "20/minute"    # expensive pipeline
CHAT_LIMIT = "30/minute"      # LLM calls
