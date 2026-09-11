"""F3.7 — audit logging checklist.

Perform several sensitive actions and confirm they all appear, correctly
attributed, in GET /account/audit-log. Also confirm the log is user-scoped.

Run: cd backend && .venv\\Scripts\\python.exe -m pytest tests/test_audit.py -v
"""
from __future__ import annotations

import io
import uuid

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _valid_pdf(text="Invoice 2027-01-01 total 50") -> bytes:
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


def _register_login(email):
    client.post("/auth/register", json={"email": email, "password": "password123"})
    return client.post("/auth/login", json={"email": email, "password": "password123"}).json()["access_token"]


def test_five_sensitive_actions_logged():
    ea = f"aud_a_{uuid.uuid4().hex[:8]}@test.com"
    eb = f"aud_b_{uuid.uuid4().hex[:8]}@test.com"
    ta = _register_login(ea)          # action: login
    tb = _register_login(eb)
    Ha = {"Authorization": f"Bearer {ta}"}

    up = client.post("/documents/upload", headers=Ha,
                     files={"file": ("a.pdf", _valid_pdf(), "application/pdf")})  # upload
    doc_id = up.json()["id"]
    client.get(f"/documents/{doc_id}", headers=Ha)                                # access
    client.post(f"/documents/{doc_id}/share", headers=Ha,
                json={"shared_with_email": eb, "permission": "view"})             # share
    client.delete(f"/documents/{doc_id}", headers=Ha)                             # delete

    log = client.get("/account/audit-log", headers=Ha).json()
    actions = [e["action"] for e in log]
    for expected in ["login", "document.upload", "document.access",
                     "share.create", "document.delete"]:
        assert expected in actions, f"missing audit action {expected}; got {actions}"
    print("audit actions logged:", actions)


def test_audit_log_user_scoped():
    ea = f"aud_c_{uuid.uuid4().hex[:8]}@test.com"
    ta = _register_login(ea)
    log = client.get("/account/audit-log", headers={"Authorization": f"Bearer {ta}"}).json()
    # A brand-new user's log has only their own login(s), nothing from others.
    assert all(e["action"] == "login" for e in log), f"unexpected cross-user entries: {log}"
