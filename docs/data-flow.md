# LifeOS Agent — Data Flow

What data the AI processes, at which stage, and what is persisted vs. ephemeral.

## 1. Upload
- **Input:** the raw file (PDF/JPG/PNG/TXT/MD) + the authenticated `user_id`.
- **Checks:** size cap, content-based MIME verification (F3.6).
- **Stored:** the file is **encrypted (Fernet) at rest** on local disk
  (`backend/storage/<user_id>/<uuid>.enc`). The plaintext filename is kept only
  as metadata on the `documents` row, not as the on-disk name.

## 2. Text extraction
- **Input to code (not AI):** file bytes → `pypdf` text layer, OCR fallback
  (`pytesseract`/`pdf2image`) for scans.
- **Stored:** extracted plain text in `documents.ocr_text`.

## 3. AI extraction pipeline (this is where the LLM sees data)
- **Sent to the LLM (Groq):** the document's `ocr_text` (truncated), inside a
  fenced "untrusted data" block in the **user** message; the **system** message
  contains only fixed instructions (no document text).
- **AI output:** a fixed JSON schema `{doc_type, key_dates, amounts, parties,
  summary}`, validated (dates/amounts must appear verbatim in the source).
- **Stored:** `extracted_fields` rows + `doc_type` + `agent_trace_json` on the
  document. Reminders (`reminders`) auto-created from date fields. Insights
  (`insights`) recomputed across the user's reminders.

## 4. Embedding / RAG index
- **Sent to the local model (NOT a third party):** `ocr_text` chunks →
  `all-MiniLM-L6-v2` embeddings **computed locally** (no network). Groq never
  receives the embeddings step.
- **Stored:** `document_chunks` rows (content + 384-dim vector), tagged with
  `user_id` + `document_id`.

## 5. Chat / Q&A
- **Retrieval:** the user's question is embedded locally; a pgvector similarity
  search runs **filtered by `user_id` in SQL** and returns only that user's
  chunks.
- **Sent to the LLM (Groq):** the question + the retrieved chunks (that user's
  data only), again as fenced untrusted data under a fixed system prompt.
- **AI output:** a grounded answer + citations (which of the user's documents
  it drew from).
- **Stored:** `conversations` + `messages` rows (the chat history), user-scoped.

## What leaves the machine
- **To Groq (LLM API):** document text and questions during extraction/Q&A —
  only the current user's own content, only for the duration of the request.
  Groq is a third-party processor; see retention-policy.md.
- **Nothing else** goes off-machine: embeddings are computed locally, files are
  stored locally (encrypted), the DB is the user's Supabase project.

## Ephemeral vs. stored
| Data | Stored? | Where |
|---|---|---|
| Raw file | Yes (encrypted) | `backend/storage/*.enc` |
| Extracted text | Yes | `documents.ocr_text` |
| Extracted fields, doc_type, agent trace | Yes | `extracted_fields`, `documents` |
| Reminders / insights | Yes | `reminders`, `insights` |
| Embeddings | Yes | `document_chunks` (pgvector) |
| Chat history | Yes | `conversations`, `messages` |
| Signed download tokens | No (stateless HMAC, 5-min TTL) | — |
| Prompts sent to Groq | Not persisted by us | transient request only |
| Audit events | Yes | `audit_logs` |
