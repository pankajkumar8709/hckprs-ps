"""Object storage — F3.3 secure document storage.

Files are ENCRYPTED AT REST with Fernet (AES-128-CBC + HMAC) before touching
disk, under backend/storage/<user_id>/<uuid>.enc. The plaintext filename is NOT
used on disk (opaque uuid), so a raw path is not guessable to a meaningful name.

Access is via SHORT-LIVED SIGNED URLs, never a static public path: sign_download
mints an HMAC token bound to (document_id, user_id, expiry); verify_download
checks it. An expired or tampered token is rejected.

Key: DOC_ENCRYPTION_KEY (a urlsafe base64 32-byte Fernet key) if set; otherwise
derived deterministically from JWT_SECRET so local dev works without extra setup.
Rotating JWT_SECRET/DOC_ENCRYPTION_KEY makes prior files unreadable (documented).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import time
import uuid
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings

_STORAGE_ROOT = Path(__file__).resolve().parents[2] / "storage"


def _fernet() -> Fernet:
    key = settings.DOC_ENCRYPTION_KEY.strip()
    if key:
        return Fernet(key.encode())
    # Derive a stable 32-byte key from JWT_SECRET (dev fallback).
    digest = hashlib.sha256(("docenc:" + settings.JWT_SECRET).encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def save_file(user_id: uuid.UUID, filename: str, data: bytes) -> str:
    """Encrypt bytes and persist. Returns the (opaque) storage path."""
    user_dir = _STORAGE_ROOT / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    dest = user_dir / f"{uuid.uuid4().hex}.enc"
    dest.write_bytes(_fernet().encrypt(data))
    return str(dest)


def read_file(storage_path: str) -> bytes:
    """Decrypt and return the original bytes. Raises on tamper/wrong key."""
    raw = Path(storage_path).read_bytes()
    return _fernet().decrypt(raw)


# ---------- F3.3 signed download URLs ----------
_SIGN_TTL_DEFAULT = 300  # 5 minutes


def _sign_key() -> bytes:
    return hashlib.sha256(("sign:" + settings.JWT_SECRET).encode()).digest()


def sign_download(document_id: uuid.UUID, user_id: uuid.UUID, ttl: int = _SIGN_TTL_DEFAULT) -> str:
    """Mint a short-lived token bound to (document_id, user_id, expiry)."""
    exp = int(time.time()) + ttl
    msg = f"{document_id}:{user_id}:{exp}".encode()
    sig = hmac.new(_sign_key(), msg, hashlib.sha256).hexdigest()
    return f"{exp}.{sig}"


def verify_download(document_id: uuid.UUID, user_id: uuid.UUID, token: str) -> bool:
    """True iff the token is valid AND not expired for this doc+user."""
    try:
        exp_str, sig = token.split(".", 1)
        exp = int(exp_str)
    except (ValueError, AttributeError):
        return False
    if exp < int(time.time()):
        return False  # expired
    msg = f"{document_id}:{user_id}:{exp}".encode()
    expected = hmac.new(_sign_key(), msg, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig)
