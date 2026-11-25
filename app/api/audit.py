"""Phase 5: read the audit trail (filter by incident or status)."""
from typing import Optional

from fastapi import APIRouter

from app.db.session import get_conn

router = APIRouter(tags=["audit"])


@router.get("/audit")
def audit(incident_id: Optional[str] = None, status: Optional[str] = None, limit: int = 100) -> list:
    sql, args = "SELECT * FROM audit_log WHERE 1=1", []
    if incident_id:
        sql += " AND incident_id=?"; args.append(incident_id)
    if status:
        sql += " AND status=?"; args.append(status)
    sql += " ORDER BY id DESC LIMIT ?"; args.append(limit)
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(sql, args)]
