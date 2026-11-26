"""Phase 4: turn a follow-up ("what if that fails?") into a standalone question."""
from langchain_core.messages import HumanMessage

from app.graph import prompts
from app.graph.state import GraphState
from app.services.llm import get_grader_llm


def contextualize(state: GraphState) -> dict:
    question = state["question"]
    history = state.get("messages", [])[:-1]  # exclude the message just added
    trace = state.get("route_trace", []) + ["contextualize"]
    reset = {"rewrite_count": 0, "generation_count": 0, "web_used": False,
             "original_question": question, "grader_scores": {}}
    if not history:
        return {**reset, "route_trace": trace}

    history_text = "\n".join(f"{m.type}: {m.content}" for m in history[-6:])
    standalone = get_grader_llm().invoke(
        prompts.CONTEXTUALIZE_PROMPT.format(history=history_text, question=question)
    ).content
    return {**reset, "question": standalone, "route_trace": trace}
