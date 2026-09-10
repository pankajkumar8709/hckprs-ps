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


def _generate_groq(prompt: str, max_tokens: int | None = None) -> str:
    from groq import Groq

    client = Groq(api_key=settings.LLM_API_KEY, timeout=_TIMEOUT, max_retries=1)
    kwargs = {}
    if max_tokens:
        kwargs["max_tokens"] = max_tokens
    resp = client.chat.completions.create(
        model=_model(),
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        **kwargs,
    )
    return (resp.choices[0].message.content or "").strip()


def _stream_groq(prompt: str, max_tokens: int | None = None):
    """Yield answer chunks as they generate (perceived-latency win)."""
    from groq import Groq

    client = Groq(api_key=settings.LLM_API_KEY, timeout=_TIMEOUT, max_retries=1)
    kwargs = {}
    if max_tokens:
        kwargs["max_tokens"] = max_tokens
    stream = client.chat.completions.create(
        model=_model(),
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        stream=True,
        **kwargs,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content if chunk.choices else None
        if delta:
            yield delta


def _generate_gemini(prompt: str) -> str:
    import google.generativeai as genai

    genai.configure(api_key=settings.LLM_API_KEY)
    model = genai.GenerativeModel(_model())
    resp = model.generate_content(
        prompt, request_options={"timeout": _TIMEOUT}
    )
    return (resp.text or "").strip()


_EXTRACT_PROMPT = """You extract a fixed set of fields from a personal document.
Return ONLY a JSON object (no prose, no markdown) with EXACTLY these keys:
{{
  "doc_type": one of ["lease","insurance","loan_emi","subscription","medical","other"],
  "key_dates": [{{"label": str, "value": "YYYY-MM-DD or as written"}}],
  "amounts":   [{{"label": str, "value": str}}],
  "parties":   [{{"label": str, "value": str}}],
  "summary":   str
}}
Pull dates (due/renewal/end/start), amounts (fees, deposits, premiums, totals),
and key parties (people/organizations). Write a 1-3 sentence plain-language summary.
Use empty arrays / "other" / "" when a section has nothing. Return the object even
if most fields are empty.

DOCUMENT TEXT:
---
{text}
---
JSON object:"""


def extract_document(ocr_text: str) -> dict:
    """Single-shot extraction returning the fixed F1.3 schema.

    Returns {"doc_type","key_dates","amounts","parties","summary","fields"} where
    `fields` is the flattened list of ExtractedField-shaped dicts. Resilient: any
    LLM/API failure returns an empty-but-valid structure (doc stays saved).
    """
    empty = {"doc_type": "other", "key_dates": [], "amounts": [],
             "parties": [], "summary": "", "fields": []}
    if not ocr_text.strip() or not _configured():
        return empty
    try:
        raw = _generate(_EXTRACT_PROMPT.format(text=ocr_text[:12000]))
    except Exception:
        return empty
    return _parse_extraction(raw)


# Backwards-compatible helper: flat list of ExtractedField dicts.
def extract_fields(ocr_text: str) -> list[dict]:
    return extract_document(ocr_text)["fields"]


_VALID_DOC_TYPES = {"lease", "insurance", "loan_emi", "subscription", "medical", "other"}


def _parse_extraction(raw: str) -> dict:
    empty = {"doc_type": "other", "key_dates": [], "amounts": [],
             "parties": [], "summary": "", "fields": []}
    if not raw:
        return empty
    fenced = re.search(r"```(?:json)?\s*(.*?)```", raw, re.DOTALL)
    if fenced:
        raw = fenced.group(1).strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return empty
    if not isinstance(data, dict):
        return empty

    doc_type = data.get("doc_type")
    if doc_type not in _VALID_DOC_TYPES:
        doc_type = "other"
    summary = str(data.get("summary") or "").strip()

    def _pairs(section):
        out = []
        if isinstance(section, list):
            for item in section:
                if isinstance(item, dict):
                    label = item.get("label") or item.get("name")
                    value = item.get("value")
                    if value is not None:
                        out.append((str(label or "")[:128], str(value)))
                elif item is not None:
                    out.append(("", str(item)))
        return out

    fields: list[dict] = []
    for label, value in _pairs(data.get("key_dates")):
        fields.append({"field_name": label or "date", "field_value": value,
                       "field_type": "date", "confidence": None})
    for label, value in _pairs(data.get("amounts")):
        fields.append({"field_name": label or "amount", "field_value": value,
                       "field_type": "amount", "confidence": None})
    for label, value in _pairs(data.get("parties")):
        fields.append({"field_name": label or "party", "field_value": value,
                       "field_type": "party", "confidence": None})
    if summary:
        fields.append({"field_name": "summary", "field_value": summary,
                       "field_type": "text", "confidence": None})

    return {
        "doc_type": doc_type,
        "key_dates": data.get("key_dates") or [],
        "amounts": data.get("amounts") or [],
        "parties": data.get("parties") or [],
        "summary": summary,
        "fields": fields,
    }


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
        prompt = _QA_PROMPT.format(context=context[:_QA_CONTEXT_CHARS], question=question)
        if _provider() == "groq":
            answer = _generate_groq(prompt, max_tokens=_ANSWER_MAX_TOKENS)
        else:
            answer = _generate(prompt)
    except Exception:
        return "The assistant is temporarily unavailable. Please try again."
    return answer or "I couldn't generate an answer."


# Latency tuning: trimmed context + bounded generation. Enough for grounded Q&A
# over personal documents; no feature loss.
_QA_CONTEXT_CHARS = 6000
_ANSWER_MAX_TOKENS = 400


def answer_question_stream(question: str, context: str):
    """Streaming Q&A: yields answer chunks. Falls back to a single yield for the
    non-Groq path or the not-configured / empty-context cases."""
    if not _configured():
        yield ("LLM is not configured (no LLM_API_KEY), so I can't answer from "
               "your documents yet. Set LLM_API_KEY in backend/.env.")
        return
    if not context.strip():
        yield "You don't have any extracted document data yet to answer from."
        return
    prompt = _QA_PROMPT.format(context=context[:_QA_CONTEXT_CHARS], question=question)
    try:
        if _provider() == "groq":
            got = False
            for chunk in _stream_groq(prompt, max_tokens=_ANSWER_MAX_TOKENS):
                got = True
                yield chunk
            if not got:
                yield "I couldn't generate an answer."
        else:
            yield _generate(prompt) or "I couldn't generate an answer."
    except Exception:
        yield "The assistant is temporarily unavailable. Please try again."


# =====================================================================
# PHASE 2 — Groq-based "agents" (no CrewAI). Each function is one agent;
# the ingestion pipeline (F2.2) chains them and records a visible trace.
# =====================================================================

_CLASSIFY_PROMPT = """You are a document classification agent. Read the document
text and return ONLY a JSON object (no prose, no markdown):
{{"doc_type": one of ["lease","insurance","loan_emi","subscription","medical","other"],
  "confidence": a number 0.0-1.0}}
Choose "other" if it clearly fits none. Base confidence on how clearly the text
matches the chosen type.

DOCUMENT TEXT:
---
{text}
---
JSON:"""


def classify_document(ocr_text: str) -> dict:
    """F2.1 Classification Agent: OCR text -> {doc_type, confidence}. Resilient."""
    fallback = {"doc_type": "other", "confidence": 0.0}
    if not ocr_text.strip() or not _configured():
        return fallback
    try:
        raw = _generate(_CLASSIFY_PROMPT.format(text=ocr_text[:6000]))
    except Exception:
        return fallback
    data = _loads_json(raw)
    if not isinstance(data, dict):
        return fallback
    doc_type = data.get("doc_type")
    if doc_type not in _VALID_DOC_TYPES:
        doc_type = "other"
    try:
        conf = float(data.get("confidence"))
    except (TypeError, ValueError):
        conf = 0.0
    return {"doc_type": doc_type, "confidence": max(0.0, min(1.0, conf))}


def _loads_json(raw: str):
    if not raw:
        return None
    fenced = re.search(r"```(?:json)?\s*(.*?)```", raw, re.DOTALL)
    if fenced:
        raw = fenced.group(1).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # try to salvage the first {...} block
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                return None
        return None


def _validate_fields(fields: list[dict], ocr_text: str) -> tuple[list[dict], list[dict]]:
    """F2.2 Validator Agent (deterministic, no LLM cost).

    Cross-checks each date/amount field's value against the actual OCR text: the
    core token(s) of the value must appear verbatim in the source. Fields that
    cannot be located are flagged and dropped (not silently accepted).

    Returns (accepted_fields, rejected_records).
    """
    haystack = ocr_text.lower()
    accepted: list[dict] = []
    rejected: list[dict] = []
    for f in fields:
        ftype = f.get("field_type")
        value = (f.get("field_value") or "").strip()
        # Only verify the "hard facts" — dates and amounts. Parties/summary are prose.
        if ftype in ("date", "amount") and value:
            # Pull comparable tokens: digits runs (years, amounts) must be present.
            tokens = re.findall(r"\d[\d,./-]*\d|\d", value)
            located = all(t.replace(",", "").lower() in haystack.replace(",", "")
                          for t in tokens) if tokens else (value.lower() in haystack)
            if not located:
                rejected.append({
                    "field_name": f.get("field_name"),
                    "field_type": ftype,
                    "field_value": value,
                    "reason": "value not found verbatim in source text",
                })
                continue
        accepted.append(f)
    return accepted, rejected


def ingest_document(ocr_text: str) -> dict:
    """F2.1 + F2.2 pipeline: Classification -> Extraction -> Validation.

    Returns {doc_type, confidence, fields, agent_trace, status} where agent_trace
    is a list of {agent, action, ...} steps for the demo's "How this was
    extracted" view. status is 'done' normally, 'failed' if the validator rejects
    every hard fact it saw (a document whose extracted dates/amounts are all
    unverifiable — a likely hallucination or bad OCR).
    """
    trace: list[dict] = []

    cls = classify_document(ocr_text)
    trace.append({
        "agent": "ClassificationAgent",
        "action": "classify",
        "doc_type": cls["doc_type"],
        "confidence": cls["confidence"],
    })

    extracted = extract_document(ocr_text)
    # Prefer the dedicated classifier's doc_type over the extractor's guess.
    doc_type = cls["doc_type"] if cls["confidence"] >= 0.4 else extracted["doc_type"]
    fields = extracted["fields"]
    trace.append({
        "agent": "ExtractionAgent",
        "action": "extract",
        "fields_found": len(fields),
        "doc_type_used": doc_type,
    })

    accepted, rejected = _validate_fields(fields, ocr_text)
    trace.append({
        "agent": "ValidatorAgent",
        "action": "validate",
        "accepted": len(accepted),
        "rejected": len(rejected),
        "rejected_fields": rejected,
    })

    # Fail only if there WERE hard facts and ALL of them were rejected.
    hard_facts = [f for f in fields if f.get("field_type") in ("date", "amount")]
    status = "done"
    if hard_facts and not any(f.get("field_type") in ("date", "amount") for f in accepted):
        status = "failed"

    return {
        "doc_type": doc_type,
        "confidence": cls["confidence"],
        "fields": accepted,
        "agent_trace": trace,
        "status": status,
    }


_ROUTER_PROMPT = """Classify the user's chat message intent. Return ONLY one word
from this set: question, show_reminders, show_insights, upload_help, general.

Rules:
- question: ANY request for information that could be answered from the user's
  documents — including asking about a deadline, due date, timeline, amount,
  party, or "what does X say". If the user wants a FACT, it is `question`.
- show_reminders: ONLY when the user explicitly asks to see/list their reminder
  or task LIST itself, e.g. "show my reminders", "what's on my to-do list",
  "list my tasks". Not for asking when a specific thing is due.
- show_insights: explicitly asks to see conflicts/clashes/insights across docs.
- upload_help: asks HOW to upload / add a document.
- general: greetings or anything unrelated to documents.

When in doubt between question and show_reminders, choose question.

MESSAGE: {message}
INTENT:"""

_VALID_INTENTS = {"question", "show_reminders", "show_insights", "upload_help", "general", "create_task"}


def route_intent(message: str) -> str:
    """F2.5 Router: keyword-first, LLM only as a rare fallback.

    Nearly every message is a `question`, so we AVOID a second Groq round-trip on
    the chat critical path: only explicit list/help phrasings are matched cheaply,
    and the LLM router is consulted just for a small ambiguous middle ground.
    """
    m = (message or "").lower().strip()
    if not m:
        return "general"

    # Cheap, unambiguous matches — no LLM call.
    reminder_kw = ("show my reminder", "list my reminder", "my reminders",
                   "my tasks", "to-do", "to do list", "todo list", "my to-do")
    insight_kw = ("show insight", "my insights", "any conflicts", "date clash",
                  "clashing", "renewal risk", "cross-document")
    upload_kw = ("how do i upload", "how to upload", "how do i add a document",
                 "how to add a document")
    create_kw = ("remind me", "add a reminder", "add a task", "create a task",
                 "create a reminder", "set a reminder", "add task", "new task",
                 "add to my tasks", "add to my reminders")
    if any(k in m for k in create_kw):
        return "create_task"
    if any(k in m for k in upload_kw):
        return "upload_help"
    if any(k in m for k in reminder_kw):
        return "show_reminders"
    if any(k in m for k in insight_kw):
        return "show_insights"

    # Everything else is treated as a question WITHOUT an LLM call — the chat
    # handler falls back to reminders/insights data only when Q&A finds nothing.
    return "question"


_TASK_PROMPT = """Extract the task/reminder(s) the user wants to create from their
message. Return ONLY a JSON object:
{{"tasks": [{{"title": str, "due_date": "YYYY-MM-DD or null"}}]}}
Today's date is {today}. Resolve relative dates ("next friday", "in 3 days",
"end of month") to an absolute YYYY-MM-DD. If no date is given, use null. Keep
each title short and action-oriented. Return an empty list if there is no task.

MESSAGE: {message}
JSON:"""


def extract_task_request(message: str, today: str) -> list[dict]:
    """Multi-step action helper: parse a create-task request into structured
    tasks [{title, due_date}]. Resilient: [] on any failure."""
    if not _configured():
        return []
    try:
        raw = _generate(_TASK_PROMPT.format(today=today, message=message[:1000]))
    except Exception:
        return []
    data = _loads_json(raw)
    if not isinstance(data, dict):
        return []
    tasks = data.get("tasks")
    if not isinstance(tasks, list):
        return []
    out = []
    for t in tasks:
        if isinstance(t, dict) and t.get("title"):
            dd = t.get("due_date")
            out.append({
                "title": str(t["title"])[:512],
                "due_date": dd if isinstance(dd, str) and dd.lower() != "null" else None,
            })
    return out[:10]
