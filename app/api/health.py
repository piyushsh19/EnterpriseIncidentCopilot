"""Phase 5: GET /health — checks each dependency."""
from fastapi import APIRouter

from app.config import get_settings
from app.db.session import get_conn

router = APIRouter(tags=["health"])


def _ollama_up(base_url: str) -> bool:
    import urllib.request
    try:
        urllib.request.urlopen(f"{base_url}/api/version", timeout=2)
        return True
    except Exception:
        return False


@router.get("/health")
def health() -> dict:
    s = get_settings()
    checks = {
        "llm": _ollama_up(s.ollama_base_url) if s.llm_provider == "ollama" else bool(s.openai_api_key),
        "pinecone_key": bool(s.pinecone_api_key),
        "tavily_key": bool(s.tavily_api_key),
    }
    try:
        with get_conn() as conn:
            conn.execute("SELECT 1")
        checks["sqlite"] = True
    except Exception:
        checks["sqlite"] = False
    # TODO Phase 5: ping Pinecone index stats and a tiny OpenAI call when ?deep=true
    return {"status": "ok" if all(checks.values()) else "degraded", "checks": checks}
