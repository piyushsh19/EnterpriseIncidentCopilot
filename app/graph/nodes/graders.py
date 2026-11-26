"""Phase 3: structured yes/no graders (relevance, hallucination, usefulness)."""
from pydantic import BaseModel, Field

from app.graph import prompts
from app.services.llm import get_grader_llm, llm_service_name
from app.services.retry import call_upstream


class BinaryScore(BaseModel):
    binary_score: str = Field(description="'yes' or 'no'")


def _grade(prompt: str) -> bool:
    llm = get_grader_llm().with_structured_output(BinaryScore)
    result = call_upstream(llm_service_name(), lambda: llm.invoke(prompt))
    return result.binary_score.strip().lower() == "yes"


def grade_relevance(question: str, document: str) -> bool:
    return _grade(prompts.GRADE_DOCUMENT_PROMPT.format(question=question, document=document))


def grade_hallucination(documents: str, generation: str) -> bool:
    """True = grounded in the documents."""
    return _grade(prompts.HALLUCINATION_PROMPT.format(documents=documents, generation=generation))


def grade_usefulness(question: str, generation: str) -> bool:
    """True = answer addresses the question."""
    return _grade(prompts.ANSWER_USEFULNESS_PROMPT.format(question=question, generation=generation))
