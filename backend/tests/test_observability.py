"""F3.10 — observability checklist.

- /health reports 'unhealthy' when the DB is deliberately broken (tested, not assumed).
- /metrics exposes request count / error rate / avg latency.
- JSON log formatter includes request_id and user_id.

Run: cd backend && .venv\\Scripts\\python.exe -m pytest tests/test_observability.py -v
"""
from __future__ import annotations

import json
import logging

from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db
from app.services.observability import JsonFormatter, request_id_var

client = TestClient(app)


def test_health_healthy_normally():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "healthy"
    assert body["db"] == "reachable"
    assert body["queue"] == "reachable"


def test_health_unhealthy_when_db_broken():
    # Override the DB dependency with a session whose execute() raises.
    class BrokenDB:
        def execute(self, *a, **k):
            raise RuntimeError("db down")
    def broken():
        yield BrokenDB()
    app.dependency_overrides[get_db] = broken
    try:
        r = client.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "unhealthy", body
        assert body["db"] == "unreachable", body
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_metrics_exposed():
    client.get("/health")  # generate at least one request
    r = client.get("/metrics")
    assert r.status_code == 200
    m = r.json()
    assert "requests_total" in m and m["requests_total"] >= 1
    assert "error_rate" in m and "avg_latency_ms" in m


def test_json_log_has_context():
    request_id_var.set("req-123")
    rec = logging.LogRecord("t", logging.INFO, __file__, 1, "hello", None, None)
    out = json.loads(JsonFormatter().format(rec))
    assert out["request_id"] == "req-123"
    assert "user_id" in out and out["msg"] == "hello"
