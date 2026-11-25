"""Phase 5: SQLite schema for incidents, ingested documents and the audit log."""

SCHEMA = """
CREATE TABLE IF NOT EXISTS incidents (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    service     TEXT,
    severity    TEXT CHECK (severity IN ('Sev1','Sev2','Sev3','Sev4')),
    status      TEXT DEFAULT 'open',
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS documents (
    doc_id      TEXT PRIMARY KEY,      -- sha256 of file content
    filename    TEXT NOT NULL,
    doc_type    TEXT,                  -- runbook | sop | postmortem
    service     TEXT,
    chunks      INTEGER,
    ingested_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    ts                TEXT NOT NULL,
    user              TEXT,
    incident_id       TEXT,
    action            TEXT,            -- chat | ingest | ...
    question          TEXT,
    rewritten_queries TEXT,            -- JSON list
    doc_ids           TEXT,            -- JSON list
    web_used          INTEGER,
    route_trace       TEXT,            -- JSON list
    grader_scores     TEXT,            -- JSON object
    latency_ms        INTEGER,
    status            TEXT,            -- ok | degraded | error
    error             TEXT
);
"""
