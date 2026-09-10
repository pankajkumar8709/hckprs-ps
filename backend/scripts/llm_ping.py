"""Fast LLM liveness check — one real Gemini call, prints latency + reply."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.services import llm

print("Model:", settings.LLM_MODEL, "| key set:", bool(settings.LLM_API_KEY))
t0 = time.time()
try:
    reply = llm._generate("Reply with exactly: OK")
    dt = time.time() - t0
    print(f"LLM RESPONDING ✓  ({dt:.1f}s)")
    print("Reply:", repr(reply))
except Exception as e:
    dt = time.time() - t0
    print(f"LLM NOT RESPONDING ✗  ({dt:.1f}s)")
    print("Error:", type(e).__name__, str(e)[:300])
