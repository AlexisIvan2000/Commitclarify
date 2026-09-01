# CommitClarify, backend

FastAPI service that scans GitHub repositories for committed secrets, `.gitignore`
mistakes, code quality debt and documentation drift, then optionally lets an LLM triage
the findings it already produced.

The service does two distinct things, in this order:

1. **Scan.** Deterministic, free, no LLM. Fixed rules over the repository files.
2. **AI triage.** Optional, quota limited. The LLM re-reads the detections the scan made,
   dismisses the ones that are not real risks and explains the rest. It never adds a
   detection of its own on the closed axes.

---

## Running it

```bash
python -m venv .venv
.venv/Scripts/activate          # Windows
source .venv/bin/activate       # Linux, macOS

pip install -r requirements.txt
npm install                     # ESLint, used as a subprocess by the quality scan

uvicorn app:app --reload
```

The service refuses to start when a required setting is missing, listing every one of
them at once rather than failing on the first use.

### Settings

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `JWT_SECRET` | yes | | Signs access tokens |
| `JWT_ALGORITHM` | no | `HS256` | Access token algorithm |
| `GITHUB_CLIENT_ID` | yes | | OAuth application |
| `GITHUB_CLIENT_SECRET` | yes | | OAuth application |
| `GITHUB_CALLBACK_URL` | yes | | OAuth redirect target |
| `FERNET_KEY` | yes | | Encrypts the stored GitHub token |
| `OPENAI_API_KEY` | yes | | AI triage |
| `FRONTEND_URL` | yes | | CORS origin and post login redirect |
| `DB_URL` | yes | | PostgreSQL, `postgresql://` is rewritten to asyncpg |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | no | `30` | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | no | `30` | Refresh token lifetime |
| `DAILY_ANALYSIS_LIMIT` | no | `3` | AI triages per user per day |
| `SCAN_RATE_PER_MINUTE` | no | `4` | Technical scan throttle |
| `SCAN_RATE_PER_HOUR` | no | `20` | Technical scan throttle |
| `EMBEDDING_MODEL` | no | `all-MiniLM-L6-v2` | Sentence transformer used for the vector index |
| `CHROMA_PATH` | no | `./chroma_db` | Where the vector index lives, point it at a volume in production |

`COOKIE_SECURE` is derived, not configured: it turns on when `GITHUB_CALLBACK_URL` uses
HTTPS.

---

## Authentication

The flow avoids putting tokens in a URL, which would leak them into browser history,
server logs and `Referer` headers. It uses a short lived single use code instead.

```
Browser                     Backend                        GitHub
   |                           |                              |
   |  GET /auth/github/login   |                              |
   |-------------------------->|                              |
   |                           |  sets cc_oauth_state cookie  |
   |<--- 307 to GitHub --------|                              |
   |                                                          |
   |  the user authorizes the OAuth app                        |
   |--------------------------------------------------------->|
   |                                                          |
   |  GET /auth/callback?code&state                            |
   |-------------------------->|                              |
   |                           |  state cookie must match     |
   |                           |  exchange code for a token   |
   |                           |----------------------------->|
   |                           |  read the GitHub profile     |
   |                           |<-----------------------------|
   |                           |  upsert the user             |
   |                           |  encrypt the GitHub token    |
   |                           |  mint access + refresh       |
   |                           |  store them behind auth_code |
   |<-- 307 /auth/callback?code|                              |
   |                           |                              |
   |  POST /auth/exchange      |                              |
   |-------------------------->|  auth_code is consumed once  |
   |<-- access + refresh ------|                              |
```

**CSRF protection.** `/auth/github/login` generates a random `state`, stores it in an
`HttpOnly` cookie scoped to `/auth`, and sends it to GitHub. The callback refuses any
request whose `state` does not match the cookie, then deletes the cookie.

**The GitHub token is never stored in clear text.** It is encrypted with Fernet
(`FERNET_KEY`) in `users.access_token` and decrypted only at the moment a scan needs it.
Rotating `FERNET_KEY` makes every stored token unreadable, which the code logs explicitly
rather than failing silently.

