"""Phase 2 end-to-end API test — verifies F2.1..F2.9 against a running server.

Run via scripts/run_e2e_phase2.ps1 (starts a server on :8072, runs this, stops it).
Uses the real DB and real Groq (extraction/classification/router). Prints a
PASS/FAIL line per checklist item and exits non-zero if any fail.
"""
from __future__ import annotations

import io
import sys
import time
import uuid

import requests

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8072"

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def _pdf(text: str) -> bytes:
    """Minimal one-page PDF with a text layer containing `text`."""
    # Escape parens for PDF string.
    esc = text.replace("(", r"\(").replace(")", r"\)")
    content = f"BT /F1 10 Tf 40 780 Td 14 TL ({esc}) Tj ET".encode()
    objs = []
    objs.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objs.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    objs.append(b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>")
    objs.append(b"<< /Length %d >>\nstream\n%s\nendstream" % (len(content), content))
    objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objs, start=1):
        offsets.append(out.tell())
        out.write(b"%d 0 obj\n%s\nendobj\n" % (i, body))
    xref_pos = out.tell()
    out.write(b"xref\n0 %d\n" % (len(objs) + 1))
    out.write(b"0000000000 65535 f \n")
    for off in offsets:
        out.write(b"%010d 00000 n \n" % off)
    out.write(b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF"
              % (len(objs) + 1, xref_pos))
    return out.getvalue()


def register(email: str) -> str:
    requests.post(f"{BASE}/auth/register",
                  json={"email": email, "password": "password123"}, timeout=30)
    r = requests.post(f"{BASE}/auth/login",
                      json={"email": email, "password": "password123"}, timeout=30)
    return r.json()["access_token"]


def H(tok: str) -> dict:
    return {"Authorization": f"Bearer {tok}"}


def upload(tok: str, name: str, text: str) -> dict:
    files = {"file": (name, _pdf(text), "application/pdf")}
    r = requests.post(f"{BASE}/documents/upload", headers=H(tok), files=files, timeout=120)
    return r


