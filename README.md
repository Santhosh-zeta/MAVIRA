# MAVIRA — Meridian AI Vendor Intelligence & Risk Assessment

Private, local-first workbench for **Case Study 1: Vendor AI Usage Analysis** (Meridian Financial).
It ingests Meridian's vendor inventory workbook, derives vendor criticality, sets OSINT depth from that
criticality, collects public evidence, determines whether each vendor genuinely uses AI in the service it
provides, identifies named model providers, scores the resulting AI security risk, routes the result through
analyst review, and writes the findings back into the original Excel structure.

> **Confidentiality.** The vendors are real organisations. Keep this repository and its outputs private: no
> public repository, no published presentation, no contact with vendors. The platform makes no contact with
> vendors; in LIVE mode it only reads public web pages.

---

## Contents

- [What it does](#what-it-does) · [Results on the supplied inventory](#results-on-the-supplied-inventory)
- [Architecture](#architecture) · [Tech stack](#tech-stack)
- [How to run the application](#how-to-run-the-application)
- [Environment variables](#environment-variables) · [Database](#database)
- [Demo mode vs live OSINT](#demo-mode-vs-live-osint) · [LLM (optional)](#llm-optional)
- [Excel import and export](#excel-import-and-export) · [Tests](#tests)
- [Methodology](#methodology) · [Security](#security-considerations) · [Privacy / data egress](#privacy-and-data-egress)
- [Limitations and assumptions](#limitations-and-known-assumptions)

Design documents: [`docs/FUNCTIONAL_DESIGN.md`](docs/FUNCTIONAL_DESIGN.md),
[`docs/TECHNICAL_ARCHITECTURE.md`](docs/TECHNICAL_ARCHITECTURE.md),
[`docs/SOURCE_STRATEGY.md`](docs/SOURCE_STRATEGY.md), [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md).

---

## What it does

```
Upload workbook → validate → parse vendors → criticality → assessment depth → search strategy
→ collect sources → extract/normalise → AI signal detection → exact-excerpt validation
→ AI usage (YES / NO / INCONCLUSIVE) → providers → AI security risk → recommendations
→ analyst review (approve / override / reassess) → export completed workbook
```

| Capability | Where |
|---|---|
| Deterministic, configurable criticality (5 factors + escalation rules) | `backend/app/services/criticality/`, `backend/app/config/methodology.yaml` |
| Criticality-driven depth tiers and query plans | `backend/app/services/depth/` |
| Provider-agnostic OSINT (Tavily, Serper, Brave, cached snapshot, fixtures) | `backend/app/services/osint/providers.py` |
| SSRF-safe, robots-aware fetcher with ETag caching | `backend/app/services/extraction/fetcher.py` |
| Evidence proposal (rule-based default, LiteLLM optional) | `backend/app/services/ai/` |
| Exact-excerpt validation (no invented quotes) | `backend/app/services/evidence/validator.py` |
| Evidence strength (separate from classification confidence) | `backend/app/services/evidence/strength.py` |
| Deterministic risk engine (9 categories, unknowns labelled) | `backend/app/services/risk/engine.py` |
| Rule-grounded recommendations | `backend/app/services/recommendations/engine.py` |
| Append-only analyst review + audit trail | `backend/app/services/review/`, `audit_events` table |
| Excel write-back preserving the original workbook | `backend/app/services/export/excel_writer.py` |
| Enterprise UI: register, import, live run, vendor detail, evidence explorer, risk, review, methodology, audit | `frontend/app/` |

## Results on the supplied inventory

Run against the six real vendors using the cached OSINT snapshot (captured 2026-10-06, see
[Demo mode](#demo-mode-vs-live-osint)). Methodology `1.0.0`.

| ID | Vendor | Criticality | AI usage (confidence) | Risk | Basis in one line |
|---|---|---|---|---|---|
| V-001 | AutomWorx | High (escalated from Medium: privileged production access) | Inconclusive (73%) | Medium | AI sits in the Automic platform it implements ("bring your own LLM"); its own use in service delivery is not stated |
| V-002 | Fiserv | Critical (0.99) | **Yes** (76%) | High | Investor release: AI "already powers fraud detection, risk management…"; Microsoft Foundry/Copilot named at enterprise level; DNA-specific use not stated |
| V-003 | FSSI | High (0.72) | Inconclusive (73%) | Low | One 2017 marketing article ("we can tap into… customer data") — capability claim, not deployment |
| V-004 | Terrapin | Medium (0.52) | Inconclusive (73%) | Low | Thought leadership on "AI-ready data"; no statement of AI in its platform |
| V-005 | BNY | Critical (0.81) | **Yes** (89%) | High | "AI-based anomaly detection in its own Payment Validation solution"; OpenAI and NVIDIA named enterprise-wide; RTP-specific use not stated |
| V-006 | The Clearing House | Critical (0.86) | Inconclusive (83%) | None identified | No public statement of AI in RTP/ACH operations; only AML advocacy. Questionnaire recommended |

`sample_data/Meridian_Vendor_Input_MAVIRA_completed.xlsx` is the exported workbook from this run (status: pending
analyst review — approve or override in the UI before submitting).

The fictional worked example (V-000, Larkspur) is used as a calibration fixture: the engine reproduces
Critical / Yes, and rates risk High rather than Critical because the only usage evidence is an executive
social post (MEDIUM reliability) that does not name Meridian's service. See `backend/tests/test_worked_example.py`.

---

## Architecture

```mermaid
flowchart LR
  U[Analyst browser] -->|same origin| FE[Next.js frontend<br/>+ /api proxy]
  FE -->|server-side, API key injected| API[FastAPI backend]
  API --> PG[(PostgreSQL)]
  API -->|enqueue run| R[(Redis)]
  R --> W[RQ worker<br/>assessment pipeline]
  W --> PG
  W -->|LIVE only| SP[Search provider<br/>Tavily / Serper / Brave]
  W -->|LIVE only, SSRF-guarded| WEB[Public web pages]
  W -.optional.-> LLM[LLM via LiteLLM]
  W -->|DEMO| SNAP[Cached OSINT snapshot<br/>in repo]
```

A modular monolith: one backend codebase serves the API and runs the worker. Full detail in
[`docs/TECHNICAL_ARCHITECTURE.md`](docs/TECHNICAL_ARCHITECTURE.md).

## Tech stack

- **Backend:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, PostgreSQL 16, Redis + RQ,
  httpx, trafilatura, BeautifulSoup, openpyxl, PyYAML; LiteLLM optional.
- **Frontend:** Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS 4, shadcn/ui-style components
  on Radix primitives, Recharts, self-hosted fonts (Public Sans, Source Serif 4).
- **Infra:** Docker Compose — `frontend`, `backend`, `worker`, `postgres`, `redis`, optional `adminer`.

---

## How to Run the Application

You can run the application either **locally (recommended for quick testing/development)** or using **Docker Compose**.

### Option 1: Running Locally (Without Docker)

**Prerequisites:**
- Python 3.12+ (Python 3.13 supported)
- Node.js 20+ and npm

#### 1. Backend Setup (FastAPI)

1. Open a terminal and navigate to the `backend` directory:
   ```bash
   cd backend
   ```

2. Create a virtual environment and activate it:
   - **Windows (PowerShell):**
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```
   - **Linux / macOS:**
     ```bash
     python -m venv .venv
     source .venv/bin/activate
     ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the `backend/` directory:
   ```ini
   DATABASE_URL=sqlite:///mavira.db
   WORKER_MODE=inline
   OSINT_MODE=DEMO
   DEMO_STEP_DELAY_MS=150
   ASSESSOR_TEAM=Team MAVIRA
   STORAGE_DIR=storage
   CORS_ORIGINS=http://localhost:3000
   ```
   *(Note: SQLite works out of the box with zero database installation required. If you prefer PostgreSQL, set `DATABASE_URL=postgresql+psycopg://mavira:mavira@localhost:5432/mavira` and run `alembic upgrade head`)*.

5. Start the backend server:
   ```bash
   uvicorn app.main:app --port 8000
   ```
   The backend API will start at **http://localhost:8000**.
   - API Docs (Swagger): **http://localhost:8000/api/docs**
   - Health check: **http://localhost:8000/api/health**

---

#### 2. Frontend Setup (Next.js)

1. Open a new terminal and navigate to the `frontend` directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. (Optional) Create `.env.local` if custom backend URL is needed (defaults to `http://localhost:8000`):
   ```ini
   BACKEND_URL=http://localhost:8000
   ```

4. Start the development server:
   ```bash
   npm run dev
   ```
   The frontend UI will be live at **http://localhost:3000**.

   *Or for production build:*
   ```bash
   npm run build
   npm start
   ```

---

### Option 2: Running with Docker Compose

If you have Docker Desktop installed and running:

```bash
cp .env.example .env          # defaults run fully offline in DEMO mode
docker compose up --build
```

- Web UI: **http://localhost:3000**
- API Docs: **http://localhost:8000/api/docs**
- Optional DB UI: `docker compose --profile admin up adminer` → **http://localhost:8081**
- Ports are bound to `127.0.0.1` only.

---

### Using the Application

1. Open **http://localhost:3000** in your browser.
2. Click **Import workbook** and upload `sample_data/Meridian_Vendor_Input.xlsx`.
3. Click **Start assessment** to initiate the analysis pipeline (or observe existing vendor records).
4. Review vendor criticality, public AI usage signals, security risk scores, and evidence extracts.
5. Make analyst approvals/overrides and click **Export completed workbook**.

## Environment variables

See [`.env.example`](.env.example). Key ones:

| Variable | Default | Meaning |
|---|---|---|
| `DATABASE_URL` | local Postgres | SQLAlchemy URL |
| `REDIS_URL` | `redis://localhost:6379/0` | queue |
| `WORKER_MODE` | `inline` (compose: `rq`) | where runs execute |
| `OSINT_MODE` | `DEMO` | `DEMO` = cached snapshot, `LIVE` = search provider + fetch |
| `SEARCH_PROVIDER` | `none` | `tavily`, `serper`, `brave` |
| `TAVILY_API_KEY` / `SERPER_API_KEY` / `BRAVE_API_KEY` | — | provider keys |
| `LLM_PROVIDER` / `LLM_MODEL` / `LLM_API_BASE` | `none` | optional LiteLLM analyzer |
| `API_KEY` | — | optional shared API key (frontend proxy injects it; never sent to the browser) |
| `ASSESSOR_TEAM` | `Team MAVIRA` | written to *Assessed By / Date* |
| `DEMO_STEP_DELAY_MS` | `150` | pacing so progress is visible in demos; affects nothing else |

## Database

PostgreSQL schema managed by Alembic (`backend/alembic/versions/0001_initial_schema.py`). Tables:
`workbook_imports, vendors, assessment_runs, assessments, search_runs, sources, assessment_sources,
source_chunks, evidence, ai_signals, ai_providers, risk_factors, recommendations, analyst_reviews,
methodology_versions, audit_events`. Sources are de-duplicated by URL hash (unique) and by content hash
within an assessment. pgvector was not used: validation is exact lexical matching and nothing needs
semantic retrieval at this scale.

---

## Demo mode vs live OSINT

Every source carries a collection method shown in the UI and the export:

| Label | Meaning |
|---|---|
| **LIVE** | fetched from the public web during the run |
| **CACHED** | verbatim passages captured during an earlier analyst OSINT session, with retrieval timestamp |
| **DEMO_MOCK** | fictional fixture (only the V-000 worked example in tests) |

**DEMO (default)** uses `backend/app/demo_data/osint_cache.json`: 13 real public pages for the six vendors,
retrieved 2026-10-06, relevant passages kept verbatim (built by `backend/scripts/build_demo_cache.py`,
which documents each source). Vendor home pages with no AI content are included on purpose — they are part
of the negative-evidence record. Nothing in the snapshot is invented, and it is never labelled LIVE.
The snapshot only returns a page for the query categories that originally surfaced it, so depth tiers still
change what each vendor's review sees.

**LIVE**: set `OSINT_MODE=LIVE`, `SEARCH_PROVIDER=tavily|serper|brave` and the matching key. The same
pipeline then executes the tier's query plan against the provider and fetches each result through the
SSRF-guarded fetcher. JavaScript-only pages return thin content (Playwright is not bundled) and are recorded,
not guessed.

## LLM (optional)

Default analyzer: deterministic rules (`rules-v1.0`), no data leaves the machine. To use a model:

```bash
INSTALL_LLM=true LLM_PROVIDER=openai LLM_MODEL=gpt-4o-mini OPENAI_API_KEY=... docker compose up --build
# local model: LLM_PROVIDER=ollama LLM_MODEL=llama3.1 LLM_API_BASE=http://host.docker.internal:11434
```

The LLM only proposes excerpts and classifications. Its output is schema-validated (Pydantic); every excerpt
must be found verbatim in the stored source or it is rejected; providers it names are kept only if they appear
in that excerpt; it cannot mark a signal SERVICE_INTEGRATED unless the excerpt names the contracted service.
Criticality, depth, strength and risk are always computed by the deterministic engines. On any LLM failure the
rule-based analyzer runs and the failure is logged on the assessment. Model name and prompt version
(`mavira-evidence-v1`) are stored on every run.

## Excel import and export

- **Import** finds the sheet with a `Vendor ID` / `Vendor Name` header row, maps columns **by header text**
  (tolerates reordering and the workbook's `Assessedd By / Date` typo), validates required columns, flags
  duplicates and missing values, and detects the worked example (V-000) so it is stored but never assessed.
- **Export** (`/api/exports/excel`) reopens the uploaded workbook and writes only the eleven assessment columns
  of assessed rows, keeping existing cell styles. Provided columns and V-000 are untouched (asserted in tests).
  Analyst overrides take precedence and the reviewer is named in *Assessed By / Date*. Three sheets are added:
  **Evidence Log** (excerpt, URL, type, reliability, method, dates, signal type, strength, confidence,
  interpretation), **Sources Checked** (negative-evidence record) and **Methodology** (version, weights, tiers).
- The *Evidence Description* column follows the Field Guide: exact excerpts with URL, retrieval date, source
  type and collection method — no interpretation.
- JSON export: `/api/exports/json`.

## Tests

```bash
cd backend
pytest                                                    # SQLite
TEST_DATABASE_URL=postgresql+psycopg://mavira:mavira@localhost:5432/mavira_test pytest   # Postgres via Alembic
```

79 tests: criticality, depth, methodology validation, strength, usage determination, risk, recommendations,
evidence validation (incl. fabricated-quote rejection), rule classifier, provider detection, source
classification, LLM schema + hallucination guards (fake LLM), Excel import edge cases, SSRF/upload/rate-limit
controls, the worked-example calibration, and an end-to-end API test (upload → run → evidence verified
against source → review/override/reassess → Excel export with V-000 and provided columns unchanged → JSON →
audit). Frontend: `npm run build` (type-checks).

---

## Methodology

All weights, thresholds, tiers, rules and recommendation templates live in
`backend/app/config/methodology.yaml`, are hashed into a version on startup, and are editable from the
**Methodology** page (each save is a new version; old assessments keep theirs). Summary:

- **Criticality** = 0.30 operational dependency + 0.25 data sensitivity + 0.15 payment-flow role +
  0.15 regulatory exposure + 0.15 volume (log-scaled). Critical ≥ 0.75, High ≥ 0.55, Medium ≥ 0.35.
  Escalation floors: Critical dependency with sensitive data or payment-rail role → Critical; highest-sensitivity
  data at scale with High dependency → Critical; privileged production access with High dependency → High.
- **Depth**: Low (baseline) → Medium (standard) → High (enhanced, adds filings, sub-processors, executive
  statements) → Critical (full, adds partner/provider searches, corroboration, negative-evidence review,
  mandatory sign-off).
- **AI usage**: YES needs a confirming signal (in-service or product capability) with strength ≥ 65, or two
  from distinct sources ≥ 45. Marketing claims, commentary, hiring and partner signals never confirm.
  Absence of evidence is INCONCLUSIVE with the statement *"NO MEANINGFUL PUBLIC EVIDENCE IDENTIFIED WITHIN
  ASSESSED OSINT SCOPE"*; NO requires an explicit negative statement from a direct source.
- **Risk** (0–100): nine categories, each `base × AI presence`; unknowns (retention, training, contract,
  undisclosed provider) are scored as unknown and labelled *UNKNOWN / NOT PUBLICLY DISCLOSED*.

Full rationale: [`docs/SOURCE_STRATEGY.md`](docs/SOURCE_STRATEGY.md).

## Security considerations

- Secrets only via environment; nothing secret in the repo; API key never reaches the browser (server-side proxy).
- Upload: extension + ZIP magic check, 10 MB cap, per-client rate limit; workbook parsed with openpyxl (no macros).
- SSRF: scheme/port allow-list, no credentials in URLs, blocks loopback/private/link-local/metadata/IPv4-mapped
  and single-label hosts, resolves DNS and checks every answer, re-validates every redirect hop.
- Fetching: robots.txt honoured, per-domain throttle, timeouts, bounded retries, response size cap.
- SQL via ORM only; React escapes all rendered text (no `dangerouslySetInnerHTML`); CSP, X-Frame-Options,
  nosniff, no-referrer headers; generic error bodies with a reference id; JSON logs with secret redaction.
- Append-only audit trail for imports, runs, vendor results, reviews, methodology changes and exports.
- Containers run as non-root; Compose binds ports to 127.0.0.1.
- Not included (single-team local deployment): user accounts/SSO. Set `API_KEY` for any shared host and put
  the stack behind your SSO proxy.

## Privacy and data egress

| Mode | What leaves the environment |
|---|---|
| DEMO, no LLM (default) | Nothing |
| LIVE | Search queries (vendor name, domain, service keywords) to the search provider; HTTP GETs to public pages |
| LLM enabled | Public page text plus vendor name/category/service description to the configured model |

No Meridian customer data is ever sent: the inventory contains none beyond vendor descriptions. `/api/health`
returns this statement for the current configuration, and the sidebar shows the mode.

## Limitations and known assumptions

1. **The Case Study Brief PDF was not available** during the build. Requirements were taken from the build
   prompt and the workbook's *Field Guide* and *Points to consider* sheets. Reconcile against the brief.
2. **Only a text rendering of the workbook was available.** `sample_data/Meridian_Vendor_Input.xlsx` is a faithful
   reconstruction (same sheets, columns, rows, V-000 verbatim; blank column A; header row 3). Fill colours are
   approximations. The importer maps by header text, so the original file works directly.
3. The cached snapshot is a point-in-time capture (2026-10-06) of 13 pages; a LIVE run at Critical depth will
   examine more sources. Sources such as SEC filings, trust centres and sub-processor lists were not in the
   snapshot and are not claimed.
4. The rule-based classifier is transparent but literal; unusual phrasing can be misclassified. Every
   classification shows its cues, and analysts can override.
5. Docker Compose configuration is validated (`docker compose config`), and the same topology (Postgres 16,
   Redis, API, RQ worker, Next.js) was run and tested natively; the image build itself could not be executed in
   the build sandbox because Docker Hub was unreachable from it.
6. PDF vendor reports are not implemented (Excel and JSON exports are). PDF sources are not parsed in LIVE mode.
7. Executive social posts are capped at MEDIUM reliability because authorship cannot be machine-verified.
