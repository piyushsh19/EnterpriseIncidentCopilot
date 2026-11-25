"""Phase 3: keep only the chunks the grader says are relevant."""
from app.graph.nodes.graders import grade_relevance
from app.graph.state import GraphState


def grade_documents(state: GraphState) -> dict:
    question = state["question"]
    relevant = [d for d in state.get("documents", []) if grade_relevance(question, d.page_content)]
    scores = {**state.get("grader_scores", {}), "relevant_docs": len(relevant)}
    return {
        "documents": relevant,
        "grader_scores": scores,
        "route_trace": state.get("route_trace", []) + ["grade_documents"],
    }
