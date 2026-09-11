"""F3.6 — malicious file handling checklist.

- Upload a renamed .exe as .pdf -> confirm rejection.
- Upload an oversized file -> confirm clean rejection (413), not a crash.
- Confirm a real PDF and a real text file still upload (no regression).

Run: cd backend && .venv\\Scripts\\python.exe -m pytest tests/test_filecheck.py -v
"""
from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _login() -> str:
    e = f"fc_{uuid.uuid4().hex[:8]}@test.com"
    client.post("/auth/register", json={"email": e, "password": "password123"})
    return client.post("/auth/login", json={"email": e, "password": "password123"}).json()["access_token"]


def _H(t): return {"Authorization": f"Bearer {t}"}


def test_renamed_exe_as_pdf_rejected():
    tok = _login()
    # A Windows PE executable starts with "MZ".
    exe_bytes = b"MZ\x90\x00\x03\x00\x00\x00" + b"\x00" * 64
    r = client.post("/documents/upload", headers=_H(tok),
                    files={"file": ("malware.pdf", exe_bytes, "application/pdf")})
    assert r.status_code == 400, f"exe-as-pdf not rejected: {r.status_code} {r.text}"
    assert "executable" in r.json()["detail"].lower() or "signature" in r.json()["detail"].lower()


def test_fake_pdf_text_rejected():
    tok = _login()
    # Claims .pdf but has no %PDF- signature.
    r = client.post("/documents/upload", headers=_H(tok),
                    files={"file": ("fake.pdf", b"this is not really a pdf", "application/pdf")})
    assert r.status_code == 400, f"fake pdf not rejected: {r.status_code}"


def test_oversized_file_rejected_cleanly():
    tok = _login()
    big = b"%PDF-1.4\n" + b"A" * (11 * 1024 * 1024)  # 11 MB > 10 MB cap
    r = client.post("/documents/upload", headers=_H(tok),
                    files={"file": ("big.pdf", big, "application/pdf")})
    assert r.status_code == 413, f"oversized not rejected with 413: {r.status_code}"
    assert "too large" in r.json()["detail"].lower()


def _valid_pdf(text: str = "Invoice total 100") -> bytes:
    esc = text.replace("(", r"\(").replace(")", r"\)")
    content = f"BT /F1 11 Tf 40 760 Td ({esc}) Tj ET".encode()
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length %d >>\nstream\n%s\nendstream" % (len(content), content),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    import io as _io
    out = _io.BytesIO(); out.write(b"%PDF-1.4\n"); offs = []
    for i, b in enumerate(objs, 1):
        offs.append(out.tell()); out.write(b"%d 0 obj\n%s\nendobj\n" % (i, b))
    x = out.tell(); out.write(b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1))
    for o in offs: out.write(b"%010d 00000 n \n" % o)
    out.write(b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF" % (len(objs) + 1, x))
    return out.getvalue()


def test_real_pdf_accepted():
    tok = _login()
    r = client.post("/documents/upload", headers=_H(tok),
                    files={"file": ("real.pdf", _valid_pdf(), "application/pdf")})
    assert r.status_code == 201, f"real pdf rejected: {r.status_code} {r.text}"


def test_real_text_accepted():
    tok = _login()
    r = client.post("/documents/upload", headers=_H(tok),
                    files={"file": ("note.txt", b"Lease end date 2027-01-01", "text/plain")})
    assert r.status_code == 201, f"real text rejected: {r.status_code} {r.text}"
