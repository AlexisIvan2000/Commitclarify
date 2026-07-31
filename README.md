# CommitClarify

Automated analysis of GitHub repositories. CommitClarify fetches a repository's code, indexes it into a vector store, then runs four analysis agents that combine deterministic linters with an LLM to produce an exportable report.

The interface and the reports are available **in French and English**.

---

## Contents

- [What it analyzes](#what-it-analyzes)
- [Architecture](#architecture)
- [Tech stack](#tech-stack)
- [Setup](#setup)
- [Running the project](#running-the-project)
- [Tests and quality](#tests-and-quality)
- [API](#api)
- [How it works](#how-it-works)
- [Deployment](#deployment)
- [Known limitations](#known-limitations)

---

## What it analyzes

Four agents run in parallel against every repository:

| Agent | What it looks for | Method |
|---|---|---|
| **Secret detection** | API keys, tokens, passwords, private keys, committed sensitive files (`.env`, `id_rsa`, `*.pem`…) | Filename scan + regex + LLM |
| **.gitignore check** | Sensitive files not excluded from the repository | LLM over the actual `.gitignore` |
| **Code quality** | Unused imports, complexity, duplicated code, dead logic | Ruff + ESLint + LLM |
| **README vs Code** | Documented features that don't exist, wrong install instructions | Comparative LLM pass |

Findings from the linters and the filename scan are **deterministic**: they don't depend on the LLM and are therefore reproducible. The LLM only handles what static tooling cannot.

Every report can be read in the app and exported as **PDF** or **JSON**.

---

## Architecture

The repository holds two independent applications.

```
CommitClarify/
├── server/      FastAPI API
└── interface/   React SPA
```

### Backend — layered

```
server/
├── api/                 HTTP layer: routers, dependencies, middlewares
│   ├── routers/         auth · analysis · repos
│   ├── dependencies.py  current-user resolution
│   └── middlewares/     JWT
├── services/            Business logic
│   ├── ai/              agents, prompts, linters (ruff, eslint)
│   ├── analysis/        SSE pipeline, quotas
│   ├── authentication/  OAuth, tokens, account deletion
│   ├── export/          PDF, JSON serialization
│   ├── github/          file fetching
│   └── rag/             chunking, embeddings, Chroma indexing
├── repositories/        Database access (no SQL lives anywhere else)
├── models/
│   ├── db/              SQLAlchemy tables (user · token · analysis)
│   ├── schemas/         Pydantic contracts (auth · analysis)
│   └── data/            extensions.json
├── core/                Infrastructure: config, database, exceptions,
│                        clock, security, language, rate_limit, schema
├── migrations/          Alembic
└── tests/               unit/ · integration/
```

Dependencies flow one way: `api → services → repositories → models`, and `core` depends on nothing. **No SQL query lives outside `repositories/`**, and no service knows about HTTP — domain errors bubble up through an `AppError` hierarchy that a global handler turns into responses.

### Frontend — feature-first

```
interface/src/
├── core/                Shared across every feature
│   ├── network/         HTTP client, token storage, typed errors
│   ├── translation/     fr/en catalogs, provider, language detection
│   ├── components/      Navbar, Spinner, ErrorState, ErrorBoundary…
│   ├── pages/           404, legal pages
│   └── utils/           dates, downloads, shared hooks
└── features/
    ├── authentication/  data/ · domain/ · presentation/
    └── analysis/        data/ · domain/ · presentation/
```

Each feature follows the same split: `data/` (API calls), `domain/` (rules and normalization), `presentation/` (pages, components, providers). `core` never depends on a feature.

---

## Tech stack

**Backend**

| Area | Choice |
|---|---|
| API | FastAPI 0.135 · Uvicorn |
| Database | PostgreSQL · SQLAlchemy 2.0 (async, asyncpg) · Alembic |
| Vector store | ChromaDB 1.5 (persistent) |
| Embeddings | sentence-transformers `all-mpnet-base-v2` — runs **locally**, no third-party call |
| LLM | OpenAI `gpt-4o-mini` |
| Splitting | LangChain `RecursiveCharacterTextSplitter` |
| Linters | Ruff · ESLint 9 (run as subprocesses) |
| Export | ReportLab |
| Security | JWT (python-jose) · Fernet · SlowAPI |

**Frontend**

React 19 · Vite 7 · React Router 7 · lucide-react · highlight.js — no state-management or data-fetching library; the network layer is hand-rolled.

**Size**

| | Files | Lines |
|---|---|---|
| Backend (excluding tests) | 56 | 3,881 |
| Frontend | 59 | 2,768 |
| Tests | 19 | 1,468 |

---

## Setup

### Prerequisites

- Python 3.13
- Node.js 20+
- PostgreSQL (or SQLite for a quick local run)
- A [GitHub OAuth App](https://github.com/settings/developers)
- An OpenAI API key

### Backend

```bash
cd server
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # macOS / Linux

pip install -r requirements.txt
npm install                   # installs ESLint, used by the quality agent
cp .env.example .env
```

> `npm install` inside `server/` is not optional: without it the JavaScript analysis silently switches off — it logs an error and reports no issue at all.

Fill in `.env`:

| Variable | Required | Default | Purpose |
|---|:---:|---|---|
| `DB_URL` | ✅ | — | PostgreSQL URL (`postgresql://…`, converted to asyncpg) |
| `JWT_SECRET` | ✅ | — | Access-token signing |
| `GITHUB_CLIENT_ID` | ✅ | — | GitHub OAuth App |
| `GITHUB_CLIENT_SECRET` | ✅ | — | GitHub OAuth App |
| `GITHUB_CALLBACK_URL` | ✅ | — | Must match the OAuth App |
| `FERNET_KEY` | ✅ | — | Encrypts stored GitHub tokens |
| `OPENAI_API_KEY` | ✅ | — | LLM agents |
| `FRONTEND_URL` | ✅ | — | CORS origin and OAuth redirect target |
| `JWT_ALGORITHM` | | `HS256` | |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | | `30` | |
| `REFRESH_TOKEN_EXPIRE_DAYS` | | `30` | |
| `DAILY_ANALYSIS_LIMIT` | | `3` | Analyses per user per day |

The app refuses to boot if a required variable is missing, and tells you which ones.

Generate a Fernet key:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Frontend

```bash
cd interface
npm install
echo 'VITE_API_URL="http://localhost:8000"' > .env
```

---

## Running the project

```bash
# Terminal 1
cd server && uvicorn app:app --reload

# Terminal 2
cd interface && npm run dev
```

The interface listens on `http://localhost:5173`, the API on `http://localhost:8000`. Interactive docs at `/docs`.

The database schema is applied on startup: if the database already holds tables but no Alembic history, it is stamped at the baseline revision and then migrated — no manual command required.

---

## Tests and quality

```bash
cd server
pytest                   # 137 tests
pytest tests/unit        # 91 — no database, no HTTP
pytest tests/integration # 46 — HTTP client + in-memory SQLite
ruff check .
```

```bash
cd interface
npm run lint             # ESLint + translation parity check
npm run build
```

The unit tests run Ruff and ESLint **for real** against deliberately broken code — no mocks — so that a broken tool surfaces as a failure instead of being mistaken for "nothing found".

`npm run lint` also compares the `fr` and `en` catalogs key by key and fails on any drift.

---

## API

Every route requires `Authorization: Bearer <access_token>`, except `/`, `/health`, `/docs`, `/redoc`, `/openapi.json`, `/auth/github/login`, `/auth/callback` and `/auth/exchange`.

| Method | Route | Description |
|---|---|---|
| `GET` | `/` | Health check |
| `GET` | `/auth/github/login` | Redirects to GitHub, sets the `state` cookie |
| `GET` | `/auth/callback` | GitHub return, redirects with a single-use code |
| `POST` | `/auth/exchange` | Trades the code for tokens |
| `POST` | `/auth/refresh` | Rotates the token pair |
| `POST` | `/auth/logout` | Revokes the refresh token |
| `GET` | `/auth/me` | Current profile |
| `DELETE` | `/auth/account` | Deletes the account and every related record |
| `GET` | `/repos/` | The user's GitHub repositories |
| `POST` | `/analyze/{owner}/{repo}?language=fr\|en` | Creates an analysis, consumes one quota unit |
| `GET` | `/analyze/{id}/stream` | SSE progress stream |
| `GET` | `/analyze/{id}` | Full report |
| `DELETE` | `/analyze/{id}` | Deletes one analysis |
| `GET` | `/analyze/history` | History |
| `DELETE` | `/analyze/history/all` | Clears the history |
| `GET` | `/analyze/quota` | Today's quota |
| `GET` | `/analyze/{id}/export/pdf` | PDF export |
| `GET` | `/analyze/{id}/export/json` | JSON export |

Errors return `{"detail": "...", "code": "..."}`. The `code` is stable (`quota_exceeded`, `analysis_running`, `analysis_finished`…) so the client can translate the message instead of displaying the server's own wording.

---

## How it works

### Authentication

1. `/auth/github/login` generates a `state` nonce, stores it in an `HttpOnly` cookie and redirects to GitHub.
2. The callback rejects the request if the `state` doesn't match (double-submit CSRF protection).
3. Rather than returning JWTs in the URL, the server issues a **single-use code** (120 s lifetime, stored hashed) that the frontend exchanges for tokens through `POST /auth/exchange`.
4. The GitHub token is encrypted with Fernet before being stored.

### Analysis pipeline

`POST /analyze/{owner}/{repo}` consumes the quota and creates the analysis in `pending`. The SSE stream then drives it through:

```
fetching → indexing → analyzing → done
```

An analysis can only run if it is `pending`, or `processing` for more than 15 minutes (recovery after a dropped connection). Anything else returns `409` — which prevents replaying a finished analysis to bypass the quota.

### File filtering

Driven by `models/data/extensions.json`: 100 extensions across 7 groups, 87 explicit filenames, 62 excluded directories.

| Limit | Value |
|---|---|
| Max file size | 100 KB |
| Max lines per file | 2,000 |
| Max files per repository | 500 |
| Batch size | 20 |

### Vector indexing

Chunking adapts to the file type (code 1,500 characters, config 1,000, docs 800). Chroma collections are named after `user + repository + commit SHA`, so re-analyzing an unchanged repository reuses the existing index. Files are still re-downloaded every time, so that linters and regex scans produce the same results as a fresh run.

Embeddings are computed locally — no code is sent to a third-party embedding service. Only excerpts reach the OpenAI API, for the semantic pass.

### Report language

The language is chosen **at launch** and stored on the analysis, because a generated report is frozen: findings are persisted in the database as plain text. Switching the interface language therefore does not retranslate an existing report. Deterministic labels (linter rules, sensitive files) are translated server-side from a catalog, and every finding carries a stable rule identifier.

---

## Deployment

**Backend — Railway.** A `Procfile` (`uvicorn app:app --host 0.0.0.0 --port $PORT`) plus `nixpacks.toml`, which adds Node.js 20 and runs `npm install` so ESLint is available in production. Migrations run on startup.

**Frontend — Vercel.** `vercel.json` rewrites every route to `index.html` (required for client-side routing). Set `VITE_API_URL` to the API URL.

After deploying the frontend, make sure the backend is up to date: FastAPI silently ignores unknown query parameters, which can make a feature look broken when in fact only the API is lagging behind.

---

## Known limitations

- Tokens are kept in `localStorage`, so they are exposed to XSS. Moving to `HttpOnly` cookies would require server-side changes.
- Refreshing the page during an analysis starts a new one and consumes another quota unit; the previous one stays in `processing` until the recovery delay expires.
- A failed analysis still consumes a quota unit, with no refund.
- The metadata in `index.html` (description, Open Graph) stays in French: it is served before React boots.
