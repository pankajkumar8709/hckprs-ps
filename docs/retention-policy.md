# LifeOS Agent — Data Retention & Deletion Policy

## Retention
- **Documents, extracted fields, reminders, insights, embeddings, chat history,
  audit logs** are retained **for as long as the user's account exists**. There
  is no automatic time-based expiry in the MVP.
- **Signed download tokens** are not stored — they are stateless HMAC tokens
  with a **5-minute TTL** and simply stop verifying after that.
- **Prompts sent to the LLM (Groq)** are not persisted by LifeOS. Groq's own
  retention is governed by Groq's terms (third-party processor).

## What deletion actually does (F3.8 — right to be forgotten)
`DELETE /account` performs a **hard, immediate, irreversible** cascade for the
authenticated user:

1. **Storage files** on disk are deleted (the encrypted `.enc` blobs).
2. **Vector embeddings** in `document_chunks` are deleted — verified by a direct
   query returning 0 rows for the user afterward (this is the step most systems
   fake; here it is explicit and tested).
3. **All Postgres rows** for the user are deleted: `extracted_fields`,
   `messages`, `reminders`, `insights`, `conversations`, `share_grants`
   (as owner or recipient), `documents`, `audit_logs`.
4. **The `users` row** is deleted last.

After deletion, login with the old credentials fails (verified).

### Individual document deletion
`DELETE /documents/{id}` removes one document and cascades its extracted fields,
chunks, and reminders (FK `ON DELETE CASCADE` + explicit chunk handling).

## Known limitations (honest)
- **No soft-delete or grace period.** Deletion is immediate and cannot be undone.
  There is no "trash" or recovery window.
- **Storage-file removal is best-effort.** If an on-disk file is already missing
  or locked at deletion time, the cascade continues rather than aborting (the DB
  rows are still removed). A stale file could in theory remain on disk without a
  DB reference; a periodic reconciliation sweep is recommended for production.
- **LLM-side copies.** Any text already sent to Groq during processing is
  outside LifeOS's deletion scope — governed by the provider. This is inherent
  to using a third-party LLM and is disclosed in data-flow.md.
- **Backups.** If the Supabase project has point-in-time backups enabled, a
  user's data may persist in backups until those backups age out — the
  application-level delete does not purge historical backups.
