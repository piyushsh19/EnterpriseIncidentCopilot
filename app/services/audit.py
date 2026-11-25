"""Phase 5: one audit row per request (SQLite) + one JSON log line."""
import json
import logging
from datetime import datetime, timezone

from app.db.session import get_conn

log = logging.getLogger("audit")


def write_audit(**row) -> None:
    row.setdefault("ts", datetime.now(timezone.utc).isoformat())
    for key in ("route_trace", "doc_ids", "grader_scores", "rewritten_queries"):
        if key in row and not isinstance(row[key], str):
            row[key] = json.dumps(row[key])
    cols = ", ".join(row)
    marks = ", ".join("?" for _ in row)
    with get_conn() as conn:
        conn.execute(f"INSERT INTO audit_log ({cols}) VALUES ({marks})", list(row.values()))
    log.info(json.dumps(row, default=str))
