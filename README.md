# CommitClarify

A developer connects their GitHub account, picks a repository, and within a minute gets a
report telling them what is actually exposed or neglected in their code: secrets committed
to history, files that should have been ignored, quality debt, documentation that no longer
matches the code.

It is not a full security audit. It answers one question: **did I leave something
compromising in this repository, and what should I fix first?**

The interface and the reports are available in French and English.

**See a sample report** at `/demo`, without connecting an account. It is a real scan of the
public `facebook/react` repository.

---

## Contents

- [How it works](#how-it-works)
- [What it looks for](#what-it-looks-for)
- [Honest reporting](#honest-reporting)
- [The backend in short](#the-backend-in-short)
- [The frontend in short](#the-frontend-in-short)
- [Tech stack](#tech-stack)
- [Setup](#setup)
- [Limits](#limits)

---

## How it works

The product does two distinct things, in this order, and the distinction matters.

**1. The scan.** Deterministic, free, no LLM involved. It fetches the repository files and
applies fixed rules across four axes. Same repository at the same commit, same result. This
is the product; most users never go further.

**2. The AI triage.** Optional, a few per day. The model re-reads the detections the scan
already made, dismisses the ones that are not real risks, explains the rest. On the two
closed axes it cannot add a detection of its own, only judge existing ones.

A report without AI triage is the normal, finished state. Nothing in the interface treats
it as an unfinished step.

The scan is carried by the server, not by the browser tab. Closing the page, navigating
away or reloading does not stop it, and coming back reattaches to the run in progress.

---

## What it looks for

| Axis | What it looks for |
|---|---|
| **Secret detection** | API keys, tokens, private keys, connection strings in versioned files |
| **.gitignore check** | Files tracked by Git that should not be, and missing rules |
| **Code quality** | Linter findings, over complex functions, missing lockfile, CI or tests |
| **README vs Code** | Environment variables the code reads but that are documented nowhere |

Findings carry one of five severities, from critical to information, and a real world
nuance the tool insists on: a secret found in a test file keeps its severity and stays in
the list, but is badged as a test file. On the reference scan, all six secret detections
are test fixtures. Hiding that would make the report either alarmist or dishonest.

Reports export to PDF and JSON.

---

## Honest reporting

Three product rules that shape most of the interface.

**Partial coverage is read per axis, never globally.** Large repositories are not fully
read: the scan caps at 500 files. When that happens an axis says "nothing on the analyzed
part" instead of "nothing to report", and the difference carries the credibility of the
whole product. On `facebook/react`, the secrets axis says exactly that while the .gitignore
axis reports two critical findings, in the same report.

**Coverage figures name what was skipped, and why.** Not a percentage. Of the 7199 files
tracked in that repository, 4394 were out of scope by construction (excluded paths, binary
extensions, oversized files) and 2309 were analyzable but went unread because the scan stops
at 500. Only the second number is a blind spot, and it is the product's limit, not the
repository's.

**Nothing the AI dismisses is deleted.** Dismissed detections move into a collapsed group,
keep their original severity next to the demoted one, and stay readable with the reason. The
user has to be able to disagree with the model.

---

## The backend in short

FastAPI, PostgreSQL, deployed on Railway. Full detail in [`server/README.md`](server/README.md).

**Authentication** is GitHub OAuth with a state cookie against CSRF, then a short lived
single use auth code so no token ever travels in a URL. Access tokens are JWTs, refresh
tokens are stored only as hashes, and the user's GitHub token is encrypted with Fernet and
decrypted only when a scan needs it.

**The database** holds users, their refresh tokens and auth codes, their analyses and one
result row per axis. Two tables stand apart: a scan cache keyed by repository, commit, rule
version and language, shared across users, and a quota ledger with reserved and committed
states, so a crashed AI run releases its slot instead of consuming it.

**A scan is not an HTTP response.** It runs as a background task that publishes events into
a buffer, and the server sent events endpoint is only a subscriber that replays and follows.
That is why disconnecting does not kill it and reconnecting catches up.

**Two limits.** A technical throttle nobody should ever hit, protecting CPU, bandwidth and
the user's own GitHub rate limit, where a cache hit costs nothing. And a product quota of a
few AI triages per day.

377 tests, unit and integration.

---

## The frontend in short

React 19, Vite, no state management or data fetching library. Full detail in
[`interface/README.md`](interface/README.md).

**Following an analysis lives above the pages**, in a provider mounted in the shell. That
one decision is what makes navigation, reload, concurrency blocking, the completion notice
and the slow warning all work, instead of five separate features.

**Detections are grouped by rule and file**, which takes the busiest axis from 21 entries to
12, and low severity ones fold into a chip that still shows how many are behind it. The
mechanism only activates on the axis that needs it; the other three render identically with
or without it.

**Error messages are localized by code, never by text.** The server answers in English with
a stable code and parameters, and the interface resolves it against its catalogs. A build
check fails when a key exists in one language and not the other.

The report component is shared by the report page, the live scan and the public demo, so the
demo cannot drift from the product.

---

## Tech stack

**Backend**

| Area | Choice |
|---|---|
| API | FastAPI, Uvicorn |
| Database | PostgreSQL, SQLAlchemy 2.0 async with asyncpg, Alembic |
| Vector store | ChromaDB, persistent |
| Embeddings | sentence-transformers `all-MiniLM-L6-v2`, runs locally, no third party call |
| LLM | OpenAI `gpt-4o-mini` |
| Splitting | LangChain `RecursiveCharacterTextSplitter` |
| Linters | Ruff and ESLint 9, run as subprocesses |
| Export | ReportLab |
| Security | JWT, Fernet, SlowAPI per IP on the auth and repository routes, a per user scan throttle |

**Frontend**

React 19, Vite 7, React Router 7, iconsax-react, highlight.js. The network layer is hand
rolled.

---

## Setup

### Prerequisites

- Python 3.13
- Node.js 20 or later
- PostgreSQL
- A [GitHub OAuth App](https://github.com/settings/developers)
- An OpenAI API key

### Backend

```bash
cd server
python -m venv .venv
.venv/Scripts/activate        # Windows
source .venv/bin/activate     # macOS, Linux

pip install -r requirements.txt
npm install                   # ESLint, used by the quality scan
cp .env.example .env          # then fill it in

alembic upgrade head
uvicorn app:app --reload
```

The service refuses to start when a required setting is missing, listing all of them at
once rather than failing on the first use. Every variable is documented in
[`server/README.md`](server/README.md).

### Frontend

```bash
cd interface
npm install
npm run dev
```

### Checks

```bash
cd server && pytest           # 377 tests
cd interface && npm run lint  # ESLint, translation parity, demo render check
```

---

## Limits

Worth knowing before relying on it.

**500 files per repository.** Beyond that the scan reads a subset and says so. It never
pretends to have read everything.

**One worker.** The live run registry lives in memory, and it alone carries stream resume,
the one concurrent run per user limit, and orphan detection. All three break silently under
several workers. Scaling out means moving that registry into a shared Redis.

**The AI triage is bounded by design.** On the two closed axes the model can only judge
existing detections, never invent one. On the two open axes, findings pointing at files that
do not exist are rejected before they reach the report.

**Embeddings run on CPU.** Indexing a large repository takes tens of seconds. The model
choice is deliberate: a heavier one measured seventeen times slower, for a retrieval quality
difference that does not show given only fifteen fragments are read per query. A feature
that takes twelve minutes is not used, so its theoretical quality is worth nothing.

**Source code is never stored.** It is fetched into memory for the duration of a scan. What
persists is the report and, for the AI phase, a vector index tied to the commit.

**It is not a security audit.** No dependency CVE scanning, no dynamic analysis, no secret
rotation. It answers one narrow question, and tries to answer it honestly.
