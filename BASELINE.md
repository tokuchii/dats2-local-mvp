# DATS 2.0 Baseline

Phase 0 discovery report for the AANR Readiness Observatory.
Prepared from the local repository and TRACER's public pages only.
No live-site probing, no database writes, no LLM calls, and no secrets were read into this document.

## Repository state

- Local root: `C:\Users\kdrak\dats2-local-mvp`
- Branch: `main`
- HEAD: `261136e` (`updv6`, 2026-08-25)
- Remote: `https://github.com/tokuchii/dats2-local-mvp.git`
- Working tree before this report: clean, with `ROADMAP.md` untracked.
- Other branches seen: `origin/kenneth`, `origin/alfie`.
- `app/db.py` on `main`, `origin/kenneth`, and `origin/alfie` all import `psycopg2`; no SQLite version of the application code was found.
- The only SQLite artifact is `backups/dats2-2026-07-13-1223.sqlite3`, a legacy backup.

## Architecture map

### Runtime

- Web application: FastAPI, started by Uvicorn (`run_local.py`) or Gunicorn in the container (`Dockerfile`).
- Pages: Jinja2 templates in `app/templates/`.
- Database: PostgreSQL through `psycopg2` and a thread pool (`app/db.py:13-43`).
- Schema: `schema/postgresql.sql`, plus an in-code schema and startup `ALTER` (`app/db.py:65-157`, `app/db.py:199-207`).
- Master import: OpenPyXL reads `data/DATS_2.0_Philippines_Master_2026.xlsx` when `systems` is empty (`app/db.py:224-284`).
- Evidence acquisition: HTTPX and BeautifulSoup for URLs; pypdf for PDFs; OpenPyXL for spreadsheets (`app/agent.py:200-279`).
- LLM: OpenAI-compatible client, configured through `OPENAI_*` or `LLM_*` environment variables (`app/agent.py:523-555`, `app/config.py:51-73`).
- Duplicate matching: RapidFuzz (`app/agent.py:558-575`).
- Server-sent events: in-process publisher/subscriber (`app/sse.py`).

### Main flows

1. Intake: `POST /submit/url`, `/submit/text`, or `/submit/file` creates a `submissions` row and queues `process_submission` as a FastAPI background task (`app/main.py:223-286`).
2. Assessment: the agent acquires evidence, tries the LLM, falls back to `heuristic_assessment`, finds duplicates, and creates a `candidates` row with status `proposed` (`app/agent.py:578-603`).
3. Review: `/review/{id}` displays the candidate and creates a per-candidate `review_token` if absent (`app/main.py:310-320`).
4. Decision: `/review/{id}/approve` or `/reject` checks the per-candidate token, then updates `systems`, `system_versions`, `candidates`, `submissions`, and `audit_events` (`app/main.py:404-440`, `app/db.py:579-649`).
5. Read-only views: dashboard, systems explorer, audit log, XLSX/CSV export, and authenticated JSON APIs (`app/main.py:168-207`, `443-495`).

### Data model

Tables in `schema/postgresql.sql`:

- `systems` — canonical record, one row per `dats2_id`, with `payload_json` and `current_version`.
- `submissions` — intake record with source type, URI, upload path, pasted text, submitter, and status.
- `candidates` — agent proposal with `payload_json`, `evidence_json`, `duplicates_json`, confidence, and review state.
- `system_versions` — versioned payload snapshots, optionally linked to a candidate.
- `audit_events` — actor, action, entity type, entity ID, details, timestamp.

Observed drift and gaps:

- `candidates.review_token` exists in code (`app/db.py:203`) but not in `schema/postgresql.sql`.
- No user or role table exists.
- No CHECK constraint limits `systems.interoperability_score` to its intended 0-4 range; the UI clamps it (`app/main.py:385`).
- No index exists on `candidates.status` or `submissions.status`.
- `audit_events.actor` is free text; the review form defaults to `local-reviewer` (`app/templates/candidate_detail.html:54`, `app/main.py:408`).
- `init_db()` applies schema and then a live `ALTER TABLE` at startup (`app/db.py:199-207`).

## Data inventory

Read with OpenPyXL against `data/DATS_2.0_Philippines_Master_2026.xlsx`.

- Sheets: `Dashboard`, `DATS 2.0 Inventory`, `Scaling Scan`, `Taxonomy & Codebook`, `Bottlenecks & Evidence`, `SINAG Integration Map`, `Literature & Sources`, `Source Code & Interop`, `Research Prototypes`, `Category Crosswalk`.
- Inventory data starts at row 5 and has 133 rows and 133 unique IDs.
- IDs run from `D2-001` to `D2-133`.
- The inventory has 37 headers.
- `INVENTORY_KEYS` (`app/db.py:160-188`) does not map 10 workbook headers: `Value-chain Stage`, `Original DATS/PIDS Bucket`, `CSA: Productivity`, `CSA: Adaptation`, `CSA: Mitigation`, `Potential SINAG Role`, `Last Verified`, `Notes`, `All Functional Category Tags`, and `Functional Category Count`.
- Imported rows keep Excel-shaped `payload_json`; reviewed candidates use Assessment-shaped payloads (`app/agent.py:68-103`). Any merge or evidence-sheet code must handle both shapes.
- `interoperability_score` is inserted as `NULL` for all imported records (`app/db.py:269`).

