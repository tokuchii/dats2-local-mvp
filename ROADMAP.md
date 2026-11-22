Part C. Roadmap and task trees (save everything in Part C as ROADMAP.md)
Legend: [R] read-only, no approval needed · [C] changes something, needs a Change Proposal and your “approve” · [U] needs input from the owner or from DOST-PCAARRD/UP Visayas before it can start.
Phase 1 is the link Doc Arnan asked for and involves no PCAARRD data. Phases 2 and 3 move data, so they wait for written permission from PCAARRD and UP Visayas.
Decisions made by the owner
• Database: PostgreSQL. The supplied db.py is SQLite, so either the repo already has a PostgreSQL version on another branch (task 0.1.1) or db.py must be ported (task 2.2).
• AI provider: the DeepSeek API through its OpenAI-compatible endpoint. Doc Arnan’s local Ollama setup stays as an optional adapter and is the only route that keeps confidential submissions off a hosted service (task 4.1).
• What follows: the public submit form must not be able to start paid AI calls unattended, so the cost and rate limits in task 1.2 come before DeepSeek is switched on.
C0. Open questions to ask the owner before Phase 1 [U]
• What does Doc Arnan mean by “link”: a hyperlink, a data hand-off or a full integration? Confirm with him before Phase 2.
• Who is the AANR-TRACER contact at DOST-PCAARRD or the UP Visayas TTBDO, and will Doc Arnan make the introduction?
• Who owns the DATS repo and the dat.pandoy.online deployment, and will it stay on that domain or move to a DOST or PCAARRD host? Which database and AI model is the live site running today (the supplied code uses SQLite and Ollama; the chosen targets are PostgreSQL and the DeepSeek API), and is REVIEWER_TOKEN set on it?
• Which DATS records are government-funded technologies eligible for TRACER, and who decides: the reviewer or PCAARRD?
• Does TRACER offer an export of results or any API, and may DATS use TRACER’s name and logo?
• Which submissions are public, and which may hold unpublished IP or personal data? Which LLM providers are allowed for which data class (hosted API, self-hosted, none)?
• Who are the reviewers, is it English only or English and Filipino, and when is the next presentation to Doc Arnan?
Phase 0. Discovery and baseline
Goal: know exactly what exists on both sides before linking anything. Outcome: a short baseline report you can verify.
• 0.1 Map the DATS repo [R]
    ◦ 0.1.1 Check the owner-supplied schema/postgresql.sql (systems, submissions, candidates, system_versions, audit_events) against the database that is actually deployed (db.py uses SQLite; the README and schema file say PostgreSQL, the chosen target), look for a PostgreSQL version of db.py on another branch, and record any drift; note schema gaps (no user or role table, no CHECK limit on interoperability_score, no index on candidates.status or submissions.status)
    ◦ 0.1.2 Re-read app/ against the deployed version: main.py, db.py, agent.py and config.py were supplied by the owner; templates, tests and data/ were not
    ◦ 0.1.3 Read data/ (master workbook structure) and tests/
• 0.2 Run the existing tests on a throwaway database and record the result [R]
• 0.3 Read TRACER’s public pages (Home, About, Terms & Definitions, FAQ, Contact Directory, Privacy Policy) [R]
    ◦ 0.3.1 Record the level names, the 9 technology types, the five assessment areas and any rule on linking or reuse
    ◦ 0.3.2 List what is not public (questions, scoring rules, report and export format)
• 0.4 Owner walks through one real TRACER assessment and shares the report format [U]
• 0.5 Write BASELINE.md: architecture map, gap list, risks, answers to C0 [C]
• 0.6 Draft the permission request to the UP Visayas TTBDO and DOST-PCAARRD for Doc Arnan to send [C]
Exit gate: owner approves the baseline and the draft request.
Phase 1. Safe link (no PCAARRD data involved)
Goal: do what Doc Arnan asked in its lightest form, safely. Outcome: from an eligible DATS record you click once to AANR-TRACER with an evidence sheet in hand, and no data leaves DATS.
• 1.1 Safety check of the live site, because it is already public [R]
    ◦ 1.1.1 Compare the live setup with the DATS README’s own pre-deployment list (login, CSRF, rate limiting, upload scanning, outbound URL controls, backups)
    ◦ 1.1.2 Report which items are in place and which are not, without probing the live site for weaknesses. From the supplied code, check these first: REVIEWER_TOKEN is set on the host (config.py falls back to a public placeholder); POST /review/{id}/save has no token check; fetch_url validates only the first URL, so redirects to private addresses are not re-checked, and it reads the whole download before applying any size limit; /api/candidates shows submitter names without login; the audit actor is a free-text name; nothing rate-limits submissions or token attempts
