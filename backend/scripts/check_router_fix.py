"""Focused test for the F2.5 router fix: 'deadline'/'timeline' questions must be
answered from the document, not dead-end at 'You have no pending reminders.'"""
from __future__ import annotations

import io
import sys
import uuid

import requests

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8073"


def _pdf(text: str) -> bytes:
    esc = text.replace("(", r"\(").replace(")", r"\)")
    content = f"BT /F1 10 Tf 40 780 Td 14 TL ({esc}) Tj ET".encode()
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length %d >>\nstream\n%s\nendstream" % (len(content), content),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = io.BytesIO(); out.write(b"%PDF-1.4\n"); offs = []
    for i, b in enumerate(objs, 1):
        offs.append(out.tell()); out.write(b"%d 0 obj\n%s\nendobj\n" % (i, b))
    x = out.tell(); out.write(b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1))
    for o in offs:
        out.write(b"%010d 00000 n \n" % o)
    out.write(b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF" % (len(objs) + 1, x))
    return out.getvalue()


def main() -> int:
    email = f"router_{uuid.uuid4().hex[:8]}@test.com"
    requests.post(f"{BASE}/auth/register", json={"email": email, "password": "password123"}, timeout=30)
    tok = requests.post(f"{BASE}/auth/login", json={"email": email, "password": "password123"}, timeout=30).json()["access_token"]
    H = {"Authorization": f"Bearer {tok}"}

    doc_text = ("Axis Bank LLM Bankathon 1.0 Rules and Regulations. The final "
                "submission deadline is 2026-09-20. Round 1 timeline: prototype "
                "due 2026-09-15. Prize amount: Rs 500000.")
    files = {"file": ("bankathon.pdf", _pdf(doc_text), "application/pdf")}
    r = requests.post(f"{BASE}/documents/upload", headers=H, files=files, timeout=120)
    print(f"upload={r.status_code} doc_type={r.json().get('doc_type')}")

    ok = True
    for q in ["when is the deadline", "hackathon timeline",
              "give Axis Bank LLM BANKATHON 1.0 timeline"]:
        r = requests.post(f"{BASE}/chat", headers=H, json={"message": q}, timeout=120)
        body = r.json()
        ans = (body.get("message", {}).get("content") or "")
        intent = body.get("intent")
        no_reminder_deadend = "no pending reminders" not in ans.lower()
        has_answer = any(x in ans for x in ["2026-09-20", "September 20", "09-20",
                                            "2026-09-15", "September 15", "deadline",
                                            "timeline", "submission"])
        passed = no_reminder_deadend and has_answer
        ok = ok and passed
        print(f"[{'PASS' if passed else 'FAIL'}] q='{q}' intent={intent} :: {ans[:110]}")

    print("=== router fix:", "PASS" if ok else "FAIL", "===")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
