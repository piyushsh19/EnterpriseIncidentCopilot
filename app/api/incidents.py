"""Phase 5: create and list incidents (incident id = LangGraph thread_id)."""
import uuid
from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.db.session import get_conn

router = APIRouter(tags=["incidents"])


class IncidentIn(BaseModel):
    title: str = Field(min_length=3)
    service: Optional[str] = None
    severity: Literal["Sev1", "Sev2", "Sev3", "Sev4"] = "Sev3"


@router.post("/incidents", status_code=201)
def create_incident(body: IncidentIn) -> dict:
    row = {"id": f"INC-{uuid.uuid4().hex[:8]}", **body.model_dump(),
           "status": "open", "created_at": datetime.now(timezone.utc).isoformat()}
    with get_conn() as conn:
        conn.execute("INSERT INTO incidents VALUES (:id,:title,:service,:severity,:status,:created_at)", row)
    return row


@router.get("/incidents")
def list_incidents() -> list:
    with get_conn() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM incidents ORDER BY created_at DESC")]
