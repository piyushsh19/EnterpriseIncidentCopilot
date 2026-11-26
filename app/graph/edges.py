"""Phase 3: the grading node and conditional routers that make the graph self-correcting."""
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


def after_web_search(state: GraphState) -> str:
    """Web search returned nothing (or failed): don't let the model answer from no context."""
    return "generate" if state.get("documents") else "give_up"


def check_answer(state: GraphState) -> dict:
    """Node: run the hallucination and usefulness graders and store the verdicts in state,
    so the router can read them and the audit log can record them."""
    grounded = grade_hallucination(format_docs(state.get("documents", [])), state["generation"])
    useful = False
    if grounded:  # no point checking usefulness of an ungrounded answer
        question = state.get("original_question") or state["question"]
        useful = grade_usefulness(question, state["generation"])

    scores = dict(state.get("grader_scores", {}))
    history = scores.get("answer_checks", []) + [{"grounded": grounded, "useful": useful}]
    scores.update({"grounded": grounded, "useful": useful, "answer_checks": history})
    return {"grader_scores": scores, "route_trace": state.get("route_trace", []) + ["check_answer"]}


def grade_generation(state: GraphState) -> str:
    """Router after check_answer: accept, regenerate, rewrite, or give up."""
    s = get_settings()
    scores = state.get("grader_scores", {})
    tries_left = state.get("generation_count", 0) < s.max_generations

    if not scores.get("grounded"):
        return "generate" if tries_left else "give_up"
    if scores.get("useful"):
        return "useful"
    if tries_left and state.get("rewrite_count", 0) < s.max_rewrites:
        return "transform_query"
    return "give_up"
