"""LLM client — Phase 1 MVP single-shot extraction + Q&A.

Provider-switched: works with Groq (OpenAI-compatible, fast) or Gemini. The
plan's stack names CrewAI, but that is a Phase 2 concern (F2.1/F2.2). For the MVP
we make ONE direct model call for extraction and one for Q&A, behind a thin
interface so swapping to a CrewAI crew later is localized.

Provider selection (LLM_PROVIDER): 'auto' (default) picks Groq when the key looks
like a Groq key (gsk_...), else Gemini. Force with 'groq' or 'gemini'.

If LLM_API_KEY is unset (e.g. in tests/CI), calls degrade gracefully: extraction
returns [] and chat returns a canned 'LLM not configured' answer.
"""
from __future__ import annotations

import json
import re

from app.config import settings

# Request timeout (seconds) — fail fast instead of the SDK's minutes-long retry.
_TIMEOUT = 30


def _provider() -> str:
    p = (settings.LLM_PROVIDER or "auto").lower()
    if p in ("groq", "gemini"):
        return p
    # auto-detect from key shape
    return "groq" if settings.LLM_API_KEY.startswith("gsk_") else "gemini"


def _model() -> str:
    if settings.LLM_MODEL:
        return settings.LLM_MODEL
    return ("openai/gpt-oss-120b" if _provider() == "groq"
            else "gemini-flash-latest")


def _configured() -> bool:
    return bool(settings.LLM_API_KEY)


def _generate(prompt: str) -> str:
    """Single text-in/text-out call to the configured provider. '' if not configured."""
    if not _configured():
        return ""
    if _provider() == "groq":
        return _generate_groq(prompt)
    return _generate_gemini(prompt)


def _generate_groq(prompt: str) -> str:
    from groq import Groq

    client = Groq(api_key=settings.LLM_API_KEY, timeout=_TIMEOUT, max_retries=1)
    resp = client.chat.completions.create(
        model=_model(),
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    return (resp.choices[0].message.content or "").strip()


def _generate_gemini(prompt: str) -> str:
    import google.generativeai as genai

    genai.configure(api_key=settings.LLM_API_KEY)
    model = genai.GenerativeModel(_model())
    resp = model.generate_content(
        prompt, request_options={"timeout": _TIMEOUT}
    )
    return (resp.text or "").strip()


_EXTRACT_PROMPT = """You extract key structured fields from a personal document.
Return ONLY a JSON array. Each item: {{"field_name": str, "field_value": str,
"field_type": one of ["date","amount","text","party"], "confidence": 0..1}}.
Pull dates (due/renewal/end), amounts (fees, deposits, premiums), and key parties.
If nothing is extractable, return [].

DOCUMENT TEXT:
---
{text}
---
JSON array:"""


def extract_fields(ocr_text: str) -> list[dict]:
    """Single-shot extraction. Returns a list of field dicts (possibly empty).

    Resilient by design: any LLM/API failure returns [] rather than raising, so an
    LLM outage degrades to 'document saved, zero fields' instead of failing upload.
    """
    if not ocr_text.strip() or not _configured():
        return []
    try:
        raw = _generate(_EXTRACT_PROMPT.format(text=ocr_text[:12000]))
    except Exception:
        return []
    return _parse_field_json(raw)


def _parse_field_json(raw: str) -> list[dict]:
    if not raw:
        return []
    # Strip markdown code fences if the model wrapped the JSON.
    fenced = re.search(r"```(?:json)?\s*(.*?)```", raw, re.DOTALL)
    if fenced:
        raw = fenced.group(1).strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    out: list[dict] = []
    valid_types = {"date", "amount", "text", "party"}
    for item in data:
        if not isinstance(item, dict):
            continue
        ftype = item.get("field_type")
        if ftype not in valid_types:
            ftype = "text"
        name = item.get("field_name")
        if not name:
            continue
        conf = item.get("confidence")
        try:
            conf = float(conf) if conf is not None else None
        except (TypeError, ValueError):
            conf = None
        out.append(
            {
                "field_name": str(name)[:128],
                "field_value": (str(item.get("field_value"))
                                if item.get("field_value") is not None else None),
                "field_type": ftype,
                "confidence": conf,
            }
        )
    return out


_QA_PROMPT = """You are LifeOS, a helpful assistant answering questions about the
user's own documents. Use ONLY the context below. If the answer is not in the
context, say you don't have that information in their documents.

CONTEXT (extracted fields from the user's documents):
{context}

QUESTION: {question}

ANSWER:"""


def answer_question(question: str, context: str) -> str:
    """Single-shot Q&A grounded in the user's own extracted fields."""
    if not _configured():
        return ("LLM is not configured (no LLM_API_KEY), so I can't answer from "
                "your documents yet. Set LLM_API_KEY in backend/.env.")
    if not context.strip():
        return "You don't have any extracted document data yet to answer from."
    try:
        answer = _generate(_QA_PROMPT.format(context=context[:12000], question=question))
    except Exception:
        return "The assistant is temporarily unavailable. Please try again."
    return answer or "I couldn't generate an answer."
