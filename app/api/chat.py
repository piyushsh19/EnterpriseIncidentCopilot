"""Phase 5: POST /api/chat runs the Self-RAG graph; history comes from the checkpointer."""
import time

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.db.session import get_conn
from app.graph.builder import get_graph, run_incident_query
from app.services.audit import write_audit

router = APIRouter(tags=["chat"])


class ChatIn(BaseModel):
    incident_id: str
    message: str = Field(min_length=1)


@router.post("/chat")
def chat(body: ChatIn, x_user: str = Header(default="anonymous")) -> dict:
    with get_conn() as conn:
        if not conn.execute("SELECT 1 FROM incidents WHERE id=?", (body.incident_id,)).fetchone():
            raise HTTPException(404, "Unknown incident_id")

    start = time.perf_counter()
    status, error, result = "ok", None, {}
    try:
        result = run_incident_query(body.incident_id, body.message)
        if result.get("web_used") and "give_up" in result.get("route_trace", []):
            status = "degraded"
    except Exception as exc:  # upstream failure (OpenAI / Pinecone / Tavily)
        status, error = "error", str(exc)
        raise HTTPException(502, f"Upstream service failed: {exc}")
    finally:
        docs = result.get("documents", [])
        write_audit(
            user=x_user, incident_id=body.incident_id, action="chat", question=body.message,
            rewritten_queries=[result.get("question")] if result.get("rewrite_count") else [],
            doc_ids=[d.metadata.get("doc_id") or d.metadata.get("source") for d in docs],
            web_used=int(bool(result.get("web_used"))),
            route_trace=result.get("route_trace", []),
            grader_scores=result.get("grader_scores", {}),
            latency_ms=int((time.perf_counter() - start) * 1000),
            status=status, error=error,
        )

    return {
        "answer": result.get("generation"),
        "sources": [{"title": d.metadata.get("title"), "source": d.metadata.get("source"),
                     "doc_type": d.metadata.get("doc_type")} for d in docs],
        "web_used": result.get("web_used", False),
        "route_trace": result.get("route_trace", []),
    }


@router.get("/chat/{incident_id}/history")
def history(incident_id: str) -> list:
    snap = get_graph().get_state({"configurable": {"thread_id": incident_id}})
    msgs = (snap.values or {}).get("messages", [])
    return [{"role": m.type, "content": m.content} for m in msgs]
