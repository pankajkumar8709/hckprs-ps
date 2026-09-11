"""F3.4 — rate limiting checklist.

Fire rapid requests at a rate-limited route and confirm 429 responses kick in.
Uses /auth/login (AUTH_LIMIT = 10/minute). Runs in-process via TestClient.

NOTE: run this test on its OWN (it intentionally exhausts a limit bucket):
  cd backend && .venv\\Scripts\\python.exe -m pytest tests/test_ratelimit.py -v
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.services.ratelimit import limiter

client = TestClient(app)


def test_rapid_requests_get_429():
    if not limiter.enabled:
        import pytest
        pytest.skip("rate limiting disabled in this env")
    # Fire well past the global limit (RATE_LIMIT_PER_MIN/min) from one client.
    codes = []
    for _ in range(120):
        r = client.post("/auth/login", json={"email": "rl@test.com", "password": "x"})
        codes.append(r.status_code)
        if r.status_code == 429:
            break
    assert 429 in codes, f"no 429 after {len(codes)} rapid requests; got {set(codes)}"
    first_429 = codes.index(429) + 1
    print(f"429 first seen at request #{first_429}")
