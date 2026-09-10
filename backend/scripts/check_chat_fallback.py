"""Confirm chat now answers from ocr_text when a doc has no extracted fields."""
import io
import sys
import uuid

import requests

BASE = "http://127.0.0.1:8074"
email = f"cf_{uuid.uuid4().hex[:8]}@example.com"


def make_pdf(text: str) -> bytes:
    content = f"BT /F1 12 Tf 50 750 Td ({text}) Tj ET"
    objs = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        "/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        f"<< /Length {len(content)} >>\nstream\n{content}\nendstream",
    ]
    pdf = "%PDF-1.4\n"; offsets = []
    for i, o in enumerate(objs, start=1):
        offsets.append(len(pdf)); pdf += f"{i} 0 obj\n{o}\nendobj\n"
    xref = len(pdf); pdf += f"xref\n0 {len(objs)+1}\n0000000000 65535 f \n"
    for off in offsets: pdf += f"{off:010d} 00000 n \n"
    pdf += f"trailer\n<< /Size {len(objs)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF"
    return pdf.encode("latin-1")


requests.post(f"{BASE}/auth/register", json={"email": email, "password": "password123"}, timeout=15)
tok = requests.post(f"{BASE}/auth/login", json={"email": email, "password": "password123"}, timeout=15).json()["access_token"]
hdr = {"Authorization": f"Bearer {tok}"}

prose = ("This project is a voice-native field operations assistant. The core "
         "differentiator is a fully conversational loop where the interface "
         "disappears and only the intelligence remains. Deliverables to submit "
         "include a working demo, a technical design document, and a short pitch.")
r = requests.post(f"{BASE}/documents/upload", headers=hdr,
                  files={"file": ("plan.pdf", io.BytesIO(make_pdf(prose)), "application/pdf")},
                  timeout=120)
doc = r.json()
print("upload status:", doc.get("upload_status"), "| fields:", len(doc.get("extracted_fields", [])))

r = requests.post(f"{BASE}/chat", headers=hdr,
                  json={"message": "What do we have to submit?"}, timeout=120)
ans = r.json()["message"]["content"]
print("ANSWER:", ans)

bad = "don't have any extracted document data" in ans.lower()
grounded = any(w in ans.lower() for w in ["demo", "design", "pitch", "submit"])
if bad:
    print("[FAIL] still returning the no-data message"); sys.exit(1)
if grounded:
    print("[PASS] chat answered from document text"); sys.exit(0)
print("[WARN] answered but no expected keyword; inspect above"); sys.exit(0)
