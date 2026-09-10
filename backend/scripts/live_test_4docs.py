"""Live-app test with 4 realistic documents against the running backend (:8000).
Exercises the same endpoints the frontend calls. Prints a per-feature report.
"""
from __future__ import annotations

import io
import sys
import uuid

import requests

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"


def _pdf(text: str) -> bytes:
    esc = text.replace("(", r"\(").replace(")", r"\)").replace("\n", ") Tj T* (")
    content = f"BT /F1 10 Tf 40 760 Td 13 TL ({esc}) Tj ET".encode()
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
    "lease.pdf": (
        "Residential Lease Agreement between landlord Acme Realty and tenant "
        "Priya Sharma. Lease start date 2026-01-01. Lease end date 2027-04-05. "
        "Monthly rent amount $1800. Security deposit $3600. Notice period 30 days."
    ),
    "insurance.pdf": (
        "Health Insurance Policy issued by SafeGuard Insurance to member Priya "
        "Sharma. Policy renewal date 2027-04-02. Annual premium amount $1200. "
        "Coverage limit $500000."
    ),
    "loan.pdf": (
        "Home Loan EMI schedule from FirstBank for borrower Priya Sharma. "
        "Next EMI due date 2027-09-15. EMI amount $950. Outstanding principal "
        "$120000."
    ),
    "subscription.pdf": (
        "Streaming subscription confirmation from StreamMax for Priya Sharma. "
        "Renewal date 2027-11-20. Monthly fee $15. Plan: Premium 4K."
    ),
}

results: list[tuple[str, bool, str]] = []
def check(n, ok, d=""):
    results.append((n, ok, d)); print(f"[{'PASS' if ok else 'FAIL'}] {n}" + (f" — {d}" if d else ""))


def H(t): return {"Authorization": f"Bearer {t}"}


def _norm(s: str) -> str:
    """Normalize model typography so ASCII assertions match: non-breaking and
    figure hyphens -> '-', curly quotes -> straight, collapse whitespace."""
    if not s:
        return ""
    trans = {
        "\u2011": "-", "\u2012": "-", "\u2013": "-", "\u2014": "-", "\u2212": "-",
        "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
        "\u00a0": " ",
    }
    return "".join(trans.get(ch, ch) for ch in s).lower()


def main() -> int:
    ua = f"live_a_{uuid.uuid4().hex[:6]}@test.com"
    ub = f"live_b_{uuid.uuid4().hex[:6]}@test.com"
    for e in (ua, ub):
        requests.post(f"{BASE}/auth/register", json={"email": e, "password": "password123"}, timeout=30)
    ta = requests.post(f"{BASE}/auth/login", json={"email": ua, "password": "password123"}, timeout=30).json()["access_token"]
    tb = requests.post(f"{BASE}/auth/login", json={"email": ub, "password": "password123"}, timeout=30).json()["access_token"]
    check("auth: 2 accounts", bool(ta and tb))

    # ---- Upload 4 real docs (F2.1 classification + F2.2 pipeline) ----
    uploaded = {}
    for name, text in DOCS.items():
        r = requests.post(f"{BASE}/documents/upload", headers=H(ta),
                          files={"file": (name, _pdf(text), "application/pdf")}, timeout=120)
        d = r.json()
        uploaded[name] = d
        agents = [s.get("agent") for s in (d.get("agent_trace") or [])]
        trace_ok = {"ClassificationAgent", "ExtractionAgent", "ValidatorAgent"}.issubset(set(agents))
        check(f"F2.1/F2.2 upload {name}: 201 + doc_type={d.get('doc_type')} + trace",
              r.status_code == 201 and trace_ok, f"type={d.get('doc_type')} agents={agents}")

    # Field extraction sanity (F2.2 validated fields)
    for name, d in uploaded.items():
        fields = d.get("extracted_fields") or []
        types = {f["field_type"] for f in fields}
        check(f"F2.2 {name}: has date+amount fields",
              "date" in types and "amount" in types, f"types={sorted(types)}")

    # ---- F2.3 reminders auto-created ----
    rems = requests.get(f"{BASE}/reminders", headers=H(ta), timeout=30).json()
    check("F2.3: reminders auto-created from dates", len(rems) >= 3, f"count={len(rems)}")
    if rems:
        r = requests.patch(f"{BASE}/reminders/{rems[0]['id']}", headers=H(ta),
                          json={"status": "done"}, timeout=30)
        check("F2.3: mark reminder done persists", r.json().get("status") == "done")

    # ---- F2.7 insights: lease(2027-04-05) & insurance(2027-04-02) are 3 days apart ----
    ins = requests.get(f"{BASE}/insights?refresh=true", headers=H(ta), timeout=30).json()
    types = [i["type"] for i in ins]
    check("F2.7: date_clash insight (lease vs insurance ~3 days)",
          "date_clash" in types, f"types={types}")

    # ---- F2.9 premium ----
    plan = requests.get(f"{BASE}/account/plan", headers=H(ta), timeout=30).json()
    check("F2.9: free plan limit 10", plan.get("document_limit") == 10, f"{plan}")
    up = requests.post(f"{BASE}/account/upgrade", headers=H(ta), timeout=30).json()
    check("F2.9: upgrade -> unlimited", up.get("document_limit") is None, f"{up}")

    # ---- F2.8 sharing ----
    lease_id = uploaded["lease.pdf"]["id"]
    r = requests.post(f"{BASE}/documents/{lease_id}/share", headers=H(ta),
                      json={"shared_with_email": ub, "permission": "view"}, timeout=30)
    check("F2.8: share lease A->B", r.status_code == 201, f"status={r.status_code}")
    shared = requests.get(f"{BASE}/documents/shared-with-me", headers=H(tb), timeout=30).json()
    check("F2.8: B sees shared lease", lease_id in [d["id"] for d in shared])

    # ---- F2.4 + F2.5 chat: grounded answers with citations, per document ----
    qa = [
        ("When does my lease end?", ["2027-04-05", "april 5", "2027"]),
        ("What is my insurance premium?", ["1200", "1,200"]),
        ("When is my next loan EMI due?", ["2027-09-15", "september 15"]),
    ]
    for q, expect in qa:
        r = requests.post(f"{BASE}/chat", headers=H(ta), json={"message": q}, timeout=120)
        b = r.json()
        ans = _norm(b.get("message", {}).get("content") or "")
        cits = b.get("citations") or []
        hit = any(_norm(e) in ans for e in expect)
        check(f"F2.4 chat '{q}' grounded + {len(cits)} citation(s)", hit,
              f"answer={ans[:70]}")

    # Refusal
    r = requests.post(f"{BASE}/chat", headers=H(ta),
                      json={"message": "What is my car's license plate number?"}, timeout=120)
    ans = _norm(r.json().get("message", {}).get("content") or "")
    check("F2.4 refuses when info absent",
          any(k in ans for k in ["don't have", "do not have", "not in", "no information", "couldn't find", "couldn't"]),
          f"answer={ans[:70]}")

    # Cross-user isolation
    r = requests.post(f"{BASE}/chat", headers=H(tb),
                      json={"message": "What is my insurance premium?"}, timeout=120)
    ans_b = _norm(r.json().get("message", {}).get("content") or "")
    check("F2.4 cross-user isolation (B has no docs)",
          "1200" not in ans_b and "1,200" not in ans_b, f"B={ans_b[:70]}")

    passed = sum(1 for _, ok, _ in results if ok)
    print(f"\n=== Live app test: {passed}/{len(results)} passed ===")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
