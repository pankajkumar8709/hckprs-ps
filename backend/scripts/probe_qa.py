"""Reveal the real exception behind 'temporarily unavailable' in chat Q&A."""
import os
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services import llm

ctx = ("Team lead: Alice Kumar. Budget: 75000 USD. Final submission 2026-12-15. "
       "Deliverables: demo, design document, pitch video.")
prompt = llm._QA_PROMPT.format(context=ctx, question="Who is the team lead?")
t0 = time.time()
try:
    r = llm._generate(prompt)
    print(f"OK in {time.time()-t0:.1f}s ->", repr(r)[:500])
except Exception:
    print(f"RAISED after {time.time()-t0:.1f}s:")
    traceback.print_exc()
