"""F3.2 — automated tenant-isolation suite.

For every user-owned resource, attempts cross-user access as User B against
User A's data and asserts 404 / exclusion. Runs against the real app + live DB
via FastAPI TestClient. Requires the server env (.env with DATABASE_URL); no
running uvicorn needed — the TestClient drives the ASGI app in-process.

Run:  cd backend && .venv\\Scripts\\python.exe -m pytest tests/test_isolation.py -v
"""
from __future__ import annotations

import io
import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _pdf(text: str) -> bytes:
    esc = text.replace("(", r"\(").replace(")", r"\)")
    content = f"BT /F1 11 Tf 40 760 Td ({esc}) Tj ET".encode()
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length %d >>\nstream\n%s\nendstream" % (len(content), content),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = io.BytesIO(); out.write(b"%PDF-1.4\n"); offs = []
    for i, b in enumerate(objs, 1):
        offs.append(out.tell()); out.write(b"%d 0 obj\n%s\nendobj\n" % (i, b))
    x = out.tell(); out.write(b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1))
    for o in offs: out.write(b"%010d 00000 n \n" % o)
    out.write(b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF" % (len(objs) + 1, x))
    return out.getvalue()


def _register_login(email: str) -> str:
    client.post("/auth/register", json={"email": email, "password": "password123"})
    r = client.post("/auth/login", json={"email": email, "password": "password123"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _H(tok: str) -> dict:
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture(scope="module")
def two_users():
    a = _register_login(f"iso_a_{uuid.uuid4().hex[:8]}@test.com")
    b = _register_login(f"iso_b_{uuid.uuid4().hex[:8]}@test.com")
    # User A uploads a doc with a date (creates Document, ExtractedField, Reminder,
    # Insight-eligible data, DocumentChunk).
    up = client.post("/documents/upload", headers=_H(a),
                     files={"file": ("a_lease.pdf", _pdf(
                         "Lease for User A. Lease end date: 2027-05-01. Deposit: $2000."),
                         "application/pdf")})
    assert up.status_code == 201, up.text
    doc_id = up.json()["id"]
    # A chat message (creates Conversation + Message).
    client.post("/chat", headers=_H(a), json={"message": "When does my lease end?"})
    return {"a": a, "b": b, "doc_id": doc_id}


def test_document_detail_cross_user_404(two_users):
    r = client.get(f"/documents/{two_users['doc_id']}", headers=_H(two_users["b"]))
    assert r.status_code == 404, f"B read A's document: {r.status_code}"


def test_document_list_excludes_other_user(two_users):
    r = client.get("/documents", headers=_H(two_users["b"]))
    assert r.status_code == 200
    assert two_users["doc_id"] not in [d["id"] for d in r.json()]


def test_document_delete_cross_user_404(two_users):
    r = client.delete(f"/documents/{two_users['doc_id']}", headers=_H(two_users["b"]))
    assert r.status_code == 404, f"B deleted A's document: {r.status_code}"


def test_reminders_isolated(two_users):
    r = client.get("/reminders", headers=_H(two_users["b"]))
    assert r.status_code == 200
    assert r.json() == [], "B sees A's reminders"


def test_reminder_patch_cross_user_404(two_users):
    a_rems = client.get("/reminders", headers=_H(two_users["a"])).json()
    if a_rems:
        rid = a_rems[0]["id"]
        r = client.patch(f"/reminders/{rid}", headers=_H(two_users["b"]),
                         json={"status": "done"})
        assert r.status_code == 404, f"B patched A's reminder: {r.status_code}"


def test_insights_isolated(two_users):
    r = client.get("/insights", headers=_H(two_users["b"]))
    assert r.status_code == 200
    assert r.json() == [], "B sees A's insights"


def test_conversations_isolated(two_users):
    r = client.get("/chat/conversations", headers=_H(two_users["b"]))
    assert r.status_code == 200
    assert r.json() == [], "B sees A's conversations"


def test_chat_rag_no_cross_user_leak(two_users):
    # B (no documents) asks about A's lease — must not reveal A's data.
    r = client.post("/chat", headers=_H(two_users["b"]),
                    json={"message": "When does my lease end?"})
    assert r.status_code == 200
    ans = (r.json().get("message", {}).get("content") or "").lower()
    assert "2027-05-01" not in ans and "may 1" not in ans, f"RAG leaked A's data: {ans[:80]}"


def test_notifications_isolated(two_users):
    r = client.get("/notifications", headers=_H(two_users["b"]))
    assert r.status_code == 200
    # B has no docs, so no reminder/insight notifications from A.
    assert r.json().get("count", 0) == 0, "B sees A's notifications"


def test_unauthenticated_blocked():
    assert client.get("/documents").status_code == 401
    assert client.get("/reminders").status_code == 401