**Access tokens** are JWTs signed with `JWT_SECRET`, carrying the user id in `sub`, valid
for 30 minutes. They are verified on every protected route by `get_current_user`.

**Refresh tokens** are random strings; only their SHA-256 hash is stored, so a database
dump does not hand out sessions. They are checked against expiry and revocation.
`/auth/logout` revokes the presented one.

**Auth codes** are the bridge between the OAuth redirect and the frontend. They are
hashed like refresh tokens, live for a very short time, hold the freshly minted token
pair, and are marked used the first time they are exchanged.

**Rate limiting on the auth surface** is per IP, via SlowAPI decorators: 10 requests per
minute on login, callback, exchange, refresh and logout, 30 per minute on the repository
listing. These decorators work without the SlowAPI middleware, which is why no middleware
is registered. There is no global default limit; `tests/integration/test_ip_rate_limit.py`
pins that fact so nobody mistakes the configuration for a blanket protection.

### Endpoints

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `GET` | `/auth/github/login` | no | Start the OAuth dance |
| `GET` | `/auth/callback` | no | GitHub returns here, redirects to the frontend with an auth code |
| `POST` | `/auth/exchange` | no | Trade the auth code for a token pair |
| `POST` | `/auth/refresh` | no | Trade a refresh token for a new pair |
| `POST` | `/auth/logout` | yes | Revoke the presented refresh token |
| `GET` | `/auth/me` | yes | Current profile |
| `DELETE` | `/auth/account` | yes | Delete the account, its analyses and its vector collections |
| `GET` | `/repos/` | yes | The user's GitHub repositories |
| `GET` | `/repos/{owner}/{repo}/scan` | yes | Repository metadata used before a scan |
| `POST` | `/analyze/{owner}/{repo}` | yes | Create a pending analysis |
| `GET` | `/analyze/{id}/stream` | yes | Server sent events for the scan phase |
| `GET` | `/analyze/{id}/deepen/stream` | yes | Server sent events for the AI phase |
| `GET` | `/analyze/active` | yes | The run currently in flight for this user, or null |
| `GET` | `/analyze/{id}` | yes | One analysis with its results |
| `GET` | `/analyze/history` | yes | Every analysis of the user |
| `DELETE` | `/analyze/{id}` | yes | Delete one analysis |
| `DELETE` | `/analyze/history/all` | yes | Delete every analysis |
| `GET` | `/analyze/quota` | yes | AI triages used and remaining today |
| `GET` | `/analyze/{id}/export/json` | yes | Report as JSON |
| `GET` | `/analyze/{id}/export/pdf` | yes | Report as PDF |

---

## Database

PostgreSQL through SQLAlchemy 2.0 async with asyncpg. Alembic owns the schema; the
application calls `upgrade_schema()` on startup so a deployment never runs against an
older shape.

```
                users
                  |  id (uuid, pk)
                  |  github_id (unique)
                  |  login, username, avatar_url, email
                  |  access_token   <- GitHub token, Fernet encrypted
                  |  created_at, updated_at
                  |
      +-----------+-----------+----------------------+
      |           |           |                      |
refresh_tokens  auth_codes  analyses            (analysis_log
      |           |           |                   is keyed by
 token_hash   code_hash    repo_name              github_id,
 expires_at   access_token repo_id, repo_sha      not a foreign
 revoked_at   refresh_token status                key)
              expires_at   language
              used_at      scan_version
                           config_hash
                           coverage (json)
                           created_at
                           phase_started_at
                           completed_at
                                |
                                | one row per axis
                                v
                        analysis_results
                          aspect
                          status
                          issues (json)
                          recommendations (json)
                          metrics (json)
```

Two tables stand apart because they are caches or ledgers rather than user data:

**`scan_cache`** stores a whole scan payload keyed by
`(repo_id, commit_sha, scan_version, config_hash, language)`. Two users scanning the same
commit of the same repository with the same rules share the result, and a cache hit costs
nothing against the technical throttle. Bumping `SCAN_VERSION` or changing the rule
configuration changes the key, so stale results are never served.

