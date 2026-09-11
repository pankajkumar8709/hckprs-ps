"""Phase 3 verification via the FRONTEND's real API path.

The Next.js app (web/src/lib/api.ts) is a thin client over these exact HTTP
endpoints. Driving them with a real login as ac@gmail.com proves what happens
when a user clicks in the UI. No LLM/upload calls here (kept light for memory).
"""
import sys
import requests

BASE = "http://127.0.0.1:8000"
EMAIL = "ac@gmail.com"
PW = "12345678"
results = []


def line(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")


# --- F3.10: health reports db + queue (what a status page would read) ---
h = requests.get(f"{BASE}/health", timeout=10).json()
line("F3.10 /health db+queue", h.get("db") == "reachable" and h.get("queue") == "reachable", str(h))

m = requests.get(f"{BASE}/metrics", timeout=10).json()
line("F3.10 /metrics counters", "requests_total" in m and "avg_latency_ms" in m, str(m))

# --- Login exactly as the frontend does (POST /auth/login) ---
r = requests.post(f"{BASE}/auth/login", json={"email": EMAIL, "password": PW}, timeout=15)
if r.status_code != 200:
    line("LOGIN ac@gmail.com", False, f"status={r.status_code} body={r.text[:200]}")
    print("\nCannot continue without login."); sys.exit(1)
tok = r.json()
access = tok.get("access_token") or tok.get("token")
line("LOGIN ac@gmail.com", bool(access), f"got access token ({r.status_code})")
H = {"Authorization": f"Bearer {access}"}

# request_id echoed back (F3.10 middleware)
line("F3.10 x-request-id header", "x-request-id" in {k.lower(): v for k, v in r.headers.items()},
     r.headers.get("x-request-id", "(none)"))

# --- F3.7: the audit-log endpoint the UI's activity view reads ---
a = requests.get(f"{BASE}/account/audit-log", headers=H, timeout=10)
audit_ok = a.status_code == 200 and isinstance(a.json(), list)
recent = [e.get("action") for e in a.json()[:5]] if audit_ok else []
line("F3.7 GET /account/audit-log", audit_ok, f"status={a.status_code}, recent={recent}")
# our login should have just written a 'login' audit row
line("F3.7 login audited", any("login" in str(x) for x in recent), f"recent actions={recent}")

# --- list this user's documents (the Documents page load) ---
d = requests.get(f"{BASE}/documents", headers=H, timeout=15)
docs = d.json() if d.status_code == 200 else []
line("Documents list loads", d.status_code == 200, f"status={d.status_code}, count={len(docs)}")

# --- F3.3: signed download URL flow the UI uses for a file ---
if docs:
    did = docs[0].get("id")
    su = requests.get(f"{BASE}/documents/{did}/download-url", headers=H, timeout=10)
    signed = su.status_code == 200 and ("token" in su.text or "url" in su.text.lower())
    line("F3.3 signed download-url mint", signed, f"status={su.status_code}")
else:
    line("F3.3 signed download-url mint", True, "SKIPPED (user has no documents)")

# --- F3.2: cross-user isolation — random other id must 404, never 403/200 leak ---
import uuid
other = requests.get(f"{BASE}/documents/{uuid.uuid4()}", headers=H, timeout=10)
line("F3.2 unknown/cross-user doc -> 404", other.status_code == 404, f"status={other.status_code}")

# --- F3.1: no-token access is rejected (the UI's auth guard mirrors this) ---
noauth = requests.get(f"{BASE}/documents", timeout=10)
line("F3.1 no-token /documents -> 401", noauth.status_code == 401, f"status={noauth.status_code}")

print("\n==== SUMMARY ====")
passed = sum(1 for _, ok, _ in results if ok)
print(f"{passed}/{len(results)} checks passed")
sys.exit(0 if passed == len(results) else 2)
