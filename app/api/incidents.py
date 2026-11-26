"""Phase 5: create, list, read and update incidents (incident id = LangGraph thread_id)."""
import uuid
from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.db.session import get_conn
from app.services.audit import write_audit

router = APIRouter(tags=["incidents"])

Severity = Literal["Sev1", "Sev2", "Sev3", "Sev4"]
Status = Literal["open", "investigating", "mitigated", "resolved"]


class IncidentIn(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    service: Optional[str] = Field(default=None, max_length=50)
    severity: Severity = "Sev3"


class IncidentPatch(BaseModel):
    status: Optional[Status] = None
    severity: Optional[Severity] = None


def _get(incident_id: str) -> dict:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM incidents WHERE id=?", (incident_id,)).fetchone()
    if not row:
        raise HTTPException(404, f"Unknown incident_id '{incident_id}'")
    return dict(row)


@router.post("/incidents", status_code=201)
def create_incident(body: IncidentIn, x_user: str = Header(default="anonymous")) -> dict:
    row = {"id": f"INC-{uuid.uuid4().hex[:8]}", **body.model_dump(),
           "status": "open", "created_at": datetime.now(timezone.utc).isoformat()}
    with get_conn() as conn:
        conn.execute("INSERT INTO incidents VALUES (:id,:title,:service,:severity,:status,:created_at)", row)
    write_audit(user=x_user, incident_id=row["id"], action="incident_create",
                question=row["title"], status="ok")
    return row


@router.get("/incidents")
def list_incidents(status: Optional[Status] = None) -> list:
    sql, args = "SELECT * FROM incidents", []
    if status:
        sql += " WHERE status=?"; args.append(status)
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(sql + " ORDER BY created_at DESC", args)]


@router.get("/incidents/{incident_id}")
def get_incident(incident_id: str) -> dict:
    return _get(incident_id)


@router.patch("/incidents/{incident_id}")
def update_incident(incident_id: str, body: IncidentPatch,
                    x_user: str = Header(default="anonymous")) -> dict:
    _get(incident_id)
    changes = body.model_dump(exclude_none=True)
    if not changes:
        raise HTTPException(400, "Nothing to update: send status and/or severity")
    sets = ", ".join(f"{k}=?" for k in changes)
    with get_conn() as conn:
        conn.execute(f"UPDATE incidents SET {sets} WHERE id=?", [*changes.values(), incident_id])
    write_audit(user=x_user, incident_id=incident_id, action="incident_update",
                question=str(changes), status="ok")
    return _get(incident_id)