**`analysis_log`** is the AI quota ledger. One row per triage, `analysis_id` unique, with a
state of `reserved` or `committed`. A reservation is taken before the AI phase starts and
either committed on success or released on failure. A background sweeper reclaims
reservations that outlived their TTL, which is how a crashed run stops holding a slot.

### Migrations

| Revision | What it adds |
|---|---|
| `0001_baseline` | users, refresh_tokens, auth_codes, analyses, analysis_results |
| `0002_analysis_language` | report language on an analysis |
| `0003_scan_phase` | scan phase columns and the scan cache |
| `0004_quota_reservations` | the reserved and committed states on the quota ledger |
| `0005_report_provenance` | scan version, config hash and coverage on an analysis |

```bash
alembic revision --autogenerate -m "what changed"
alembic upgrade head
```

---

## Layout

```
server/
├── app.py                  FastAPI application, lifespan, middleware, routers
├── api/
│   ├── routers/            HTTP surface, one module per domain
│   │   ├── auth.py           OAuth, tokens, profile, account deletion
│   │   ├── repos.py          GitHub repository listing
│   │   └── analysis.py       scans, streams, history, quota, exports
│   ├── dependencies.py     resolves the current user from the bearer token
│   └── middlewares/        JWT plumbing
├── services/               business logic, no HTTP, no SQL
│   ├── analysis/
│   │   ├── pipeline.py       the two phases, as async generators of events
│   │   ├── runs.py           in memory registry of live runs, see the warning below
│   │   ├── throttle.py       technical scan rate limit, invisible to the product
│   │   └── quota.py          AI triage quota, reserve, commit, release
│   ├── scan/               the deterministic rules, one module per axis
│   │   ├── secrets.py        API keys, tokens, private keys, connection strings
│   │   ├── gitignore.py      tracked files that should be ignored
│   │   ├── quality.py        linters, complexity, lockfiles, CI, tests
│   │   ├── documentation.py  environment variables read but never documented
│   │   ├── runner.py         runs the four axes and assembles the verdict
│   │   ├── report.py         findings, severities, SCAN_VERSION
│   │   └── config.py         the hash that invalidates the scan cache
│   ├── ai/                 the LLM side
│   │   ├── triage.py         verdicts on existing detections, closed list
│   │   ├── consistency_agent.py  quality and README agents
│   │   ├── validation.py     rejects invented paths, applies verdicts
│   │   ├── prompts.py        every prompt, in one place
│   │   └── linters/          ruff and ESLint, run as subprocesses
│   ├── rag/                retrieval for the AI phase
│   │   ├── chunker.py        splits files by type
│   │   ├── embeddings.py     sentence transformer, runs locally
│   │   ├── selection.py      caps the indexed corpus, source before generated
│   │   └── indexer.py        Chroma collections, keyed by model and commit
│   ├── github/             repository fetching and coverage accounting
│   ├── authentication/     OAuth, tokens, account deletion
│   └── export/             PDF and JSON serialization
├── repositories/           every SQL query in the project lives here
├── models/
│   ├── db/                 SQLAlchemy tables
│   ├── schemas/            Pydantic contracts
│   └── data/               extensions.json, the file rules and limits
├── core/                   infrastructure with no domain knowledge
│   ├── config.py             settings and their defaults
│   ├── database.py           engine and session factory
│   ├── exceptions.py         AppError hierarchy, turned into responses centrally
│   ├── language.py           fr and en message catalogs for the streams
│   ├── file_rules.py         allowed extensions, size and count limits
│   ├── rate_limit.py         the per IP limiter
│   ├── maintenance.py        background sweeper
│   ├── security.py           hashing and token generation
│   └── clock.py              one source of time, so tests can reason about it
├── migrations/             Alembic
├── scripts/                scan_repo.py, runs a scan from the command line
└── tests/                  unit and integration
```

Dependencies flow one way: `api -> services -> repositories -> models`, and `core` depends
on nothing. **No SQL lives outside `repositories/`**, and no service knows about HTTP.
Domain errors bubble up as `AppError` subclasses and a single handler turns them into
responses carrying a stable `code`, optional `params` and, for rate limits, `Retry-After`.

