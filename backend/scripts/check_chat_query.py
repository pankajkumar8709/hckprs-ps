"""Test LLM chat with real queries grounded in an uploaded document."""
import io
import sys
import uuid

import requests

BASE = "http://127.0.0.1:8075"
email = f"q_{uuid.uuid4().hex[:8]}@example.com"


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

doc_text = (
    "DataForge Voice-Native Field Operations Assistant - Project Plan. "
    "The core differentiator is a voice-native architecture where speech is the "
    "primary medium of interaction, not an accessibility layer. "
    "Team members: Alice Kumar (lead), Ravi Sharma (backend), Meera Nair (Android). "
    "Milestones: prototype due 2026-10-01, beta 2026-11-15, final submission 2026-12-15. "
    "Budget allocated is 75000 USD. Deliverables to submit: a working demo, a "
    "technical design document, and a 3-minute pitch video. "
    "The tech stack is FastAPI backend with a Kotlin Android client."
)
requests.post(f"{BASE}/documents/upload", headers=hdr,
              files={"file": ("project_plan.pdf", io.BytesIO(make_pdf(doc_text)), "application/pdf")},
              timeout=120)

queries = [
    "Who is the team lead?",
    "What is the final submission date and the budget?",
    "What do we have to submit?",
    "What is the CEO's home address?",  # not present -> should decline
]
conv = None
for q in queries:
    payload = {"message": q}
    if conv: payload["conversation_id"] = conv
    r = requests.post(f"{BASE}/chat", headers=hdr, json=payload, timeout=120)
    body = r.json()
    conv = body["conversation_id"]
    print("Q:", q)
    print("A:", body["message"]["content"])
    print("-" * 60)
