"""Phase 5: POST /api/chat runs the Self-RAG graph; history comes from the checkpointer.

Every chat call writes exactly one audit row, whether it succeeds, degrades or fails.
"""
import logging
import time

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.db.session import get_conn
from app.graph.builder import get_graph, run_incident_query
from app.services.audit import write_audit
from app.services.retry import UpstreamError

router = APIRouter(tags=["chat"])
log = logging.getLogger("chat")


class ChatIn(BaseModel):
    incident_id: str = Field(min_length=1)
    message: str = Field(min_length=1, max_length=4000)

    @field_validator("message")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("message must not be blank")
        return v.strip()


def _status(result: dict) -> str:
    """ok = grounded answer; degraded = safe fallback answer or web search failed."""
    if result.get("web_error") or "give_up" in result.get("route_trace", []):
        return "degraded"
    return "ok"


def _source(doc) -> dict:
    m = doc.metadata
    return {"title": m.get("title"), "source": m.get("source"),
            "doc_type": m.get("doc_type"), "service": m.get("service")}


@router.post("/chat")
def chat(body: ChatIn, x_user: str = Header(default="anonymous")) -> dict:
    with get_conn() as conn:
        if not conn.execute("SELECT 1 FROM incidents WHERE id=?", (body.incident_id,)).fetchone():
            raise HTTPException(404, f"Unknown incident_id '{body.incident_id}'")

    start = time.perf_counter()
    result, status, error = {}, "error", None
    try:
        result = run_incident_query(body.incident_id, body.message)
        status = _status(result)
    except UpstreamError as exc:
        error = str(exc)
        raise HTTPException(502, f"{exc.service} is unavailable, please retry. ({exc})")
    except Exception as exc:  # unexpected bug: still audited, returned as 500
        error = f"{type(exc).__name__}: {exc}"
        log.exception("chat failed")
        raise HTTPException(500, "Internal error while answering; see audit log")
    finally:
        docs = result.get("documents", [])
        write_audit(
            user=x_user, incident_id=body.incident_id, action="chat", question=body.message,
            rewritten_queries=result.get("rewritten_queries", []),
            doc_ids=[d.metadata.get("doc_id") or d.metadata.get("source") for d in docs],
            web_used=int(bool(result.get("web_used"))),
            route_trace=result.get("route_trace", []),
            grader_scores=result.get("grader_scores", {}),
            latency_ms=int((time.perf_counter() - start) * 1000),
            status=status, error=error or result.get("web_error"),
        )

    return {
        "answer": result.get("generation"),
        "status": status,
        "sources": [_source(d) for d in result.get("documents", [])],
        "web_used": bool(result.get("web_used")),
        "route_trace": result.get("route_trace", []),
        "grader_scores": result.get("grader_scores", {}),
    }


@router.get("/chat/{incident_id}/history")
def history(incident_id: str) -> list:
    with get_conn() as conn:
        if not conn.execute("SELECT 1 FROM incidents WHERE id=?", (incident_id,)).fetchone():
            raise HTTPException(404, f"Unknown incident_id '{incident_id}'")
    snap = get_graph().get_state({"configurable": {"thread_id": incident_id}})
    msgs = (snap.values or {}).get("messages", [])
    return [{"role": m.type, "content": m.content} for m in msgs]
