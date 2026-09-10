"""Test the notification system: upload docs with near-term / clashing dates,
then verify GET /notifications surfaces reminder + insight notifications."""
from __future__ import annotations

import io
import sys
import uuid
from datetime import datetime, timedelta, timezone

import requests

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"


def _pdf(text: str) -> bytes:
    parts, y = [], 760
    for ln in text.split("\n"):
        esc = ln.replace("(", r"\(").replace(")", r"\)")
        parts.append(f"BT /F1 11 Tf 40 {y} Td ({esc}) Tj ET"); y -= 18
    content = ("\n".join(parts)).encode()
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


def H(t): return {"Authorization": f"Bearer {t}"}


def main() -> int:
    email = f"notif_{uuid.uuid4().hex[:6]}@test.com"
    requests.post(f"{BASE}/auth/register", json={"email": email, "password": "password123"}, timeout=30)
    tok = requests.post(f"{BASE}/auth/login", json={"email": email, "password": "password123"}, timeout=30).json()["access_token"]
    print(f"user: {email}")

    now = datetime.now(timezone.utc)
    d3 = (now + timedelta(days=3)).strftime("%Y-%m-%d")   # within 14d -> notif (high, <=7)
    d5 = (now + timedelta(days=5)).strftime("%Y-%m-%d")   # within 7d of d3 -> clash insight
    d40 = (now + timedelta(days=40)).strftime("%Y-%m-%d")  # outside window -> NOT a notif

    docs = {
        "insurance_soon.pdf": f"Insurance policy for Test User. Policy renewal date: {d3}. Annual premium: $2,400.",
        "loan_soon.pdf": f"Home loan for Test User. Next EMI due date: {d5}. EMI amount: $1,120.",
        "lease_far.pdf": f"Lease agreement for Test User. Lease end date: {d40}. Monthly rent: $1,500.",
    }
    for name, text in docs.items():
        r = requests.post(f"{BASE}/documents/upload", headers=H(tok),
                          files={"file": (name, _pdf(text), "application/pdf")}, timeout=120)
        print(f"  uploaded {name}: {r.status_code} type={r.json().get('doc_type')}")

    rems = requests.get(f"{BASE}/reminders", headers=H(tok), timeout=30).json()
    print(f"reminders created: {len(rems)}")

    notif = requests.get(f"{BASE}/notifications", headers=H(tok), timeout=30).json()
    items = notif.get("items", [])
    print(f"\nGET /notifications -> count={notif.get('count')}")
    for n in items:
        print(f"  [{n['severity']:6}] {n['kind']:8} {n['message'][:70]}")

    # Assertions
    ok = True
    kinds = {n["kind"] for n in items}
    reminder_notifs = [n for n in items if n["kind"] == "reminder"]
    insight_notifs = [n for n in items if n["kind"] == "insight"]
    def check(name, cond):
        nonlocal ok; ok = ok and cond
        print(f"[{'PASS' if cond else 'FAIL'}] {name}")

    check("has >=1 notification", len(items) >= 1)
    check("reminder notification present (near-term due date)", len(reminder_notifs) >= 1)
    check("insight notification present (clashing dates)", len(insight_notifs) >= 1)
    check("far-future date (40d) NOT in notifications",
          not any("lease" in n["message"].lower() and "40" in n["message"] for n in items))
    check("high-severity item sorted first", items and items[0]["severity"] == "high")

    print("\n=== Notification test:", "PASS" if ok else "FAIL", "===")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
