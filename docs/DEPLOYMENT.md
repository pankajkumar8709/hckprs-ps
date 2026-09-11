# LifeOS Agent — Deployment Guide

Backend = FastAPI (Python). Frontend = Next.js. DB = Supabase Postgres (pgvector).
Recommended split: **Backend → Render**, **Frontend → Vercel**, **DB → Supabase**
(already provisioned). Any equivalent host works (Railway, Fly.io, a VPS) — only
the platform UI differs; the env vars and steps below are the same.

---

## 0. Prerequisites
- Your code pushed to a Git repo (GitHub/GitLab). `.env` is gitignored — never commit real secrets.
- Supabase project already live (you have `DATABASE_URL`).
- A Groq API key (`gsk_...`).
- Accounts: Render (backend) + Vercel (frontend). Both have free tiers.

---

## 1. Generate production secrets (do this first)

Run locally (Python is available in `backend/.venv`):

```powershell
cd "D:\Code Base\2026\HackSprint\AI-comp\backend"
# 32+ char JWT signing secret
.\.venv\Scripts\python.exe -c "import secrets; print('JWT_SECRET=' + secrets.token_urlsafe(48))"
# Fernet key for document encryption at rest
.\.venv\Scripts\python.exe -c "from cryptography.fernet import Fernet; print('DOC_ENCRYPTION_KEY=' + Fernet.generate_key().decode())"
```

Save both outputs somewhere safe. **Critical:** set `DOC_ENCRYPTION_KEY` explicitly
and never change it after real files exist — files are decrypted with this key.
(If left unset it derives from `JWT_SECRET`, so rotating `JWT_SECRET` would then
break every stored file. Set both explicitly to decouple them.)

---

## 2. Database (Supabase) — one-time

Your DB is live. Just make sure the schema is migrated to the latest revision:

```powershell
cd "D:\Code Base\2026\HackSprint\AI-comp\backend"
# Uses DATABASE_URL from backend/.env
.\.venv\Scripts\python.exe -m alembic upgrade head
```

This applies all migrations incl. `0003_jobs` (async queue tables) and pgvector.
Use the Supabase **Session pooler** connection string as `DATABASE_URL` for a
serverless/edge host; the direct connection is fine for Render.

---

## 3. Backend → Render

### 3a. Create the service
1. Render Dashboard → **New → Web Service** → connect your repo.
2. **Root Directory:** `backend`
3. **Runtime:** Python 3
4. **Build Command:**
   ```
   pip install -r requirements.txt
   ```
5. **Start Command:**
   ```
   uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```
   (Render injects `$PORT`. Do NOT hardcode 8000.)

### 3b. Environment variables (Render → Environment)
| Key | Value |
|---|---|
| `DATABASE_URL` | your Supabase connection string |
| `JWT_SECRET` | the 48-char value from step 1 |
| `DOC_ENCRYPTION_KEY` | the Fernet key from step 1 |
| `LLM_API_KEY` | your `gsk_...` Groq key |
| `LLM_PROVIDER` | `groq` |
| `LLM_MODEL` | `openai/gpt-oss-120b` |
| `CORS_ORIGINS` | your Vercel URL, e.g. `https://lifeos.vercel.app` (set after step 4; comma-separate multiple) |
| `DEBUG` | `false` |
| `RATE_LIMIT_PER_MIN` | `60` |
| `ASYNC_INGEST` | `false` (leave sync unless you also run a worker — see 3d) |

### 3c. Run migrations on Render (once)
Open the Render **Shell** for the service and run:
```
alembic upgrade head
```
(Or add it to the build command: `pip install -r requirements.txt && alembic upgrade head`.)

### 3d. (Optional) Async worker
Only if you set `ASYNC_INGEST=true`. Add a second Render **Background Worker**
service, same repo/root/env, Start Command:
```
python -m app.worker
```
For the hackathon, keep `ASYNC_INGEST=false` (synchronous upload works fine and
needs no extra service).

