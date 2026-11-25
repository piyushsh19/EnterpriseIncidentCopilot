"""Phase 3: conditional routers that make the graph self-correcting."""
from app.config import get_settings
from app.graph.nodes.generate import format_docs
from app.graph.nodes.graders import grade_hallucination, grade_usefulness
from app.graph.state import GraphState


def decide_to_generate(state: GraphState) -> str:
    """After grading docs: generate, rewrite, go to the web, or give up."""
    s = get_settings()
    if len(state.get("documents", [])) >= s.relevance_min_docs:
        return "generate"
    if state.get("rewrite_count", 0) < s.max_rewrites:
        return "transform_query"
    if not state.get("web_used"):
        return "web_search"
    return "give_up"


def grade_generation(state: GraphState) -> str:
    """After generating: accept, regenerate, rewrite, or give up."""
    s = get_settings()
    tries_left = state.get("generation_count", 0) < s.max_generations

    grounded = grade_hallucination(format_docs(state.get("documents", [])), state["generation"])
    if not grounded:
        return "generate" if tries_left else "give_up"

    question = state.get("original_question") or state["question"]
    if grade_usefulness(question, state["generation"]):
        return "useful"
    if tries_left and state.get("rewrite_count", 0) < s.max_rewrites:
        return "transform_query"
    return "give_up"
