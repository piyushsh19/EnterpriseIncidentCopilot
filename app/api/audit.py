"""Phase 5: read the audit trail (filter by incident or status)."""
from typing import Optional

import json

from fastapi import APIRouter, Query

from app.db.session import get_conn

router = APIRouter(tags=["audit"])


@router.get("/audit")
def audit(incident_id: Optional[str] = None, status: Optional[str] = None,
          action: Optional[str] = None, limit: int = Query(100, ge=1, le=1000)) -> list:
    sql, args = "SELECT * FROM audit_log WHERE 1=1", []
    if incident_id:
        sql += " AND incident_id=?"; args.append(incident_id)
    if action:
        sql += " AND action=?"; args.append(action)
    if status:
        sql += " AND status=?"; args.append(status)
    sql += " ORDER BY id DESC LIMIT ?"; args.append(limit)
    with get_conn() as conn:
        rows = [dict(r) for r in conn.execute(sql, args)]
    for r in rows:  # JSON columns back to lists / objects
        for key in ("rewritten_queries", "doc_ids", "route_trace", "grader_scores"):
            if r.get(key):
                r[key] = json.loads(r[key])
    return rows
