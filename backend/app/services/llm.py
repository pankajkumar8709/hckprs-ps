"""LLM client — Phase 1 MVP single-shot extraction + Q&A via Gemini.

The plan's stack names CrewAI, but that is a Phase 2 concern (F2.1/F2.2). For the
MVP we make ONE direct model call for extraction and one for Q&A, behind a thin
interface so swapping to a CrewAI crew later is localized.

If LLM_API_KEY is unset (e.g. in tests/CI), calls degrade gracefully: extraction
returns [] and chat returns a canned 'LLM not configured' answer, so the upload
and chat flows still work end-to-end without a live key.
"""
from __future__ import annotations

import json
import re

from app.config import settings

# Default to the stable 'latest' alias so the model name doesn't rot; override
# via LLM_MODEL in .env. (gemini-1.5-flash was retired on public v1beta.)
_MODEL = getattr(settings, "LLM_MODEL", None) or "gemini-flash-latest"


def _configured() -> bool:
    return bool(settings.LLM_API_KEY)


def _generate(prompt: str) -> str:
    """Single text-in/text-out call to Gemini. Returns '' if not configured."""
    if not _configured():
        return ""
    import google.generativeai as genai

    genai.configure(api_key=settings.LLM_API_KEY)
    model = genai.GenerativeModel(_MODEL)
    resp = model.generate_content(prompt)
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
