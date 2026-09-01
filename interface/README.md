# CommitClarify, interface

React front end for CommitClarify. A developer connects their GitHub account, picks a
repository, and gets a report on what is exposed or neglected in their code: committed
secrets, files that should have been ignored, quality debt, documentation drift.

The report screen is the product. The AI triage is an option offered once the report is
read, not a step the user is walked toward.

---

## Running it

```bash
npm install
npm run dev        # http://localhost:5173
npm run lint       # ESLint, translation parity, demo render check
npm run build      # production build
npm run preview    # serve the build
```

The API is expected at `http://localhost:8000`, overridable with `VITE_API_URL`.

`npm run lint` is three checks in one, and the last two are the ones that catch real
regressions:

- **ESLint** with the React Hooks v7 rules.
- **`scripts/check-translations.mjs`** compares the French and English catalogs key by key.
  Adding a key to one and forgetting the other fails the build.
- **`scripts/check-demo.mjs`** compiles the demo fixture through the real report component
  and renders it server side, asserting 17 properties. If the finding format changes, the
  demo breaks here rather than in production.

---

## Layout

```
src/
├── main.jsx                 entry point, StrictMode
├── App.jsx                  routes, providers, session gate
├── AppShell.jsx             the authenticated layout: sidebar, outlet, run notice
├── index.css                base layer, imports the design tokens
├── App.css                  every component style, one flat sheet
├── core/                    shared by every feature, never depends on one
│   ├── network/
│   │   ├── apiClient.js       fetch wrapper, bearer token, transparent refresh, SSE reader
│   │   ├── errors.js          ApiError and NetworkError, code to message resolution
│   │   └── tokenStorage.js    access and refresh tokens
│   ├── translation/
│   │   ├── fr.js, en.js       the two catalogs, ~297 keys each
│   │   ├── index.js           active language, detection, persistence
│   │   ├── LanguageProvider.jsx
│   │   └── useTranslation.js
│   ├── design/
│   │   ├── tokens.css         colors, type, motion, elevation, sidebar
│   │   └── icons.jsx          semantic icon map over iconsax
│   ├── components/          Sidebar, Spinner, EmptyState, ErrorState, PageHeader,
│   │                        ErrorBoundary, CodeHighlight, LanguageSwitch, HomeNavbar
│   ├── pages/               404 and the legal pages
│   └── utils/               dates and relative time, downloads
└── features/
    ├── authentication/      OAuth callback, session, account
    ├── repositories/        the repository list, filters, last scan verdict
    ├── scan/                starting and following analyses, quota, run provider
    ├── report/              the report, its exports, the AI deepening, the demo
    └── history/             past analyses
```

Each feature keeps the same split:

- **`data/`** talks to the API and nothing else.
- **`domain/`** holds the rules and the normalization. Pure functions, no React, which is
  what makes them testable without a renderer.
- **`presentation/`** holds pages, components and providers.

`core` never imports a feature. The **`scan` feature owns the analysis vocabulary** and
the others import it: severities, verdicts, statuses, steps, coverage, the stream reducer.
That is why `report/` imports `@features/scan/domain/issue` rather than keeping its own
copy.

---

## Routing

```
public                          authenticated (inside SessionGate + AppShell)
/                landing        /dashboard      repositories
/demo            sample report  /scan           live scan follow
/auth/callback   OAuth return   /report         redirects to the latest viewable report
/privacy                        /report/:id     one report
/terms                          /history        past analyses
                                /account        profile, preferences, danger zone
```

`/analyze/:owner/:repo` and `/analysis/:id` are kept as redirects so old bookmarks still
resolve.

---

## Two things that are not obvious from the file tree

### Following an analysis lives above the pages

`RunsProvider` is mounted in `AppShell`, above the router outlet. A page never starts an
analysis itself; it asks the provider. That single relocation is what makes five separate
behaviours work:

- Leaving the scan page does not stop the analysis, and coming back attaches to it instead
  of starting a second one.
- A page reload finds the run again through `GET /analyze/active`, then reattaches. A
  `ready` flag holds the scan page back until that check resolves, otherwise it would race
  and start a duplicate.
- A run already in flight blocks starting another, in the interface rather than as a 429
  from the API.
- Success and failure surface as a discreet notice, fixed bottom right, `role="status"`
  and `aria-live="polite"` so it never steals focus. It carries a link to the report and
  survives navigation, because the point is that the user was somewhere else.
