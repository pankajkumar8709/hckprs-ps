"""Full live E2E across Phase 1 / 2 / 3 via the frontend's API path (web/src/lib/api.ts).
Login ac@gmail.com, ONE upload, exercise every phase, clean up. Memory-conscious.
"""
import io, sys, time, uuid, requests

BASE = "http://127.0.0.1:8000"
P = lambda n, ok, d="": print(f"[{'PASS' if ok else 'FAIL'}] {n}: {d}")

def _pdf(text):
    esc = text.replace("(", r"\(").replace(")", r"\)")
    content = f"BT /F1 11 Tf 40 760 Td ({esc}) Tj ET".encode()
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
            b"<< /Length %d >>\nstream\n%s\nendstream" % (len(content), content),
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    out = io.BytesIO(); out.write(b"%PDF-1.4\n"); offs = []
    for i, b in enumerate(objs, 1):
        offs.append(out.tell()); out.write(b"%d 0 obj\n%s\nendobj\n" % (i, b))
    x = out.tell(); out.write(b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1))
    for o in offs: out.write(b"%010d 00000 n \n" % o)
    out.write(b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF" % (len(objs) + 1, x))
    return out.getvalue()

print("===== PHASE 3: infra (no auth) =====")
h = requests.get(f"{BASE}/health", timeout=10).json()
P("F3.10 /health db+queue", h.get("db")=="reachable" and h.get("queue")=="reachable", str(h))
m = requests.get(f"{BASE}/metrics", timeout=10).json()
P("F3.10 /metrics", "requests_total" in m, str(m))

print("\n===== PHASE 1: auth =====")
noauth = requests.get(f"{BASE}/documents", timeout=10)
P("F1 no-token /documents -> 401", noauth.status_code==401, f"status={noauth.status_code}")
r = requests.post(f"{BASE}/auth/login", json={"email":"ac@gmail.com","password":"12345678"}, timeout=15)
P("F1 login ac@gmail.com", r.status_code==200, f"status={r.status_code}")
if r.status_code != 200: sys.exit(1)
access = r.json().get("access_token") or r.json().get("token")
H = {"Authorization": f"Bearer {access}"}
bad = requests.post(f"{BASE}/auth/login", json={"email":"ac@gmail.com","password":"wrongpw"}, timeout=15)
P("F1 wrong password rejected", bad.status_code in (400,401), f"status={bad.status_code}")

print("\n===== PHASE 1: upload + extraction =====")
docs0 = requests.get(f"{BASE}/documents", headers=H, timeout=15).json()
P("F1 documents list", isinstance(docs0, list), f"count={len(docs0)}")
up = requests.post(f"{BASE}/documents/upload", headers=H,
    files={"file": ("e2e_lease.pdf", io.BytesIO(_pdf(
        "Residential Lease Agreement. Tenant John Doe. Monthly rent is 3100 dollars. "
        "Security deposit 6200 dollars. The lease renewal date is August 1 2026.")), "application/pdf")}, timeout=90)
P("F1 upload valid PDF", up.status_code==201, f"status={up.status_code} {up.text[:120] if up.status_code!=201 else ''}")
if up.status_code != 201: sys.exit(2)
did = up.json()["id"]
det = requests.get(f"{BASE}/documents/{did}", headers=H, timeout=20).json()
fields = det.get("fields") or det.get("extracted_fields") or []
P("F2.1 extraction fields", len(fields)>0, f"{len(fields)} fields, doc_type={det.get('doc_type')}")
P("F2.2 agent trace", bool(det.get("agent_trace") or det.get("agent_trace_json")), "present")

print("\n===== PHASE 3: security on the uploaded doc =====")
exe = b"MZ\x90\x00" + b"\x00"*200
sp = requests.post(f"{BASE}/documents/upload", headers=H,
    files={"file": ("bad.pdf", io.BytesIO(exe), "application/pdf")}, timeout=20)
P("F3.6 spoofed exe rejected", sp.status_code==400, f"status={sp.status_code}")
su = requests.get(f"{BASE}/documents/{did}/download-url", headers=H, timeout=10)
P("F3.3 signed download-url", su.status_code==200, f"status={su.status_code}")
cross = requests.get(f"{BASE}/documents/{uuid.uuid4()}", headers=H, timeout=10)
P("F3.2 cross-user doc -> 404", cross.status_code==404, f"status={cross.status_code}")
al = requests.get(f"{BASE}/account/audit-log", headers=H, timeout=10)
acts = [e.get("action") for e in al.json()[:8]] if al.status_code==200 else []
P("F3.7 audit-log + upload logged", al.status_code==200 and any("upload" in str(a) for a in acts), f"recent={acts}")

print("\n===== PHASE 2: RAG chat + citations =====")
c = requests.post(f"{BASE}/chat", headers=H, json={"message":"What is the renewal date, monthly rent and security deposit in the e2e_lease?"}, timeout=90)
P("F2.4 chat 200", c.status_code==200, f"status={c.status_code}")
if c.status_code==200:
    cj = c.json(); txt = (cj.get("message") or {}).get("content","").lower()
    print(f"   ANSWER: {txt[:220]}")
    P("F2.4 grounded answer", ("3100" in txt or "3,100" in txt) and ("august" in txt or "2026" in txt), "rent+date present")
    P("F2.5 intent routed", bool(cj.get("intent")), f"intent={cj.get('intent')}")
    P("F2.4 citations", len(cj.get("citations",[]))>0, f"{len(cj.get('citations',[]))} cites")

print("\n===== PHASE 2: reminders / insights / plan =====")
rem = requests.get(f"{BASE}/reminders", headers=H, timeout=15)
P("F2.3 reminders list", rem.status_code==200, f"count={len(rem.json()) if rem.status_code==200 else '?'}")
ins = requests.get(f"{BASE}/insights", headers=H, timeout=30)
P("F2.7 insights", ins.status_code==200, f"count={len(ins.json()) if ins.status_code==200 else '?'}")
pl = requests.get(f"{BASE}/account/plan", headers=H, timeout=10)
P("F2.9 plan tier", pl.status_code==200, f"{pl.json() if pl.status_code==200 else pl.status_code}")
sw = requests.get(f"{BASE}/documents/shared-with-me", headers=H, timeout=10)
P("F2.6 shared-with-me endpoint", sw.status_code==200, f"count={len(sw.json()) if sw.status_code==200 else '?'}")

print("\n===== CLEANUP =====")
d = requests.delete(f"{BASE}/documents/{did}", headers=H, timeout=20)
P("F3.8 delete test doc", d.status_code in (200,204), f"status={d.status_code}")
after = requests.get(f"{BASE}/documents", headers=H, timeout=15).json()
P("account restored", len(after)==len(docs0), f"{len(docs0)} -> {len(after)}")
