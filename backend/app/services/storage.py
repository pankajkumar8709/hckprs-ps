"""Object storage — Phase 1 MVP local-disk backend (Section 0.1, STORAGE_BACKEND=local).

Files are written under backend/storage/<user_id>/<uuid>__<filename>. S3 is a later
swap; the interface (save -> storage_path) stays the same.
"""
from __future__ import annotations

import re
import uuid
from pathlib import Path

_STORAGE_ROOT = Path(__file__).resolve().parents[2] / "storage"


def _safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", name)[:200] or "file"


def save_file(user_id: uuid.UUID, filename: str, data: bytes) -> str:
    """Persist bytes to local disk and return the storage path (str)."""
    user_dir = _STORAGE_ROOT / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    dest = user_dir / f"{uuid.uuid4().hex}__{_safe_name(filename)}"
    dest.write_bytes(data)
    return str(dest)
