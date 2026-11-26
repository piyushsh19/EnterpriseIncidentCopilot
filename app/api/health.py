"""Phase 5: GET /health checks each dependency. ?deep=true also calls the services."""
import urllib.request

from fastapi import APIRouter

from app.config import get_settings
from app.db.session import get_conn

router = APIRouter(tags=["health"])


def _ollama_up(base_url: str) -> bool:
    try:
        urllib.request.urlopen(f"{base_url}/api/version", timeout=2)
        return True
    except Exception:
        return False


def _check(fn) -> dict:
    try:
        return {"ok": True, **(fn() or {})}
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {str(exc)[:200]}"}


@router.get("/health")
def health(deep: bool = False) -> dict:
    s = get_settings()
    checks = {}

    def sqlite():
        with get_conn() as conn:
            conn.execute("SELECT 1")
    checks["sqlite"] = _check(sqlite)

    if s.llm_provider == "ollama":
        checks["llm"] = {"ok": _ollama_up(s.ollama_base_url), "provider": "ollama"}
    else:
        checks["llm"] = {"ok": bool(s.openai_api_key), "provider": "openai"}
    checks["pinecone"] = {"ok": bool(s.pinecone_api_key)}
    checks["tavily"] = {"ok": bool(s.tavily_api_key)}

    if deep:  # real calls: a few seconds, small token cost
        from app.services.llm import get_embeddings, get_grader_llm
        from app.services.vectorstore import get_pinecone

        checks["llm"] = {"provider": s.llm_provider, **_check(
            lambda: {"reply": get_grader_llm().invoke("Reply with OK").content[:20]})}
        checks["embeddings"] = _check(lambda: {"dim": len(get_embeddings().embed_query("ping"))})
        checks["pinecone"] = _check(lambda: {"vectors": get_pinecone().Index(
            s.pinecone_index).describe_index_stats().total_vector_count})
        # Tavily: key presence only, to avoid spending search credits on health checks

    ok = all(c["ok"] for c in checks.values())
    return {"status": "ok" if ok else "degraded", "provider": s.llm_provider, "checks": checks}