- A timer flips a `slow` flag past a measured threshold, 60 seconds for a scan and 120 for
  an AI analysis, and the page then says the wait will be longer and that leaving is safe.

`followRun` handles the connection itself. If the stream drops without a verdict it asks
the server for the analysis state; terminal means adopt the result, still running means
reconnect with backoff of 1, 2, 4, 8 and 15 seconds. The budget resets whenever new events
arrive, and a 403 or 429 is fatal rather than retried.

### Error messages are localized by code, never by text

The server answers in English with a stable `code` and optional `params`. The front looks
up `apiErrors[code]` in the active catalog and interpolates: `scan_throttled` receives
`{seconds}`, `quota_exceeded` receives `{limit}`. The English detail from the server is
only a last resort fallback.

Adding a code on the server therefore means adding its entry to both catalogs, and
`npm run lint` fails until you do.

---

## The report

The report is one component, `AnalysisReport`, used by the report page, the live scan page
and the public demo. A divergence between the demo and the real product would be worse
than no demo, so there is no second copy.

**Detections are grouped by rule and file**, never by rule alone. On a real scan that takes
the quality axis from 21 raw detections to 12 entries, and the whole report from 29 to 20.
Grouping by rule alone would merge the same lint rule across three different files into one
entry that no longer says where, which makes it unactionable.

**Severity hierarchy folds what does not deserve attention.** Critical, high and medium stay
in the main list. Low and information collapse into one chip per severity, showing both the
entry count and the detection count, so a folded chip still says how much is behind it.
Nothing is ever hidden, only summarized.

The mechanism only activates where it earns its place. On the reference scan, three axes out
of four render identically with and without it; only the quality axis, which carries most
of the volume, actually folds.

**AI verdicts are a separate mechanism.** Dismissed detections move into their own collapsed
bucket, keep their original severity next to the demoted one, and stay readable. The user
has to be able to disagree with the model.

---

## Design system

`core/design/tokens.css` is the single source of truth: paper and surface grounds, ink
scale, one slate blue accent, five semantic severity colors that are deliberately not the
accent, IBM Plex Sans and Mono, radii, and the sidebar geometry.

**Motion is tokenized too.** Four easing curves and five named durations, instead of the
durations that used to be scattered across the sheet. A single `prefers-reduced-motion`
block neutralizes transitions and animations, keeping the loading spinner running but
slowed, because it reports state rather than decorating.

Two choreographed moments, one per screen: the active step breathes in a pulsing ring while
scanning, and the four axes rise in sequence when a report opens. Everything else is hover
and press feedback.

**Icons go through `core/design/icons.jsx`**, never imported from iconsax directly. The
`themed()` wrapper there exists for a concrete reason: React 19 removed `defaultProps` for
function components, including `forwardRef` ones, so iconsax's own `color: currentColor`
default stopped applying and every path rendered with no stroke at all. The wrapper injects
the defaults for the whole library in one place.

---

## The demo

`/demo` shows a real report without an account, because asking for OAuth access to private
repositories before showing anything is the main friction at sign up.

It is a frozen report, not a simulated scan. No authentication, no writes, no GitHub or
OpenAI call. The data is the real scan of `facebook/react`: a public repository, two
committed `.env` files as critical findings, and partial coverage with 2309 files left
unread, which shows the product's limits honestly.

`scripts/build-demo-fixture.mjs` generates the fixture from `server/scan_react.json`,
pruning repeated evidence and verbose locations, and produces two variants: the raw scan
and the AI sorted one. It is imported dynamically, so it ships as its own content hashed
chunk of about 3 kB gzipped and never weighs on the landing page.

The banner says it is a demonstration and keeps the GitHub button within reach. In sorted
mode it also says the verdicts are illustrative: the detections are real, the AI sentences
were written by hand.

---

## Verification

There is no test runner in this project. What exists instead:

- ESLint, translation parity and the demo render check, all three wired into `npm run lint`.
- Domain logic extracted into pure functions precisely so it can be checked without a
  renderer: grouping, folding, the last scan join, the start decision, the coverage split.
- Server side rendering harnesses used during development to render real components against
  real fixtures.

Screens are not covered by automated visual testing. The demo render check is the closest
thing, and it exists because the report format is the part most likely to drift.
