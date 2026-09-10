"""Probe: does Gemini extraction error, or genuinely return no fields?"""
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.services import llm

print("key set:", bool(settings.LLM_API_KEY), "| model:", settings.LLM_MODEL)
txt = ("DataForge Rime Track Project Plan. A high-stakes, immersive conversational "
       "loop. Budget: 50000 USD. Deadline: 2026-12-15. Owner: Jane Smith. "
       "Kickoff date 2026-10-01. Renewal review 2027-01-10.")
try:
    raw = llm._generate(llm._EXTRACT_PROMPT.format(text=txt))
    print("RAW RESPONSE >>>")
    print(repr(raw)[:2000])
    print("PARSED FIELDS >>>", llm._parse_field_json(raw))
except Exception:
    traceback.print_exc()