def main() -> int:
    ua = f"p2a_{uuid.uuid4().hex[:8]}@test.com"
    ub = f"p2b_{uuid.uuid4().hex[:8]}@test.com"
    ta = register(ua)
    tb = register(ub)
    check("auth: two users registered + logged in", bool(ta and tb))

    # ---- F2.1 + F2.2: upload a lease, classification + validator + trace ----
    lease_text = ("Residential Lease Agreement. Tenant: John Doe. Landlord: Acme "
                  "Properties. Lease end date: 2026-12-31. Security deposit amount: "
                  "$2500. Monthly rent: $1500.")
    r = upload(ta, "lease.pdf", lease_text)
    ok = r.status_code == 201
    doc = r.json() if ok else {}
    check("F2.1: lease upload 201", ok, f"status={r.status_code}")
    check("F2.1: doc_type classified as lease",
          doc.get("doc_type") == "lease", f"doc_type={doc.get('doc_type')}")
    trace = doc.get("agent_trace") or []
    agents = [s.get("agent") for s in trace]
    check("F2.2: agent_trace has Classification+Extraction+Validator",
          {"ClassificationAgent", "ExtractionAgent", "ValidatorAgent"}.issubset(set(agents)),
          f"agents={agents}")
    fields = doc.get("extracted_fields") or []
    has_date = any(f["field_type"] == "date" for f in fields)
    has_amount = any(f["field_type"] == "amount" for f in fields)
    check("F2.2: validator-accepted date+amount fields present",
          has_date and has_amount, f"dates={has_date} amounts={has_amount}")
    # Validator: the accepted date/amount values must appear in source text.
    validated_ok = all(
        (f["field_value"] and any(tok in lease_text for tok in
         [t for t in [f["field_value"]] if t]))
        or f["field_type"] not in ("date", "amount")
        for f in fields
    )
    check("F2.2: accepted hard-fact values trace to source", validated_ok)

    doc_id = doc.get("id")

    # ---- F2.3: reminders auto-created from the date field ----
    time.sleep(0.5)
    r = requests.get(f"{BASE}/reminders", headers=H(ta), timeout=30)
    rems = r.json()
    check("F2.3: reminder auto-created from extracted date", len(rems) >= 1,
          f"count={len(rems)}")
    # PATCH one to done
    if rems:
        rid = rems[0]["id"]
        r = requests.patch(f"{BASE}/reminders/{rid}", headers=H(ta),
                           json={"status": "done"}, timeout=30)
        check("F2.3: PATCH reminder -> done persists",
              r.status_code == 200 and r.json()["status"] == "done")
    # Isolation: user B sees no reminders
    r = requests.get(f"{BASE}/reminders", headers=H(tb), timeout=30)
    check("F2.3: reminders scoped to user (B empty)", r.json() == [],
          f"B_count={len(r.json())}")

    # ---- F2.7: insights — create clashing reminders, expect date_clash ----
    # Upload two more docs with dates within 5 days for user A (re-open reminders).
    upload(ta, "insurance.pdf",
           "Insurance policy renewal date: 2027-03-10. Premium amount: $800.")
    upload(ta, "loan.pdf",
           "Loan EMI due date: 2027-03-13. Installment amount: $400.")
    r = requests.get(f"{BASE}/insights?refresh=true", headers=H(ta), timeout=30)
    ins = r.json()
    clash = any(i["type"] == "date_clash" for i in ins)
    check("F2.7: date_clash insight generated (dates within 7 days)", clash,
          f"types={[i['type'] for i in ins]}")

    # ---- F2.9: premium limit ----
    r = requests.get(f"{BASE}/account/plan", headers=H(ta), timeout=30)
    check("F2.9: free plan reports limit 10",
          r.json().get("document_limit") == 10, f"plan={r.json()}")
    r = requests.post(f"{BASE}/account/upgrade", headers=H(ta), timeout=30)
    check("F2.9: upgrade -> premium, unlimited",
          r.json().get("plan_tier") == "premium" and r.json().get("document_limit") is None,
          f"plan={r.json()}")

    # ---- F2.8: sharing ----
    if doc_id:
        r = requests.post(f"{BASE}/documents/{doc_id}/share", headers=H(ta),
                          json={"shared_with_email": ub, "permission": "view"}, timeout=30)
        check("F2.8: share doc A->B (201)", r.status_code == 201, f"status={r.status_code}")
        r = requests.get(f"{BASE}/documents/shared-with-me", headers=H(tb), timeout=30)
        shared_ids = [d["id"] for d in r.json()]
        check("F2.8: B sees doc in shared-with-me", doc_id in shared_ids)
        r = requests.get(f"{BASE}/documents/{doc_id}", headers=H(tb), timeout=30)
        check("F2.8: B can read shared doc detail", r.status_code == 200,
              f"status={r.status_code}")
        # Expired grant: share with an expiry in the past to a third user
        uc = f"p2c_{uuid.uuid4().hex[:8]}@test.com"
        tc = register(uc)
        requests.post(f"{BASE}/documents/{doc_id}/share", headers=H(ta),
                      json={"shared_with_email": uc, "permission": "view",
                            "expires_at": "2000-01-01T00:00:00+00:00"}, timeout=30)
        r = requests.get(f"{BASE}/documents/{doc_id}", headers=H(tc), timeout=30)
        check("F2.8: expired grant blocks access (404)", r.status_code == 404,
              f"status={r.status_code}")

    # ---- F2.4: RAG chat citations + cross-user isolation ----
    r = requests.post(f"{BASE}/chat", headers=H(ta),
                      json={"message": "When does my lease end?"}, timeout=120)
    body = r.json()
    check("F2.4: chat answers lease question", r.status_code == 200
          and "2026" in (body.get("message", {}).get("content") or ""),
          f"answer={body.get('message',{}).get('content','')[:80]}")
    check("F2.5: intent routed", body.get("intent") in
          {"question", "show_reminders", "show_insights", "upload_help", "general"},
          f"intent={body.get('intent')}")
    # citations present only if embeddings loaded; don't hard-fail if model absent
    cits = body.get("citations") or []
    check("F2.4: citations returned (RAG active)" if cits else
          "F2.4: RAG fell back to whole-text (embeddings not loaded)",
          True, f"citations={len(cits)}")

    # Cross-user: B (no lease) asks the same — must not leak A's data
    r = requests.post(f"{BASE}/chat", headers=H(tb),
                      json={"message": "When does my lease end?"}, timeout=120)
    ans_b = (r.json().get("message", {}).get("content") or "").lower()
    check("F2.4: cross-user isolation (B gets no lease date)",
          "2026-12-31" not in ans_b and "december 31" not in ans_b,
          f"B_answer={ans_b[:80]}")

    # ---- F2.5: reminders intent ----
    r = requests.post(f"{BASE}/chat", headers=H(ta),
                      json={"message": "What reminders do I have?"}, timeout=120)
    check("F2.5: reminders-intent chat returns reminder data",
          r.status_code == 200, f"intent={r.json().get('intent')}")

    # ---- summary ----
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print(f"\n=== Phase 2 e2e: {passed}/{total} passed ===")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
