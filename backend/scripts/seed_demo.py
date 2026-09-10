"""Seed the evaluator demo account with realistic sample documents.

Registers (or logs into) ac@gmail.com / 12345678, uploads 5 documents that
exercise every Phase 2 feature (classification variety, dates that clash for
insights, amounts/parties for extraction), then prints the resulting state.

Idempotent-ish: if a document with the same filename already exists for the
user, it is skipped so re-running doesn't pile up duplicates.
"""
from __future__ import annotations

import io
import sys

import requests

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
EMAIL = "ac@gmail.com"
PASSWORD = "12345678"


def _pdf(text: str) -> bytes:
    lines = text.split("\n")
    parts = []
    y = 760
    for ln in lines:
        esc = ln.replace("(", r"\(").replace(")", r"\)")
        parts.append(f"BT /F1 11 Tf 40 {y} Td ({esc}) Tj ET")
        y -= 18
    content = ("\n".join(parts)).encode()
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


DOCS = {
    "residential_lease.pdf": (
        "RESIDENTIAL LEASE AGREEMENT\n"
        "Landlord: Greenfield Properties LLC\n"
        "Tenant: Arjun Chandra\n"
        "Property: 42 Maple Street, Unit 5B\n"
        "Lease start date: 2026-02-01\n"
        "Lease end date: 2027-01-31\n"
        "Monthly rent: $1,850\n"
        "Security deposit: $3,700\n"
        "Notice period: 60 days before end date\n"
    ),
    "health_insurance_policy.pdf": (
        "HEALTH INSURANCE POLICY\n"
        "Insurer: SafeGuard Health Insurance\n"
        "Policy Holder: Arjun Chandra\n"
        "Policy Number: SG-2026-88421\n"
        "Policy renewal date: 2027-01-28\n"
        "Annual premium: $2,400\n"
        "Coverage limit: $500,000\n"
        "Co-pay: $30 per visit\n"
    ),
    "home_loan_emi.pdf": (
        "HOME LOAN EMI SCHEDULE\n"
        "Lender: FirstNational Bank\n"
        "Borrower: Arjun Chandra\n"
        "Loan account: HL-556231\n"
        "Next EMI due date: 2027-06-15\n"
        "EMI amount: $1,120\n"
        "Outstanding principal: $184,000\n"
        "Interest rate: 7.2 percent\n"
    ),
    "streaming_subscription.pdf": (
        "SUBSCRIPTION CONFIRMATION\n"
        "Service: StreamMax Premium\n"
        "Account holder: Arjun Chandra\n"
        "Plan: Premium 4K, up to 4 screens\n"
        "Renewal date: 2027-03-05\n"
        "Monthly fee: $18\n"
        "Payment method: Visa ending 4021\n"
    ),
    "medical_report.pdf": (
        "MEDICAL REPORT SUMMARY\n"
        "Clinic: Riverside Family Clinic\n"
        "Patient: Arjun Chandra\n"
        "Consulting physician: Dr. Neha Rao\n"
        "Visit date: 2026-09-01\n"
        "Follow-up appointment: 2027-01-25\n"
        "Prescription refill due: 2026-12-01\n"
        "Notes: Routine checkup, all vitals normal.\n"
    ),
}


def H(t): return {"Authorization": f"Bearer {t}"}


def main() -> int:
    # Register (ignore 409 if already exists), then log in.
    requests.post(f"{BASE}/auth/register",
                  json={"email": EMAIL, "password": PASSWORD, "full_name": "Arjun Chandra"},
                  timeout=30)
    r = requests.post(f"{BASE}/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=30)
    if r.status_code != 200:
        print(f"LOGIN FAILED: {r.status_code} {r.text[:200]}")
        return 1
    tok = r.json()["access_token"]
    print(f"Logged in as {EMAIL}")

    existing = {d["filename"] for d in requests.get(f"{BASE}/documents", headers=H(tok), timeout=30).json()}

    for name, text in DOCS.items():
        if name in existing:
            print(f"  skip (exists): {name}")
            continue
        resp = requests.post(f"{BASE}/documents/upload", headers=H(tok),
                             files={"file": (name, _pdf(text), "application/pdf")}, timeout=120)
        if resp.status_code == 201:
            d = resp.json()
            nf = len(d.get("extracted_fields") or [])
            print(f"  uploaded: {name}  -> type={d.get('doc_type')}  fields={nf}")
        else:
            print(f"  FAILED {name}: {resp.status_code} {resp.text[:160]}")

    # Report resulting state
    docs = requests.get(f"{BASE}/documents", headers=H(tok), timeout=30).json()
    rems = requests.get(f"{BASE}/reminders", headers=H(tok), timeout=30).json()
    ins = requests.get(f"{BASE}/insights?refresh=true", headers=H(tok), timeout=30).json()
    print(f"\nAccount now has: {len(docs)} documents, {len(rems)} reminders, {len(ins)} insights")
    print("Insight types:", [i["type"] for i in ins])
    print("Doc types:", sorted({d["doc_type"] for d in docs}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
