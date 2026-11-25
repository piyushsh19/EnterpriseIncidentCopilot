"""Phase 2-3: draft an answer from the (graded) documents."""
from langchain_core.messages import AIMessage

from app.graph import prompts
from app.graph.state import GraphState
from app.services.llm import get_llm


def format_docs(docs) -> str:
    return "\n\n".join(
        f"[{d.metadata.get('title') or d.metadata.get('source')}] "
        f"({d.metadata.get('doc_type', 'doc')})\n{d.page_content}"
        for d in docs
    )


def generate(state: GraphState) -> dict:
    context = format_docs(state.get("documents", []))
    answer = get_llm().invoke(
        prompts.GENERATE_PROMPT.format(context=context, question=state["question"])
    ).content
    return {
        "generation": answer,
        "generation_count": state.get("generation_count", 0) + 1,
        "route_trace": state.get("route_trace", []) + ["generate"],
    }


def finalize(state: GraphState) -> dict:
    """Write the final answer into chat memory."""
    return {"messages": [AIMessage(content=state.get("generation", ""))],
            "route_trace": state.get("route_trace", []) + ["finalize"]}


def give_up(state: GraphState) -> dict:
    """Loop limits hit: return a safe answer instead of a guess."""
    return {"generation": prompts.INSUFFICIENT_EVIDENCE,
            "route_trace": state.get("route_trace", []) + ["give_up"]}
