"""Phase 2-3: draft an answer from the (graded) documents."""
from langchain_core.messages import AIMessage

from app.graph import prompts
from app.graph.state import GraphState
from app.services.llm import get_llm, llm_service_name
from app.services.retry import call_upstream


def format_docs(docs) -> str:
    return "\n\n".join(
        f"[{d.metadata.get('title') or d.metadata.get('source')}] "
        f"({d.metadata.get('doc_type', 'doc')})\n{d.page_content}"
        for d in docs
    )


def generate(state: GraphState) -> dict:
    context = format_docs(state.get("documents", []))
    prompt = prompts.GENERATE_PROMPT.format(context=context, question=state["question"])
    if state.get("generation_count", 0) > 0:  # regenerating after a failed grounding check
        prompt += prompts.RETRY_GENERATION_NOTE
    llm = get_llm()
    answer = call_upstream(llm_service_name(), lambda: llm.invoke(prompt)).content
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
    """Loop limits hit: never guess. If we did find relevant documents, quote them
    verbatim (grounded by construction) so the engineer still has something to act on."""
    docs = [d for d in state.get("documents", []) if d.metadata.get("doc_type") != "web"]
    if docs:
        excerpts = "\n\n".join(
            f"**From {d.metadata.get('title') or d.metadata.get('source')}**\n{d.page_content[:1200].strip()}"
            for d in docs[:2]
        )
        answer = (f"{prompts.PARTIAL_EVIDENCE}\n\n{excerpts}\n\n"
                  "**Escalation**\nIf these steps don't resolve it, escalate to the on-call lead.")
    else:
        answer = prompts.INSUFFICIENT_EVIDENCE
    return {"generation": answer, "route_trace": state.get("route_trace", []) + ["give_up"]}
