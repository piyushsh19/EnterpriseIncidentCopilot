"""Phase 3: rewrite a weak query for better retrieval."""
from app.graph import prompts
from app.graph.state import GraphState
from app.services.llm import get_grader_llm, llm_service_name
from app.services.retry import call_upstream


def transform_query(state: GraphState) -> dict:
    llm = get_grader_llm()
    prompt = prompts.REWRITE_PROMPT.format(question=state["question"])
    better = call_upstream(llm_service_name(), lambda: llm.invoke(prompt)).content.strip()
    return {
        "question": better,
        "rewritten_queries": state.get("rewritten_queries", []) + [better],
        "rewrite_count": state.get("rewrite_count", 0) + 1,
        "route_trace": state.get("route_trace", []) + ["transform_query"],
    }
