"""Phase 7: router logic with graders mocked (scenarios S3, S4, S5, S7)."""
from langchain_core.documents import Document

from app.graph import edges


def test_generate_when_relevant_docs():
    assert edges.decide_to_generate({"documents": [Document(page_content="x")]}) == "generate"


def test_rewrite_when_no_docs():
    assert edges.decide_to_generate({"documents": [], "rewrite_count": 0}) == "transform_query"


def test_web_after_max_rewrites():
    assert edges.decide_to_generate({"documents": [], "rewrite_count": 2}) == "web_search"


def test_give_up_after_web():
    assert edges.decide_to_generate({"documents": [], "rewrite_count": 2, "web_used": True}) == "give_up"


def test_regenerate_on_hallucination(monkeypatch):
    monkeypatch.setattr(edges, "grade_hallucination", lambda d, g: False)
    assert edges.grade_generation({"generation": "x", "generation_count": 1}) == "generate"


def test_give_up_at_generation_limit(monkeypatch):
    monkeypatch.setattr(edges, "grade_hallucination", lambda d, g: False)
    assert edges.grade_generation({"generation": "x", "generation_count": 3}) == "give_up"


def test_useful_answer_ends(monkeypatch):
    monkeypatch.setattr(edges, "grade_hallucination", lambda d, g: True)
    monkeypatch.setattr(edges, "grade_usefulness", lambda q, g: True)
    assert edges.grade_generation({"question": "q", "generation": "x", "generation_count": 1}) == "useful"
