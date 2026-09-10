"""Showcase notifications for the demo account: upload docs with near-term dates,
then print GET /notifications to prove the bell will show them."""
from __future__ import annotations

import io
import sys
from datetime import datetime, timedelta, timezone

import requests

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
EMAIL, PASSWORD = "ac@gmail.com", "12345678"


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
    tok = requests.post(f"{BASE}/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=30).json().get("access_token")
    if not tok:
        print("LOGIN FAILED"); return 1
    print(f"Logged in as {EMAIL}")

    now = datetime.now(timezone.utc)
    d2 = (now + timedelta(days=2)).strftime("%Y-%m-%d")
    d6 = (now + timedelta(days=6)).strftime("%Y-%m-%d")
    docs = {
        "car_insurance_renewal.pdf": f"Car insurance policy for Arjun Chandra. Policy renewal date: {d2}. Annual premium: $980.",
        "electricity_bill.pdf": f"Electricity bill. Account holder: Arjun Chandra. Payment due date: {d6}. Amount due: $145.",
    }
    for name, text in docs.items():
        r = requests.post(f"{BASE}/documents/upload", headers=H(tok),
                          files={"file": (name, _pdf(text), "application/pdf")}, timeout=120)
        d = r.json()
        print(f"  uploaded {name}: {r.status_code} type={d.get('doc_type')} fields={len(d.get('extracted_fields') or [])}")

    notif = requests.get(f"{BASE}/notifications", headers=H(tok), timeout=30).json()
    print(f"\nGET /notifications -> count={notif.get('count')}")
    for n in notif.get("items", []):
        print(f"  [{n['severity']:6}] {n['kind']:8} -> {n['message'][:75]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
