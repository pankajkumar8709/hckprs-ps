"""F3.3 — secure document storage checklist.

- Confirm the raw stored file is ENCRYPTED (plaintext not present on disk).
- Confirm a signed download URL works, and an expired/tampered token is rejected.
Run: cd backend && .venv\\Scripts\\python.exe -m pytest tests/test_storage.py -v
"""
from __future__ import annotations

import io
import time
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.services import storage

client = TestClient(app)
SECRET_TEXT = "SUPER_SECRET_LEASE_CLAUSE_XYZ123"


def _txt_upload(tok: str):
    files = {"file": ("secret.txt", SECRET_TEXT.encode(), "text/plain")}
    return client.post("/documents/upload", headers={"Authorization": f"Bearer {tok}"}, files=files)


def _login() -> str:
    e = f"stor_{uuid.uuid4().hex[:8]}@test.com"
    client.post("/auth/register", json={"email": e, "password": "password123"})
    return client.post("/auth/login", json={"email": e, "password": "password123"}).json()["access_token"]


def test_file_encrypted_at_rest():
    tok = _login()
    r = _txt_upload(tok)
    assert r.status_code == 201, r.text
    doc = client.get(f"/documents/{r.json()['id']}", headers={"Authorization": f"Bearer {tok}"}).json()
    # find the storage path via the DB isn't exposed; instead read the newest .enc file
    # for this doc by asking the download route. But first: check disk directly.
    root = Path(storage._STORAGE_ROOT)
    enc_files = list(root.rglob("*.enc"))
    assert enc_files, "no .enc file written"
    # The most recent .enc must NOT contain the plaintext secret.
    newest = max(enc_files, key=lambda p: p.stat().st_mtime)
    raw = newest.read_bytes()
    assert SECRET_TEXT.encode() not in raw, "plaintext found in stored file — not encrypted!"
    # And decrypting it must recover the plaintext.
    assert SECRET_TEXT.encode() in storage.read_file(str(newest))


def test_signed_url_works_and_expires():
    tok = _login()
    r = _txt_upload(tok)
    doc_id = r.json()["id"]
    H = {"Authorization": f"Bearer {tok}"}
    # Mint a signed URL
    du = client.get(f"/documents/{doc_id}/download-url", headers=H).json()
    assert "url" in du
    # Valid token downloads the real content
    dl = client.get(du["url"])
    assert dl.status_code == 200
    assert SECRET_TEXT.encode() in dl.content

    # Tampered token → 403
    bad = du["url"].rsplit("token=", 1)[0] + "token=999999999.deadbeef"
    assert client.get(bad).status_code == 403

    # Expired token → 403 (mint one that already expired)
    uid = du["url"].split("uid=")[1].split("&")[0]
    expired = storage.sign_download(uuid.UUID(doc_id), uuid.UUID(uid), ttl=-10)
    assert client.get(f"/documents/{doc_id}/file?uid={uid}&token={expired}").status_code == 403


def test_no_bearer_no_download_url():
    # The mint route requires auth.
    r = client.get(f"/documents/{uuid.uuid4()}/download-url")
    assert r.status_code == 401
