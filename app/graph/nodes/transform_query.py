"""Phase 3: rewrite a weak query for better retrieval."""
from app.graph import prompts
from app.graph.state import GraphState
from app.services.llm import get_grader_llm


def transform_query(state: GraphState) -> dict:
    better = get_grader_llm().invoke(prompts.REWRITE_PROMPT.format(question=state["question"])).content
    return {
        "question": better.strip(),
        "rewrite_count": state.get("rewrite_count", 0) + 1,
        "route_trace": state.get("route_trace", []) + ["transform_query"],
    }
