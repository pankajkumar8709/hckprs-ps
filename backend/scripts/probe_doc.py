"""Read the latest uploaded document's stored text and run real extraction on it."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import Document, ExtractedField
from app.services import llm

db = SessionLocal()
doc = db.query(Document).order_by(Document.created_at.desc()).first()
if not doc:
    print("No documents in DB.")
    sys.exit(0)

print("Latest doc:", doc.filename, "| status:", doc.upload_status)
text = doc.ocr_text or ""
print("ocr_text length:", len(text))
print("--- first 800 chars of stored text ---")
print(text[:800])
print("--- end ---")

existing = db.query(ExtractedField).filter(ExtractedField.document_id == doc.id).count()
print("existing extracted_fields rows:", existing)

print("\nRe-running extraction on the STORED text...")
fields = llm.extract_fields(text)
print("extracted", len(fields), "fields:")
for f in fields:
    print("  -", f)
db.close()
