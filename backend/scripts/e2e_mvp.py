"""End-to-end MVP smoke test — drives the running server over HTTP.

Covers: /health, register, login, refresh, upload (PDF -> extract), list, detail,
chat (+ conversations, messages), delete, and a user_id-isolation check (user B
cannot see user A's document). Prints PASS/FAIL per step; exits non-zero on failure.

Run the server first:  uvicorn app.main:app --host 127.0.0.1 --port 8071
Then:                   python scripts/e2e_mvp.py
"""
from __future__ import annotations

import io
import sys
import uuid

import requests

BASE = "http://127.0.0.1:8071"
results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def make_pdf(text: str) -> bytes:
    """Minimal single-page PDF with embedded text (no external deps)."""
    content = f"BT /F1 12 Tf 50 750 Td ({text}) Tj ET"
    objs = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        "/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        f"<< /Length {len(content)} >>\nstream\n{content}\nendstream",
    ]
    pdf = "%PDF-1.4\n"
    offsets = []
    for i, o in enumerate(objs, start=1):
        offsets.append(len(pdf))
        pdf += f"{i} 0 obj\n{o}\nendobj\n"
    xref_pos = len(pdf)
    pdf += f"xref\n0 {len(objs)+1}\n0000000000 65535 f \n"
    for off in offsets:
        pdf += f"{off:010d} 00000 n \n"
    pdf += (
        f"trailer\n<< /Size {len(objs)+1} /Root 1 0 R >>\n"
        f"startxref\n{xref_pos}\n%%EOF"
    )
    return pdf.encode("latin-1")


def main() -> int:
    # /health
    r = requests.get(f"{BASE}/health", timeout=10)
    check("/health reachable + healthy", r.ok and r.json().get("status") == "healthy",
          r.text[:200])

    email_a = f"a_{uuid.uuid4().hex[:8]}@example.com"
    email_b = f"b_{uuid.uuid4().hex[:8]}@example.com"

    # register A
    r = requests.post(f"{BASE}/auth/register",
                      json={"email": email_a, "password": "password123",
                            "full_name": "User A"}, timeout=10)
    check("register user A (201)", r.status_code == 201, f"status={r.status_code}")

    # duplicate register -> 409
    r = requests.post(f"{BASE}/auth/register",
                      json={"email": email_a, "password": "password123"}, timeout=10)
    check("duplicate email rejected (409)", r.status_code == 409, f"status={r.status_code}")

    # login A
    r = requests.post(f"{BASE}/auth/login",
                      json={"email": email_a, "password": "password123"}, timeout=10)
    check("login user A (200 + tokens)",
          r.ok and "access_token" in r.json() and "refresh_token" in r.json(),
          f"status={r.status_code}")
    tok_a = r.json()
    hdr_a = {"Authorization": f"Bearer {tok_a['access_token']}"}

    # refresh
    r = requests.post(f"{BASE}/auth/refresh",
                      json={"refresh_token": tok_a["refresh_token"]}, timeout=10)
    check("refresh token (200 + new access)", r.ok and "access_token" in r.json(),
          f"status={r.status_code}")

    # unauthenticated access blocked
    r = requests.get(f"{BASE}/documents", timeout=10)
    check("unauthenticated /documents blocked (401)", r.status_code == 401,
          f"status={r.status_code}")

    # upload PDF
    pdf = make_pdf("Lease agreement end date 2026-12-31 deposit amount 1500 USD")
    r = requests.post(f"{BASE}/documents/upload", headers=hdr_a,
                      files={"file": ("lease.pdf", io.BytesIO(pdf), "application/pdf")},
                      timeout=60)
    upload_ok = r.status_code == 201
    check("upload PDF (201, status done)",
          upload_ok and r.json().get("upload_status") == "done", f"status={r.status_code} body={r.text[:200]}")
    doc = r.json() if upload_ok else {}
    doc_id = doc.get("id")
    check("OCR text extracted from PDF (non-empty)",
          bool(doc.get("ocr_text")), f"ocr_len={len(doc.get('ocr_text') or '')}")

    # list
    r = requests.get(f"{BASE}/documents", headers=hdr_a, timeout=10)
    check("list documents (contains uploaded)",
          r.ok and any(d["id"] == doc_id for d in r.json()), f"status={r.status_code}")

    # detail
    r = requests.get(f"{BASE}/documents/{doc_id}", headers=hdr_a, timeout=10)
    check("document detail (200)", r.ok, f"status={r.status_code}")

    # reject unsupported type
    r = requests.post(f"{BASE}/documents/upload", headers=hdr_a,
                      files={"file": ("x.exe", io.BytesIO(b"MZ"), "application/octet-stream")},
                      timeout=10)
    check("reject unsupported file type (400)", r.status_code == 400,
          f"status={r.status_code}")

    # chat
    r = requests.post(f"{BASE}/chat", headers=hdr_a,
                      json={"message": "When does my lease end?"}, timeout=120)
    chat_ok = r.ok and "conversation_id" in r.json()
    check("chat returns assistant reply (200)", chat_ok, f"status={r.status_code} body={r.text[:200]}")
    conv_id = r.json().get("conversation_id") if chat_ok else None

    # conversations list
    r = requests.get(f"{BASE}/chat/conversations", headers=hdr_a, timeout=10)
    check("list conversations (contains new)",
          r.ok and any(c["id"] == conv_id for c in r.json()), f"status={r.status_code}")

    # messages
    r = requests.get(f"{BASE}/chat/conversations/{conv_id}/messages", headers=hdr_a,
                     timeout=10)
    check("conversation messages (user + assistant)",
          r.ok and len(r.json()) >= 2, f"count={len(r.json()) if r.ok else 'err'}")

    # user_id isolation: user B cannot see A's document
    requests.post(f"{BASE}/auth/register",
                  json={"email": email_b, "password": "password123"}, timeout=10)
    rb = requests.post(f"{BASE}/auth/login",
                       json={"email": email_b, "password": "password123"}, timeout=10)
    hdr_b = {"Authorization": f"Bearer {rb.json()['access_token']}"}
    r = requests.get(f"{BASE}/documents/{doc_id}", headers=hdr_b, timeout=10)
    check("user B cannot read user A's document (404)", r.status_code == 404,
          f"status={r.status_code}")
    r = requests.get(f"{BASE}/documents", headers=hdr_b, timeout=10)
    check("user B document list excludes A's docs",
          r.ok and all(d["id"] != doc_id for d in r.json()), f"status={r.status_code}")

    # delete (as A)
    r = requests.delete(f"{BASE}/documents/{doc_id}", headers=hdr_a, timeout=10)
    check("delete document (204)", r.status_code == 204, f"status={r.status_code}")
    r = requests.get(f"{BASE}/documents/{doc_id}", headers=hdr_a, timeout=10)
    check("deleted document gone (404)", r.status_code == 404, f"status={r.status_code}")

    # health still healthy after everything
    r = requests.get(f"{BASE}/health", timeout=10)
    check("/health still healthy at end", r.ok and r.json().get("status") == "healthy",
          r.text[:120])

    passed = sum(1 for _, ok, _ in results if ok)
    print(f"\n{passed}/{len(results)} checks passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
