# AgriGen AI: Leaving Cert Agricultural Science Tutor

[![Live demo](https://img.shields.io/badge/Demo-Vercel-black)](https://final-year-project-delta-coral.vercel.app/)
![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![FastAPI](https://img.shields.io/badge/API-FastAPI-009688.svg)
![Next.js](https://img.shields.io/badge/Frontend-Next.js-black)

## Project overview

**Live app:** [final-year-project-delta-coral.vercel.app](https://final-year-project-delta-coral.vercel.app/)

AgriGen AI is a web application focused on the **Irish Leaving Certificate Agricultural Science** course. It helps teachers generate exam-style material and helps students practise with immediate feedback.

General purpose chat tools can drift off syllabus or tone. This project keeps generation and judging **tied to exam-style prompts and official-style marking logic**, with optional **avatar video** feedback when D-ID is configured.

---

## Key features

### For teachers

- **Question generation:** Topic- and level-aware prompts aligned with SEC-style long answers.
- **Export:** Download generated exams with marking schemes as **PDF** or **DOCX** (`python-docx`, ReportLab).

### For students

- **Practice mode:** Answer in the browser and submit for feedback.
- **Judging engine:** OpenAI compares answers to the supplied marking scheme so paraphrasing can still earn credit where appropriate.
- **Avatar and voice:** Optional D-ID **Talks** video plus TTS-style delivery of feedback when API keys are present.

---

## Technical architecture

1. **Question generation:** With `OLLAMA_BASE_URL` set (for example `http://localhost:11434/v1`), a local **Ollama** model (default `llama3.1:8b`, overridable via `MODEL_NAME`) generates questions. If Ollama errors at runtime, the service **falls back to OpenAI** (`CHATGPT_MODEL`). If `OLLAMA_BASE_URL` is omitted, generation uses **OpenAI only** (requires `OPENAI_API_KEY`).
2. **Feedback and judging (OpenAI):** The OpenAI API implements structured feedback and mark-style commentary (`CHATGPT_MODEL`, default `gpt-4o-mini`).
3. **Persistence:** **PostgreSQL** (async SQLAlchemy + `asyncpg`) stores users and generated exams; **Alembic** manages schema migrations.
4. **Auth:** **Google OAuth** (Authlib) with session cookies; JWT used where configured for API flows.
5. **Frontend:** **Next.js** (App Router), **React**, **Tailwind CSS**, calling the FastAPI backend via `NEXT_PUBLIC_API_URL`.

---

## Tech stack

| Area | Technologies |
|------|----------------|
| Backend | Python, FastAPI, Uvicorn, Pydantic, SQLAlchemy, Alembic, Authlib |
| AI | Ollama (generation), OpenAI (feedback / TTS helpers), optional D-ID (avatar video) |
| Frontend | Next.js, React, Axios, Framer Motion, Vitest |
| Data | PostgreSQL (`asyncpg`); SQLite async URL supported for tests / local experiments |
| Documents | python-docx, ReportLab |

---

## Prerequisites

- **Python** 3.10+ and **pip**
- **Node.js** 18+ (20+ recommended for Next.js 16)
- **PostgreSQL** database URL (for example [Neon](https://neon.tech/)) — set `DATABASE_URL` to an `postgresql+asyncpg://...` connection string
- **Ollama** (optional) with your chosen model pulled, if you prefer local generation instead of OpenAI-only
- **OpenAI** API key for feedback features
- **Google Cloud OAuth** client (web application) for sign-in — authorised redirect URIs must match your FastAPI auth callback URL

---

## Installation and setup

### 1. Clone the repository

```bash
git clone https://github.com/roxaaaaa/final-year-project.git
cd final-year-project
```

### 2. Backend dependencies

From the repository root (this installs `backend/requirements.txt`):

```bash
pip install -r requirements.txt
```

### 3. Backend environment

Create `backend/.env` by copying and editing [`backend/env_example`](backend/env_example). Typical variables:

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@host/db?ssl=require` |
| `OPENAI_API_KEY` | OpenAI API access (required for feedback; also used for generation if Ollama is unavailable) |
| `OLLAMA_BASE_URL` | Optional. Ollama OpenAI-compatible base URL, e.g. `http://localhost:11434/v1`. If unset, questions are generated with OpenAI only. |
| `MODEL_NAME` | Ollama model id (default `llama3.1:8b`) |
| `CHATGPT_MODEL` | OpenAI chat model for feedback (default `gpt-4o-mini`) |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Google OAuth credentials |
| `FRONTEND_URL` | Frontend origin, e.g. `http://localhost:3000` |
| `SESSION_SECRET` | Secret for Starlette session middleware |
| `JWT_SECRET` | Secret for JWT signing |
| `DID_API_KEY` | Optional — D-ID avatar video |
| `DID_AVATAR_ENABLED` | Optional — `true` / `false` to toggle D-ID |

Apply database migrations from the `backend` folder:

```bash
cd backend
alembic upgrade head
```

Alternatively, with `DATABASE_URL` set, you can run `python create_tables.py` for a one-off schema create (migrations are preferred for production).

### 4. Frontend

```bash
cd frontend
npm install
```

Copy `frontend/env_example` to `frontend/.env.local` and set:

```env
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

Use your deployed API URL in production.

---

## Running locally

Use two terminals.

**Terminal 1 — API (from `backend`):**

```bash
cd backend
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 — web app (from `frontend`):**

```bash
cd frontend
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). For Ollama-backed generation, run Ollama and `ollama pull` your `MODEL_NAME`. For OpenAI-only generation, leave `OLLAMA_BASE_URL` unset and set `OPENAI_API_KEY`.

---

## Tests

Backend unit tests (SQLite test database is configured in `conftest.py`):

```bash
cd backend
pytest
```

Frontend:

```bash
cd frontend
npm test
```

---

## Dataset and methodology

Content is oriented around **Irish State Examination** Agricultural Science material (past papers, marking schemes, and syllabus-style topics). Supporting scripts under `scripts/pdf-extraction/` help ingest and structure PDF sources for the project pipeline.

Development follows **iterative, Agile-style** delivery: model and prompt changes, export quality, and UX are refined based on testing and feedback.

---

## Disclaimer

This tool is for **revision and teaching support** only. It does not replace official SEC materials, circulars, or classroom instruction.
