"""Phase 4: turn a follow-up ("what if that fails?") into a standalone question."""
from langchain_core.messages import HumanMessage

from app.graph import prompts
from app.graph.state import GraphState
from app.services.llm import get_grader_llm, llm_service_name
from app.services.retry import call_upstream


def contextualize(state: GraphState) -> dict:
    question = state["question"]
    history = state.get("messages", [])[:-1]  # exclude the message just added
    trace = state.get("route_trace", []) + ["contextualize"]
    reset = {"rewrite_count": 0, "generation_count": 0, "web_used": False,
             "original_question": question, "grader_scores": {},
             "rewritten_queries": [], "web_error": None}
    if not history:
        return {**reset, "route_trace": trace}

    history_text = "\n".join(f"{m.type}: {m.content}" for m in history[-6:])
    llm = get_grader_llm()
    prompt = prompts.CONTEXTUALIZE_PROMPT.format(history=history_text, question=question)
    standalone = call_upstream(llm_service_name(), lambda: llm.invoke(prompt)).content.strip()
    return {**reset, "question": standalone, "route_trace": trace}
