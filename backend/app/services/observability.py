"""F3.10 — observability: structured JSON logging + in-memory metrics.

- JSON logs with request_id and user_id on every line (contextvars carry them
  through the request without threading them by hand).
- A tiny in-memory metrics counter (request count, error count, latency sum)
  exposed at /metrics — enough to demonstrate the concept without a metrics
  backend.
"""
from __future__ import annotations

import contextvars
import json
import logging
import sys
import time

# Per-request context.
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")
user_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("user_id", default="-")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": request_id_var.get(),
            "user_id": user_id_var.get(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def setup_logging() -> None:
    root = logging.getLogger()
    # Avoid duplicate handlers on reload.
    if any(isinstance(h.formatter, JsonFormatter) for h in root.handlers):
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.handlers = [handler]
    root.setLevel(logging.INFO)


# ---------- metrics (in-memory) ----------
class _Metrics:
    def __init__(self) -> None:
        self.requests = 0
        self.errors = 0
        self.latency_sum = 0.0

    def record(self, status_code: int, latency_s: float) -> None:
        self.requests += 1
        if status_code >= 500:
            self.errors += 1
        self.latency_sum += latency_s

    def snapshot(self) -> dict:
        avg = (self.latency_sum / self.requests) if self.requests else 0.0
        rate = (self.errors / self.requests) if self.requests else 0.0
        return {
            "requests_total": self.requests,
            "errors_total": self.errors,
            "error_rate": round(rate, 4),
            "avg_latency_ms": round(avg * 1000, 2),
        }


metrics = _Metrics()