### 3e. OCR note
Scanned-image PDFs need the Tesseract + Poppler **system binaries**. Render's
default Python image doesn't have them; text-layer PDFs work without. If you need
scanned-PDF OCR, use a Docker deploy with `apt-get install tesseract-ocr poppler-utils`.
Otherwise it degrades gracefully (returns empty text, no crash).

After deploy you'll get a URL like `https://lifeos-api.onrender.com`. Test:
```
https://lifeos-api.onrender.com/health   ->  {"status":"healthy","db":"reachable","queue":"reachable"}
```

---

## 4. Frontend → Vercel

1. Vercel → **Add New → Project** → import the same repo.
2. **Root Directory:** `web`
3. Framework preset auto-detects **Next.js**. Leave build/output defaults.
4. **Environment Variables:**
   | Key | Value |
   |---|---|
   | `NEXT_PUBLIC_API_BASE` | your Render backend URL, e.g. `https://lifeos-api.onrender.com` (HTTPS, no trailing slash) |
5. Deploy. You'll get `https://<project>.vercel.app`.

### 4a. Close the CORS loop
Copy your Vercel URL back into Render's `CORS_ORIGINS` (step 3b) and redeploy the
backend. The frontend origin must be listed or the browser blocks every API call.

---

## 5. Post-deploy verification (do all of these)

```
# 1. Backend health (DB + queue reachable)
curl https://lifeos-api.onrender.com/health

# 2. Metrics respond
curl https://lifeos-api.onrender.com/metrics

# 3. CORS preflight from your real frontend origin returns the allow-origin header
curl -i -X OPTIONS https://lifeos-api.onrender.com/documents \
  -H "Origin: https://<project>.vercel.app" \
  -H "Access-Control-Request-Method: GET"
```
Then in a browser: open the Vercel URL → sign up → upload a document → chat.
If chat/API calls fail with a CORS error, `CORS_ORIGINS` doesn't match the exact
frontend origin (scheme + host, no path).

### Seed a demo account (optional)
```powershell
# points the seed script at the deployed API
.\.venv\Scripts\python.exe backend\scripts\seed_demo.py https://lifeos-api.onrender.com
```

---

## 6. Production hardening checklist (must-review before real users)

- [x] `DEBUG=false` (default in code)
- [x] `.env` gitignored, git history scanned clean
- [x] CORS + API base env-configurable (no code edit)
- [ ] **Strong `JWT_SECRET`** (32+ chars) — set in step 1
- [ ] **Explicit `DOC_ENCRYPTION_KEY`** — set in step 1, never rotate after data exists
- [ ] **HTTPS everywhere** — Render + Vercel give free TLS; ensure `NEXT_PUBLIC_API_BASE` is `https://` (tokens live in `localStorage`; plain HTTP is interceptable)
- [ ] Run `alembic upgrade head` against the prod DB
- [ ] If multi-instance later: move rate-limit + metrics to Redis (they're in-memory/per-process today)

Known limitations to be aware of in production (full detail in
`docs/threat-model.md`): no JWT server-side revocation (tokens valid to 15-min
expiry), account deletion is hard/irreversible, malicious-file check is
signature+structure based not a full sandbox, rate-limit/metrics per-process.

---

## 7. Quick reference — every env var

**Backend (Render):** `DATABASE_URL`, `JWT_SECRET`, `DOC_ENCRYPTION_KEY`,
`LLM_API_KEY`, `LLM_PROVIDER=groq`, `LLM_MODEL=openai/gpt-oss-120b`,
`CORS_ORIGINS`, `DEBUG=false`, `RATE_LIMIT_PER_MIN=60`, `ASYNC_INGEST=false`.

**Frontend (Vercel):** `NEXT_PUBLIC_API_BASE`.

Templates: `backend/.env.example` and `web/.env.example`.
