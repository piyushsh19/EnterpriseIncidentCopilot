"""Phase 3: router logic in isolation (no models needed)."""
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


def _state(grounded, useful, gen_count=1, rewrites=0):
    return {"grader_scores": {"grounded": grounded, "useful": useful},
            "generation_count": gen_count, "rewrite_count": rewrites}


def test_regenerate_on_hallucination():
    assert edges.grade_generation(_state(False, False)) == "generate"


def test_give_up_at_generation_limit():
    assert edges.grade_generation(_state(False, False, gen_count=3)) == "give_up"


def test_useful_answer_ends():
    assert edges.grade_generation(_state(True, True)) == "useful"


def test_not_useful_rewrites():
    assert edges.grade_generation(_state(True, False)) == "transform_query"


def test_not_useful_and_no_rewrites_left_gives_up():
    assert edges.grade_generation(_state(True, False, rewrites=2)) == "give_up"


def test_check_answer_records_scores(monkeypatch):
    monkeypatch.setattr(edges, "grade_hallucination", lambda d, g: True)
    monkeypatch.setattr(edges, "grade_usefulness", lambda q, g: False)
    out = edges.check_answer({"question": "q", "generation": "a", "documents": []})
    assert out["grader_scores"]["grounded"] is True
    assert out["grader_scores"]["useful"] is False
    assert out["route_trace"] == ["check_answer"]
