"""Phase 5: GET /health — checks each dependency."""
from fastapi import APIRouter

from app.config import get_settings
from app.db.session import get_conn

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    s = get_settings()
    checks = {
        "openai_key": bool(s.openai_api_key),
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
