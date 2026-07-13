-- DATS 2.0 PostgreSQL Schema
-- Run: psql -U <user> -d <database> -f schema/postgresql.sql

BEGIN;

-- ─── Systems ───────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS systems (
    id                  SERIAL PRIMARY KEY,
    dats2_id            TEXT UNIQUE NOT NULL,
    name                TEXT NOT NULL,
    acronym             TEXT,
    developer_owner     TEXT,
    owner_type          TEXT,
    sector_commodity    TEXT,
    geographic_scope    TEXT,
    primary_category    TEXT NOT NULL,
    secondary_categories_json  JSONB NOT NULL DEFAULT '[]',
    commodity_tags_json        JSONB NOT NULL DEFAULT '[]',
    value_chain_tags_json      JSONB NOT NULL DEFAULT '[]',
    technology_tags_json       JSONB NOT NULL DEFAULT '[]',
    livestock_coverage  TEXT,
    core_function       TEXT,
    technology_channel  TEXT,
    primary_users       TEXT,
    maturity            TEXT,
    operating_status    TEXT,
    evidence_of_scale   TEXT,
    main_scaling_strength TEXT,
    primary_bottleneck  TEXT,
    interoperability    TEXT,
    interoperability_score INTEGER,
    source_url_1        TEXT,
    source_url_2        TEXT,
    evidence_confidence TEXT,
    sinag_priority      TEXT,
    recommended_sinag_action TEXT,
    payload_json        JSONB NOT NULL DEFAULT '{}',
    current_version     INTEGER NOT NULL DEFAULT 1,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_systems_name ON systems (name);
CREATE INDEX IF NOT EXISTS idx_systems_primary_category ON systems (primary_category);
CREATE INDEX IF NOT EXISTS idx_systems_status ON systems (operating_status);
CREATE INDEX IF NOT EXISTS idx_systems_livestock ON systems (livestock_coverage);
CREATE INDEX IF NOT EXISTS idx_systems_dats2_id ON systems (dats2_id);

-- ─── Submissions ───────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS submissions (
    id              SERIAL PRIMARY KEY,
    source_type     TEXT NOT NULL,
    source_uri      TEXT,
    uploaded_path   TEXT,
    pasted_text     TEXT,
    submitted_by    TEXT,
    status          TEXT NOT NULL DEFAULT 'queued',
    error_message   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── Candidates ────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS candidates (
    id              SERIAL PRIMARY KEY,
    submission_id   INTEGER NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
    status          TEXT NOT NULL DEFAULT 'proposed',
    assessment_mode TEXT NOT NULL,
    payload_json    JSONB NOT NULL DEFAULT '{}',
    evidence_json   JSONB NOT NULL DEFAULT '[]',
    duplicates_json JSONB NOT NULL DEFAULT '[]',
    confidence      DOUBLE PRECISION NOT NULL DEFAULT 0,
    reviewer_note   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reviewed_at     TIMESTAMPTZ
);

-- ─── System Versions ──────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS system_versions (
    id              SERIAL PRIMARY KEY,
    system_id       INTEGER NOT NULL REFERENCES systems(id) ON DELETE CASCADE,
    version         INTEGER NOT NULL,
    payload_json    JSONB NOT NULL DEFAULT '{}',
    candidate_id    INTEGER REFERENCES candidates(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (system_id, version)
);

-- ─── Audit Events ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS audit_events (
    id              SERIAL PRIMARY KEY,
    actor           TEXT NOT NULL,
    action          TEXT NOT NULL,
    entity_type     TEXT NOT NULL,
    entity_id       TEXT NOT NULL,
    details_json    JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_events (created_at DESC);

COMMIT;
