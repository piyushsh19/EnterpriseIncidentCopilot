"""Phase 4: Tavily fallback when internal docs don't cover the incident."""
from langchain_core.documents import Document

from app.config import get_settings
from app.graph.state import GraphState
from app.services.retry import UpstreamError, call_upstream


def web_search(state: GraphState) -> dict:
    from tavily import TavilyClient

    s = get_settings()
    trace = state.get("route_trace", []) + ["web_search"]
    web_error = None
    try:
        client = TavilyClient(api_key=s.tavily_api_key)
        results = call_upstream(
            "Tavily", lambda: client.search(state["question"], max_results=s.web_results)
        ).get("results", [])
    except UpstreamError as exc:  # don't fail the request: the graph gives a safe answer
        results, web_error = [], str(exc)

    docs = [
        Document(page_content=r.get("content", ""),
                 metadata={"source": r.get("url"), "title": r.get("title"), "doc_type": "web"})
        for r in results
    ]
    return {"documents": docs, "web_used": True, "web_error": web_error, "route_trace": trace}
