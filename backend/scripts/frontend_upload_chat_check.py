"""Live upload + chat as ac@gmail.com through the frontend's API path.

ONE upload, ONE chat (memory-conscious). Also does the free F3.6 spoof-reject
(no LLM). Mirrors web/src/lib/api.ts: POST /documents (multipart), GET
/documents/{id} to poll, POST /chat for the grounded Q&A.
"""
import io
import sys
import time
import requests

BASE = "http://127.0.0.1:8000"
r = requests.post(f"{BASE}/auth/login", json={"email": "ac@gmail.com", "password": "12345678"}, timeout=15)
r.raise_for_status()
access = r.json().get("access_token") or r.json().get("token")
H = {"Authorization": f"Bearer {access}"}
print(f"[PASS] login ac@gmail.com ({r.status_code})")

# --- F3.6 live: a Windows EXE renamed .pdf must be rejected (no LLM cost) ---
exe = b"MZ\x90\x00" + b"\x00" * 200
sp = requests.post(f"{BASE}/documents/upload", headers=H,
                   files={"file": ("invoice.pdf", io.BytesIO(exe), "application/pdf")}, timeout=20)
print(f"[{'PASS' if sp.status_code == 400 else 'FAIL'}] F3.6 spoofed .exe-as-.pdf rejected: status={sp.status_code}")

# --- Upload ONE small real PDF (a lease with a clear renewal date + rent) ---
def _pdf(text: str) -> bytes:
    esc = text.replace("(", r"\(").replace(")", r"\)")
    content = f"BT /F1 11 Tf 40 760 Td ({esc}) Tj ET".encode()
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

pdf = _pdf("Residential Lease Agreement. Monthly rent is 2400 dollars. "
           "The lease renewal date is March 15 2026.")
up = requests.post(f"{BASE}/documents/upload", headers=H,
                   files={"file": ("lease_qa_test.pdf", io.BytesIO(pdf), "application/pdf")}, timeout=60)
if up.status_code not in (200, 201):
    print(f"[FAIL] upload: status={up.status_code} body={up.text[:300]}"); sys.exit(2)
doc = up.json(); did = doc.get("id")
print(f"[PASS] upload lease_qa_test.pdf ({up.status_code}) id={did}")

# --- Poll until processed (synchronous mode usually returns done already) ---
status = doc.get("upload_status")
for _ in range(20):
    if status in ("processed", "done", "completed", "ready"):
        break
    time.sleep(2)
    g = requests.get(f"{BASE}/documents/{did}", headers=H, timeout=20)
    status = g.json().get("upload_status")
print(f"[INFO] processing status = {status}")
detail = requests.get(f"{BASE}/documents/{did}", headers=H, timeout=20).json()
fields = detail.get("fields") or detail.get("extracted_fields") or []
print(f"[{'PASS' if fields else 'WARN'}] extraction produced {len(fields)} fields")
trace = detail.get("agent_trace") or detail.get("agent_trace_json")
print(f"[{'PASS' if trace else 'WARN'}] agent_trace present: {bool(trace)}")

# --- ONE grounded chat question (RAG path, user-scoped) ---
q = "What is the renewal date and the monthly rent in my lease?"
c = requests.post(f"{BASE}/chat", headers=H, json={"message": q}, timeout=90)
if c.status_code != 200:
    print(f"[FAIL] chat: status={c.status_code} body={c.text[:300]}"); sys.exit(2)
ans = c.json()
msg = ans.get("message") or {}
text = (msg.get("content") or msg.get("text") or "").lower()
cites = ans.get("citations") or []
intent = ans.get("intent")
print(f"\n[CHAT ANSWER] {text[:300]}\n")
print(f"[INFO] intent={intent}")
grounded = ("march" in text or "2026" in text) and ("2400" in text or "2,400" in text)
print(f"[{'PASS' if grounded else 'FAIL'}] answer grounded (renewal date + rent from the doc): {grounded}")
print(f"[{'PASS' if cites else 'WARN'}] citations returned: {cites if cites else '(none)'}")

# --- Cleanup: delete the throwaway test doc so the account stays clean ---
d = requests.delete(f"{BASE}/documents/{did}", headers=H, timeout=20)
print(f"[{'PASS' if d.status_code in (200,204) else 'WARN'}] cleanup delete test doc: status={d.status_code}")