## Findings

### PostgreSQL and AI configuration

- The brief's claim that `app/db.py` uses SQLite is outdated for this checkout; it uses PostgreSQL.
- The brief's claim that `app/agent.py` uses a local Ollama model by default is also outdated. The code uses an OpenAI-compatible endpoint; the local `.env` points at a DeepSeek-compatible base URL, while `.env.production` still contains placeholder OpenAI GPT-4o-mini settings.
- If no key is configured, `openai_assessment` uses the literal string `ollama` as the API key and still tries the configured endpoint; failure then falls back silently (`app/agent.py:523-555`).
- There is no visible daily AI-call cap or spend limit. Every public submission can start an LLM attempt.

### Authentication and authorization

- `REVIEWER_TOKEN` is read from the environment and warns when empty (`app/config.py:40-45`).
- The local `.env` has `REVIEWER_TOKEN` commented out. If it is empty at runtime, `ensure_api_auth` compares an empty supplied token with an empty configured token and accepts it; `/api/*` then requires no credential (`app/main.py:135-142`).
- `/review/{id}` is public, mints a per-candidate token if absent, and renders it in the page (`app/main.py:310-320`, `app/templates/candidate_detail.html:55`).
- `/review/{id}/save` has no token or authentication check at all (`app/main.py:323-401`).
- Approve and reject check only the per-candidate token that the public review page displays; the shared `REVIEWER_TOKEN` is not required (`app/main.py:404-440`).
- `/review`, `/audit`, `/submissions/{id}`, and system pages are public.
- The audit actor is whatever the reviewer types; no identity is verified.

### Outbound URL controls

- `validate_public_url` resolves and blocks private, loopback, link-local, reserved, multicast, and unspecified addresses (`app/agent.py:124-138`).
- `httpx.Client` follows redirects, but only the first URL is validated; each redirect hop is not re-checked (`app/agent.py:200-211`).
- The response body is downloaded before the 12 MB check; the check only examines the `content-length` header after the request (`app/agent.py:218-219`).
- There is no outbound proxy, domain allowlist, or per-hop timeout budget.

### Upload handling

- Extensions are allowlisted and the upload size is capped while writing (`app/main.py:259-286`).
- There is no antivirus scan, content sniffing, sandbox, or object storage.

### Submission and API exposure

- `POST /submit/*` has no rate limit or CAPTCHA.
- `/api/candidates` requires the shared token when `REVIEWER_TOKEN` is set, but returns submitter names and candidate details (`app/main.py:487-490`, `app/db.py:480-506`).
- `/api/proposed-count` is public and unauthenticated (`app/main.py:493-495`).
- No CSRF protection, secure session, or login exists.

### Merge behavior

- `approve_candidate(..., merge_into=...)` builds a full column map from the candidate payload and writes every column, including missing or empty values (`app/db.py:547-576`, `app/db.py:588-601`). A merge can therefore overwrite existing canonical values with blanks.

### Tests

- `tests/test_smoke.py` imports the application and uses the configured database.
- Several tests delete rows from `system_versions`, `candidates`, and `submissions` (`tests/test_smoke.py:122-127`, `148-153`, `166-171`, `188-193`).
- Phase 0.2 was run against a throwaway PostgreSQL database, not the configured one.

### Phase 0.2 test evidence

- Date: 19 November 2026.
- Runner: global Python 3.14.5 with pytest 9.1.1; all application dependencies were importable. The project `.venv` lacked pytest, so no packages were installed or changed.
- Database: disposable `postgres:16-alpine` container named `dats2-test-pg`, database `dats2_test`, bound only to `127.0.0.1:55432`, with no host volume.
- LLM isolation: `LLM_BASE_URL=http://127.0.0.1:9` and `LLM_API_KEY=ollama`; no hosted model was called.
- Command: `python -m pytest -q` with `DATABASE_URL` pointed at the disposable database and `REVIEWER_TOKEN=test-reviewer-token`.
- Result: `9 passed, 3 warnings in 47.35s`.
- Warnings: one Starlette/httpx `TestClient` deprecation warning; two OpenPyXL warnings about unsupported workbook extensions.
- Cleanup: the test container was removed and port 55432 was confirmed free. The configured database was not used. The `postgres:16-alpine` image remains cached locally and may be removed separately.

## TRACER public facts

