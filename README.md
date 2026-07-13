# DATS 2.0 Local Agentic Dashboard

A runnable, local-first web dashboard for the Philippine **Digital Agriculture Tools and Services 2.0** inventory.

The application starts with the bundled 133-system master database and supports:

- interactive dashboard and searchable systems explorer;
- primary plus secondary functional categories;
- commodity/species, value-chain, technology, and livestock/poultry filters;
- URL, pasted-text, and document submission;
- automatic evidence extraction and structured DATS assessment;
- optional local Ollama assessment with deterministic fallback;
- duplicate/entity-resolution suggestions;
- editable reviewer queue;
- approve as a new system or merge into an existing DATS2 ID;
- system version history and audit events;
- current-database XLSX and CSV export.

## Fastest Windows setup

1. Extract the ZIP to a normal folder, such as `Documents\DATS2`.
2. Install **Python 3.11 or newer** if it is not already installed.
3. Install **PostgreSQL** if not already installed and create a database.
4. Run the schema:

   ```bash
   psql -U <user> -d <database> -f schema/postgresql.sql
   ```

5. Edit `.env` and set `DATABASE_URL` to your PostgreSQL connection string.
6. Double-click:

   ```text
   START_DATS2_WINDOWS.bat
   ```

7. The browser opens at:

   ```text
   http://localhost:8501
   ```

The first launch creates a private Python environment and installs the required open-source packages. Later launches reuse that environment.

## macOS or Linux

```bash
chmod +x START_DATS2_MAC_LINUX.sh
./START_DATS2_MAC_LINUX.sh
```

Then open `http://localhost:8501`.

## Reviewer token

On first launch, `.env.example` is copied to `.env`. Change this value before approving records:

```env
REVIEWER_TOKEN=replace-with-a-long-local-secret
```

The token is required only for **approve/merge/reject** actions. Public exploration and submissions do not require it in this local MVP.

## Optional local AI with Ollama

The application works without an LLM. Its deterministic fallback extracts categories, tags, maturity signals, technical links, interoperability evidence, and duplicate matches.

For stronger structured extraction, install Ollama and pull a small model, for example:

```bash
ollama pull gemma3:4b
```

Then edit `.env`:

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma3:4b
```

Restart the dashboard. Candidate records will show the assessment mode used.

## Agent workflow

```text
Submission
  ├─ public URL
  ├─ pasted description/evidence
  └─ PDF/TXT/MD/CSV/JSON file
        ↓
Acquire and parse evidence
        ↓
Structured field extraction
        ↓
Primary + secondary category classification
        ↓
Commodity, value-chain, technology and livestock tags
        ↓
Source-code/API/export/interoperability assessment
        ↓
Duplicate/entity-resolution matching
        ↓
Candidate change proposal
        ↓
Human edit and approval gate
        ├─ approve as new D2-WEB record
        ├─ merge into existing DATS2 ID
        └─ reject
        ↓
Versioned canonical database + audit event
```

The agent never directly changes a canonical system record.

## Local technical stack

| Layer | Technology |
|---|---|
| Web application/API | FastAPI |
| Pages | Jinja2 + vanilla CSS |
| Database | PostgreSQL (psycopg2) |
| Master import/export | OpenPyXL |
| Web acquisition | HTTPX + BeautifulSoup |
| PDF extraction | pypdf |
| Duplicate matching | RapidFuzz |
| Optional local model | Ollama structured JSON output |
| Server | Uvicorn |

There is no Node.js, Docker, Redis, Celery, or cloud service requirement for the local MVP.

## Main pages

- `/` — dashboard
- `/systems` — search and multi-dimensional filters
- `/submit` — URL, pasted text, or file intake
- `/review` — candidate review queue
- `/audit` — governance activity log
- `/api/summary` — JSON dashboard data
- `/api/systems` — JSON systems endpoint
- `/export/current.xlsx` — export the current canonical database

## Database and backups

The application connects to PostgreSQL using the `DATABASE_URL` environment variable in `.env`.

Run the schema once on your PostgreSQL instance:

```bash
psql -U <user> -d <database> -f schema/postgresql.sql
```

Use `BACKUP_DATABASE_WINDOWS.bat` or `pg_dump` to back up the database.

Use `RESET_DATABASE_WINDOWS.bat` to rebuild the database from the bundled master workbook.

## Security boundaries in this MVP

Implemented:

- human approval before canonical updates;
- private/loopback/link-local URL blocking;
- file type and upload-size restrictions;
- reviewer token for write decisions;
- candidate and system version history;
- audit events;
- conservative repository/API claims;
- no cloud dependency by default.

Before a public internet deployment, add:

- institutional OIDC/Keycloak login and roles;
- CSRF protection and secure sessions;
- antivirus/document sandboxing;
- rate limiting and CAPTCHA;
- production SSRF controls using an outbound proxy;
- task workers, object storage, backups, and observability;
- source terms/robots compliance and domain crawl policy;
- model evaluation and prompt/version registry;
- claim-level reviewer interfaces and two-person approval for sensitive changes.

## Tests

```bash
python -m pytest -q
```

The smoke suite verifies master import, dashboard rendering, pasted-text assessment, poultry classification, review rendering, and approval behavior.

## Important interpretation

An agent proposal is not verified truth. It is a structured reading of submitted evidence. Operating status, scale, public source-code availability, API access, licensing, ownership, and interoperability must remain conservative until supported by authoritative evidence and reviewer validation.
