"""F3.8 — data deletion / right-to-be-forgotten checklist.

- Delete a test account; query the vector store (document_chunks) DIRECTLY and
  confirm no embeddings remain for that user (not just the Postgres user row).
- Confirm login with the deleted credentials now fails.

Run: cd backend && .venv\\Scripts\\python.exe -m pytest tests/test_deletion.py -v -s
"""
from __future__ import annotations

import io
import uuid

from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models import (
    Document, DocumentChunk, ExtractedField, Reminder, Conversation, Message, User,
)

client = TestClient(app)


def _valid_pdf(text="Lease end date 2027-01-01 deposit 2000 tenant John") -> bytes:
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


def test_account_deletion_cascade_and_vector_removal():
    email = f"del_{uuid.uuid4().hex[:8]}@test.com"
    client.post("/auth/register", json={"email": email, "password": "password123"})
    tok = client.post("/auth/login", json={"email": email, "password": "password123"}).json()["access_token"]
    H = {"Authorization": f"Bearer {tok}"}

    up = client.post("/documents/upload", headers=H,
                     files={"file": ("l.pdf", _valid_pdf(), "application/pdf")})
    assert up.status_code == 201

    # Resolve the user id from the DB.
    s = SessionLocal()
    user = s.query(User).filter(User.email == email).first()
    uid = user.id
    # Confirm data exists BEFORE deletion.
    chunks_before = s.query(DocumentChunk).filter(DocumentChunk.user_id == uid).count()
    docs_before = s.query(Document).filter(Document.user_id == uid).count()
    s.close()
    print(f"before delete: docs={docs_before} chunks={chunks_before}")
    assert docs_before >= 1

    # DELETE the account.
    r = client.delete("/account", headers=H)
    assert r.status_code == 204, r.text

    # Query the vector store + other tables DIRECTLY (fresh session).
    s2 = SessionLocal()
    chunks_after = s2.query(DocumentChunk).filter(DocumentChunk.user_id == uid).count()
    docs_after = s2.query(Document).filter(Document.user_id == uid).count()
    fields_after = s2.query(ExtractedField).filter(ExtractedField.user_id == uid).count()
    rem_after = s2.query(Reminder).filter(Reminder.user_id == uid).count()
    conv_after = s2.query(Conversation).filter(Conversation.user_id == uid).count()
    user_after = s2.query(User).filter(User.id == uid).first()
    s2.close()
    print(f"after delete: docs={docs_after} chunks={chunks_after} fields={fields_after} "
          f"reminders={rem_after} convs={conv_after} user={user_after}")

    assert chunks_after == 0, "vector embeddings (document_chunks) NOT removed!"
    assert docs_after == 0 and fields_after == 0 and rem_after == 0 and conv_after == 0
    assert user_after is None, "user row still present"


def test_login_fails_after_deletion():
    email = f"del2_{uuid.uuid4().hex[:8]}@test.com"
    client.post("/auth/register", json={"email": email, "password": "password123"})
    tok = client.post("/auth/login", json={"email": email, "password": "password123"}).json()["access_token"]
    client.delete("/account", headers={"Authorization": f"Bearer {tok}"})
    # Login with deleted credentials must fail.
    r = client.post("/auth/login", json={"email": email, "password": "password123"})
    assert r.status_code == 401, f"deleted account still logs in: {r.status_code}"