Read-only review of `https://aanr-tracer.com` and its public pages: Home, About, Terms & Definitions, FAQs, Privacy Policy, Contact Directory, Documents, and `robots.txt`.
No API, question set, or scoring logic was accessed. `robots.txt` disallows `/api/`.

### Levels

TRACER publishes nine levels:

1. Concept & Market Definition
2. Design / Formulation / Prototype Planning
3. Prototype Development & Laboratory Testing
4. Controlled Validation & IP Filing
5. Pilot Testing & Industry Engagement
6. Multi-location Testing & Scale-up Preparation
7. Industry Validation & Regulatory Submission
8. Commercial Production Readiness
9. Full Commercialization

### Technology types

1. Food, Food Ingredients and Beverages
2. Animal Feed, Feed Ingredients and Animal Nutrition
3. Fertilizer and Pesticide
4. Agri-Aqua Machinery and Facility
5. Agri-Aqua Device and Diagnostic Kits
6. ICT (Apps and Systems involving IoT)
7. New Plant Variety
8. New Animal Breed (Aquatic and Terrestrial)
9. Natural Resource-Derived Materials

### Assessment areas

TRACER describes five areas:

1. Technology development status / technology status
2. Intellectual property position / IP protection
3. Market and pre-commercialization readiness
4. Industry validation and adoption
5. Regulatory compliance

### Stated process and output

- Choose a technology type.
- Answer structured questions across the five areas.
- Receive the highest completed level, strengths, gaps, and a roadmap.

### Privacy and data handling

- No account or login is required.
- Assessment input stays in the browser until submission.
- On submission, a summary is sent to DOST-PCAARRD for monitoring, evaluation, research, and program improvement.
- OpenAI generates the roadmap and chatbot replies; it receives the technology description and chat messages.
- Resend sends the summary and optional report email.
- Upstash is used for rate limiting by IP.
- No cookies, advertising, or analytics are used.
- A report can be downloaded, printed, or emailed before leaving the results page; it cannot be recovered afterward.

### Contact and ownership

- Contact: `ttbdo.upvisayas@up.edu.ph`, `09054439916`, DOST-PCAARRD, Jamboree Road, Los Baños, Laguna.
- Footer: copyright 2026 University of the Philippines Visayas. All rights reserved.
- No explicit reuse, linking, logo, or data-extraction permission was found on the public pages.

### Not public

- Question sets.
- Scoring rules and decision thresholds.
- Per-level criteria for every technology type.
- Report schema and export format.
- Any results API.
- The answers hidden behind the collapsed FAQ buttons were not rendered in the fetched HTML; they were not bypassed or scraped.

## Risks

1. Review decisions are currently not authenticated in any meaningful way, and the save route is completely unprotected.
2. Empty `REVIEWER_TOKEN` can open the JSON APIs.
3. Public submissions can trigger paid LLM calls with no cap.
4. Redirect-based SSRF remains possible because only the first URL is validated.
5. The live site is public while the README's own pre-deployment checklist is not met.
6. `dat.pandoy.online` deployment state is unknown; local code, local `.env`, and `.env.production` disagree on the model provider.
7. TRACER's name, logo, report content, and derived level fields need written permission before Phase 2.
8. Submitting DATS evidence to TRACER would send it through OpenAI and DOST-PCAARRD; confidentiality and data-class rules must be settled first.
9. `baseline` and test claims are limited to the local checkout; the live host was not inspected.

## Open C0 questions

1. What does Doc Arnan mean by "link": hyperlink, data hand-off, or full integration?
2. Who is the AANR-TRACER contact at DOST-PCAARRD or UPV TTBDO, and will Doc Arnan make the introduction?
3. Who owns the DATS repository and the `dat.pandoy.online` deployment, and will it stay on that domain?
4. Which database, AI model, and `REVIEWER_TOKEN` setting are live today?
5. Which records are government-funded and TRACER-eligible, and who decides eligibility?
6. Does TRACER provide any export or API, and may DATS use its name and logo?
7. Which submissions are public versus unpublished IP or personal data, and which LLM providers are allowed per data class?
8. Who are the reviewers, is English only or English and Filipino, and when is the next presentation to Doc Arnan?

## Unverified items

- Live deployment configuration, database contents, model provider, and whether `REVIEWER_TOKEN` is set on the host.
- Phase 0.4 owner walkthrough and a real TRACER report format.
- TRACER's hidden FAQ answers and any non-public assessment methodology.
- Whether the live site actually serves this exact commit.

## Suggested next steps

1. Approve and send the Phase 0.6 permission-request draft.
2. Use the isolated PostgreSQL test procedure from Phase 0.2 for future test runs.
3. Answer C0 before Phase 1.3 eligibility and Phase 1.2 hardening are finalized.
4. Change Phase 2.2 from "port SQLite to PostgreSQL" to "verify the existing PostgreSQL schema, resolve drift, and back up before migration."