> **The service runs on a single worker.** `services/analysis/runs.py` keeps the live run
> registry in memory, and that registry alone carries three guarantees: resuming a stream
> after a disconnect, the one concurrent run per user limit, and orphan detection. All
> three break silently under several workers. Moving past one worker means moving the
> registry into a shared Redis, pub/sub for the stream and TTL keys for concurrency.

---

## How a scan runs

The work is **not** the HTTP response. A run is an `asyncio.Task` owned by the
application, with its own database session, publishing events into a buffer. The SSE
endpoint is a subscriber: it replays everything already emitted, then follows.

That distinction is the whole design. A client that disconnects only removes a subscriber;
the scan keeps going. A client that reconnects gets the full replay and catches up. A
heartbeat every 15 seconds keeps intermediaries from cutting an idle connection during a
long phase.

```
POST /analyze/owner/repo        creates a pending analysis
GET  /analyze/{id}/stream       starts the run if none is live, otherwise attaches
                                emits: progress, step_complete, done or error, ping
GET  /analyze/active            what is in flight for this user, used after a reload
```

The scan phase fetches the repository (capped at 500 files, 100 kB and 2000 lines each),
consults the scan cache, runs the four axes, persists the results and reports coverage.
CPU bound axes run in threads so the event loop stays responsive.

The AI phase re-fetches the repository pinned to the scan's commit, chunks it, caps the
corpus, indexes it into Chroma with a progress counter, then runs four agents in parallel.
Two of them triage existing detections against a closed list; two discover new ones on the
open axes, with invented file paths rejected.

### Two limits worth knowing

**Technical throttle** (`throttle.py`), invisible to the product, protects CPU, bandwidth
and the user's own GitHub rate limit: a few scans per minute, a wider hourly ceiling, and
at most one concurrent run per user. A cache hit refunds its slot. Refusals carry
`Retry-After` and say when to try again.

**AI quota** (`quota.py`) is a product limit: `DAILY_ANALYSIS_LIMIT` triages per day,
reserved before the run and committed on success.

---

## Tests

```bash
pytest                       # 377 tests
pytest tests/unit            # rules, parsers, agents, no database
pytest tests/integration     # HTTP surface and pipeline, SQLite in memory
```

Integration tests run against SQLite in memory with UUID columns adapted at import time,
and override the database dependency, so they never touch a real database. An autouse
fixture clears the run registry and the throttle counters between tests, since both are
process global.

A few tests deserve a mention because they encode a decision rather than a behaviour:

- `test_scan_version.py` hashes every module that can change a scan result and fails when
  one of them changes. It forces a conscious choice: bump `SCAN_VERSION` if the output can
  differ, otherwise record the new digest. Without it, cached scans would be served stale.
- `test_gitignore_matches_git.py` checks the gitignore rules against real `git` behaviour
  rather than against our own understanding of it.
- `test_ip_rate_limit.py` pins that the SlowAPI decorators are enforced and that an
  undecorated route is not, so nobody reads the configuration as a global guarantee.
- `test_scan_resume.py` covers the part that is easy to break: reconnecting replays the
  whole run, a second reader attaches instead of launching a second scan, and a live run is
  findable again after a page reload.
- `test_indexer.py` covers the collection key, including that a long repository name never
  truncates the commit hash away, which would make two commits share one index.

The `ruff` and `ESLint` tests need those tools on the PATH of the subprocess. They fail
outside the virtual environment, which is a local environment problem rather than a
product one.

---

## Deployment

Railway, `Procfile`, `uvicorn app:app --host 0.0.0.0 --port $PORT`, root directory
`/server`. A volume is mounted at `/data/models`; `SENTENCE_TRANSFORMERS_HOME` points there
so the embedding model survives a redeploy, and `CHROMA_PATH` should point inside the same
volume so the vector index does too. Without that, the index is wiped on every deployment
and every analysis re-indexes from scratch.