• 1.2 Minimum hardening before the link is promoted [C]: a strong reviewer token with no default fallback in config.py, a token check on /review/{id}/save, every redirect hop re-validated and downloads size-capped in fetch_url, submitter names hidden from /api/candidates, rate limits on /submit/* and on token attempts, a daily cap on AI calls plus a spend limit on the DeepSeek key (each public submission would otherwise trigger a paid call; or let only reviewers start the AI step), field-level merging so approve-with-merge does not overwrite existing values with empty ones, HTTPS only, backup schedule confirmed
• 1.3 Eligibility rule [C]: derived from developer_owner (free text) and owner_type (never filled by the fallback assessment, so empty for web submissions): records owned by DOST, PCAARRD or PCAARRD-funded teams get a TRACER link, marketplaces and private apps do not; a reviewer override is kept in payload_json or one new nullable column
• 1.4 TRACER link [C]
    ◦ 1.4.1 “Assess readiness in AANR-TRACER” button on eligible record pages (app/templates/system_detail.html, not yet seen), opening aanr-tracer.com in a new tab
    ◦ 1.4.2 One-line explainer: DATS classifies a system; TRACER measures its readiness
• 1.5 Relabel DATS’s “Assess a system” button to “Submit a system” on the dashboard and intake page [C]
• 1.6 Evidence sheet per record [C]
    ◦ 1.6.1 New route /systems/{dats2_id}/tracer-sheet (HTML and CSV) backed by a new app/tracer.py: a printable page grouped by TRACER’s five assessment areas, filled from existing columns: technology status from maturity, operating_status and technology_tags_json; market readiness from primary_users, sector_commodity and main_scaling_strength; industry validation from evidence_of_scale, evidence_confidence and the two source URLs. DATS has no IP or regulatory columns, so those two areas stay blank for the reviewer
    ◦ 1.6.2 Labelled PROVISIONAL (not the official TRACER questions), with blanks where DATS has no data
• 1.7 Tests [C]: link targets resolve, the eligibility rule, the sheet output, and a check that nothing is sent to TRACER
• 1.8 Ask TRACER’s team to link back to DATS [U]
Exit gate: demo to Doc Arnan, from a DATS record to TRACER with the evidence sheet.
Phase 2. Record TRACER results on DATS (needs written permission)
Goal: bring readiness levels into the registry without automating TRACER. Outcome: DATS shows a reviewer-confirmed TRACER level on records, and you can filter and export by level.
• 2.1 Written permission and scope from DOST-PCAARRD and UP Visayas: use of the TRACER name and logo, what may be stored, privacy terms [U]
• 2.2 Move to PostgreSQL, then add the data model, backup first [C]: port app/db.py from SQLite to psycopg2 (? placeholders to %s, AUTOINCREMENT to SERIAL, TEXT JSON columns to JSONB, ISO text timestamps to TIMESTAMPTZ, json_array_length and LIKE-on-JSON filters to JSONB operators). Note that the current _unjson helper would silently return empty defaults for JSONB values, which psycopg2 already returns as Python objects. Copy the 133 records, versions and audit events across and compare row counts and a sample of rows
    ◦ 2.2.1 A new readiness_assessments table (system_id referencing systems.id; technology type, TRACER level 1–9, assessment date, assessor, status, report file path) added to schema/postgresql.sql with CREATE TABLE IF NOT EXISTS (applied by init_db at start-up once db.py is ported), with a matching rollback script; existing tables are not touched
    ◦ 2.2.2 Log every change in the existing audit_events table (entity_type readiness_assessment); system_versions stays as it is
• 2.3 Reviewer screen to record the level from a TRACER report the innovator shares, with the report attached [C]
• 2.4 Level badge on records, a level filter in /systems, and a level column in the XLSX and CSV exports [C]
• 2.5 Publish dats2_id (for example D2-133), which already exists as a unique column, as the stable public ID, and write a data dictionary [C]
• 2.6 Level distribution chart by functional category on the dashboard [C]
Exit gate: 10 records carry reviewer-confirmed levels, and the owner and TRACER’s team have reviewed the data dictionary.
Phase 3. Deeper integration (only if TRACER’s owners agree)
Goal: exchange data without re-typing. Outcome: results flow between the two sites through an agreed channel, and every import is still approved by a reviewer.
• 3.1 Ask whether TRACER has a results export, an API or shared identifiers; meanwhile no scraping or automation of its site [U]
• 3.2 If TRACER provides an export file: import it into the Phase 2 fields, held in the review queue until a reviewer approves [C]
• 3.3 If TRACER provides an API: a connector with caching, provenance, timeouts and a kill switch [C]
• 3.4 Pre-fill: send DATS evidence to TRACER only if TRACER supports it and both owners approve in writing [C][U]
• 3.5 Align with DOST’s PHITEST readiness framework once TRACER’s team confirms how their levels map to it [U]
Exit gate: one agreed channel working on 5 records, or a written decision that Phase 2 is the stopping point.
Phase 4. Evidence and AI layer
Goal: cited evidence behind every level, and a model setup that can change. Outcome: each assessed record shows sourced facts with a retrieved-on date, and the AI step can switch providers.
Rule: every external source starts with a read-only probe proposal (one request, no key) before any code is written.
• 4.1 Model gateway [C]: one interface; DeepSeek API as the default hosted adapter, through its OpenAI-compatible endpoint with the key in .env as DEEPSEEK_API_KEY, replacing the Ollama call in agent.py. DeepSeek’s JSON mode returns valid JSON but does not enforce a schema, so put the word json and an example in the prompt, set max_tokens, keep the Pydantic validation, retry once on empty output, then fall back. Keep the deterministic fallback and the local Ollama path as optional adapters (agent.py already falls back silently). Strip emails and phone numbers from page content before any hosted call; routing by data class so confidential data never reaches a hosted provider without written approval; prompt and model version registry
• 4.2 Evaluation harness [C]: gold set from the 133 reviewed records, mapped from the Excel headers to the Assessment fields through INVENTORY_KEYS in db.py (imported rows keep Excel-shaped payloads, approved rows keep Assessment-shaped ones), plus proposed-vs-approved pairs from candidates.payload_json and system_versions.payload_json (linked by candidate_id) wherever the review queue was used; split results by candidates.assessment_mode (Ollama or fallback); field accuracy, category F1, cost and latency per model; the first hosted-model run needs its own approval
• 4.3 Connector framework [C]: caching, rate limits, provenance fields, offline mode
• 4.4 PSA OpenStat (PxWeb API) [C]: production and prices as market evidence; probe first because a data-catalog registry marks its API status uncertain
• 4.5 NASA POWER [C]: climate-fit hint for trial siting; no authentication
• 4.6 AGROVOC [C]: normalise commodity and species tags; check Filipino coverage first
• 4.7 IPOPHL [C][U]: link-out and reviewer checklist only; automate with IPOPHL’s written permission
• 4.8 Evidence pre-fill for the evidence sheet and reviewer screen [C]: one narrow agent per assessment area, answers with citations, combined by rule; a missing fact reads “needs evidence”, never “fail”; also back-fill interoperability_score, which is empty for all 133 imported records
• 4.9 Calibration [U][C]: experts rate 20 technologies independently; compare with the agent and agree an acceptance threshold
Exit gate: each source demonstrated on 5 records, and the calibration report approved.
Phase 5. Unified platform, hardening and handover
Goal: one product, safe on an institutional host. Outcome: the submit, assess, review, portfolio and export journey works end to end and is ready for a pilot.
• 5.1 Portfolio view [C]: level × category × commodity heatmap, a readiness × use quadrant (innovation use scored 0–9), an overlap panel (“integrate, extend or build new”), and a list of stale and unverified records
• 5.2 Assess wizard in TRACER’s style [C][U]: only with TRACER’s owners’ approval and the official criteria
• 5.3 Open API /api/v1 [C]: OpenAPI docs, stable IDs, CSV, XLSX and JSON export
• 5.4 Hardening for an institutional host [C]: OIDC login with roles (Innovator, Reviewer, Programme manager, Admin) mapped to new user and role tables (audit actors are free-text names typed on the review form, so attribution is not yet trustworthy), CSRF, secure sessions, upload scanning, outbound proxy, background worker, object storage, monitoring
• 5.5 Privacy [C][U]: Data Privacy Act review, privacy impact assessment, retention rules, crawl policy that respects robots and site terms
• 5.6 Pilot [C][U]: the eligible DATS records plus 10–20 technologies from partner institutions; track reviewer minutes per record, agent–human agreement, duplicates found and cost per record
• 5.7 Documentation and handover [C][U]: user manual, reviewer guide, data dictionary, API guide, runbook, ownership agreement, presentation pack for Doc Arnan
Exit gate: pilot results approved, and ownership and hosting agreed.
