"""Phase 3: run the real compiled graph with fake models and assert the path it takes.

Each test maps to a scenario in the plan's test matrix (S1-S9). Nothing here calls
Ollama, OpenAI, Pinecone or Tavily, so the tests are fast and deterministic.
"""
from types import SimpleNamespace

import pytest
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver

from app.graph import edges
from app.graph.builder import build_workflow
from app.graph.nodes import contextualize, generate, grade_documents, retrieve, transform_query
from app.graph.prompts import INSUFFICIENT_EVIDENCE

RDS = Document(page_content="RDS high CPU: check Top SQL", metadata={"title": "runbook_rds_high_cpu", "doc_type": "runbook"})
K8S = Document(page_content="CrashLoopBackOff: kubectl logs --previous", metadata={"title": "runbook_k8s", "doc_type": "runbook"})
REDIS = Document(page_content="Redis eviction", metadata={"title": "runbook_redis", "doc_type": "runbook"})


class FakeLLM:
    """Returns canned replies in order; records every prompt it was given."""

    def __init__(self, replies):
        self.replies, self.prompts = list(replies), []

    def invoke(self, prompt):
        self.prompts.append(prompt)
        return SimpleNamespace(content=self.replies.pop(0) if self.replies else "answer")


class Fakes:
    def __init__(self, monkeypatch):
        self.mp = monkeypatch
        self.retrieved = [RDS]          # what retrieve returns
        self.relevant = lambda q, doc: True
        self.grounded = [True]          # one verdict per generation
        self.useful = [True]
        self.web_results = [{"url": "https://example.com/afd", "title": "AFD 502", "content": "Check origin health"}]
        self.web_calls = 0
        self.gen_llm = FakeLLM([])
        self.aux_llm = FakeLLM([])      # contextualize + transform_query

        mp = monkeypatch
        mp.setattr(retrieve, "get_retriever", lambda: SimpleNamespace(invoke=lambda q: list(self.retrieved)))
        mp.setattr(grade_documents, "grade_relevance", lambda q, d: self.relevant(q, d))
        mp.setattr(generate, "get_llm", lambda: self.gen_llm)
        mp.setattr(transform_query, "get_grader_llm", lambda: self.aux_llm)
        mp.setattr(contextualize, "get_grader_llm", lambda: self.aux_llm)
        mp.setattr(edges, "grade_hallucination", lambda d, g: self._next(self.grounded))
        mp.setattr(edges, "grade_usefulness", lambda q, g: self._next(self.useful))

        fakes = self

        class FakeTavily:
            def __init__(self, api_key=None):
                pass

            def search(self, q, max_results=3):
                fakes.web_calls += 1
                if isinstance(fakes.web_results, Exception):
                    raise fakes.web_results
                return {"results": fakes.web_results}

        import tavily
        mp.setattr(tavily, "TavilyClient", FakeTavily)

    @staticmethod
    def _next(seq):
        return seq.pop(0) if len(seq) > 1 else seq[0]


@pytest.fixture
def fakes(monkeypatch):
    return Fakes(monkeypatch)


@pytest.fixture
def graph():
    return build_workflow().compile(checkpointer=MemorySaver())


def ask(graph, question, thread="INC-test"):
    return graph.invoke(
        {"question": question, "messages": [HumanMessage(content=question)], "route_trace": []},
        config={"configurable": {"thread_id": thread}},
    )


def test_s1_happy_path(fakes, graph):
    r = ask(graph, "RDS CPU at 98%")
    assert r["route_trace"] == ["contextualize", "retrieve", "grade_documents",
                                "generate", "check_answer", "finalize"]
    assert r["web_used"] is False
    assert r["grader_scores"]["grounded"] and r["grader_scores"]["useful"]


def test_s2_irrelevant_chunks_dropped(fakes, graph):
    fakes.retrieved = [K8S, REDIS]
    fakes.relevant = lambda q, d: "CrashLoop" in d
    r = ask(graph, "Pods restarting after deploy")
    assert [d.metadata["title"] for d in r["documents"]] == ["runbook_k8s"]
    assert r["grader_scores"]["relevant_docs"] == 1


def test_s3_rewrite_then_success(fakes, graph):
    fakes.aux_llm = FakeLLM(["database high CPU troubleshooting"])
    fakes.relevant = lambda q, d: "database" in q   # only the rewritten query matches
    r = ask(graph, "db is cooked")
    assert r["route_trace"][:6] == ["contextualize", "retrieve", "grade_documents",
                                    "transform_query", "retrieve", "grade_documents"]
    assert r["route_trace"][-1] == "finalize"
    assert r["rewrite_count"] == 1 and r["web_used"] is False


def test_s4_web_fallback_after_max_rewrites(fakes, graph):
    fakes.relevant = lambda q, d: False
    r = ask(graph, "Azure Front Door 502 errors")
    assert r["route_trace"].count("transform_query") == 2
    assert "web_search" in r["route_trace"]
    assert r["web_used"] is True
    assert r["documents"][0].metadata["doc_type"] == "web"


def test_s5_hallucination_regenerates(fakes, graph):
    fakes.grounded = [False, True]
    r = ask(graph, "RDS CPU at 98%")
    assert r["route_trace"].count("generate") == 2
    assert r["generation_count"] == 2
    assert r["grader_scores"]["answer_checks"][0]["grounded"] is False


def test_s6_grounded_but_not_useful_rewrites(fakes, graph):
    fakes.useful = [False, True]
    r = ask(graph, "RDS CPU at 98%")
    trace = r["route_trace"]
    assert trace.index("transform_query") > trace.index("check_answer")
    assert trace[-1] == "finalize"


def test_s7_loop_limits_give_safe_answer(fakes, graph):
    fakes.grounded = [False]   # never grounded
    r = ask(graph, "RDS CPU at 98%")
    assert r["generation_count"] == 3
    assert "give_up" in r["route_trace"]
    assert r["generation"] == INSUFFICIENT_EVIDENCE


def test_s8_web_search_fails_safely(fakes, graph):
    fakes.relevant = lambda q, d: False
    fakes.web_results = RuntimeError("Tavily 503")
    r = ask(graph, "Azure Front Door 502 errors")
    assert r["route_trace"][-2:] == ["give_up", "finalize"]
    assert r["generation"] == INSUFFICIENT_EVIDENCE


def test_s9_follow_up_is_contextualized_with_memory(fakes, graph):
    ask(graph, "RDS CPU at 98%", thread="INC-mem")
    fakes.aux_llm = FakeLLM(["What if RDS CPU stays high after the runbook steps?"])
    r = ask(graph, "what if that doesn't help?", thread="INC-mem")
    assert r["question"] == "What if RDS CPU stays high after the runbook steps?"
    assert "RDS CPU at 98%" in fakes.aux_llm.prompts[0]      # history was passed in
    assert len(r["messages"]) == 4                            # 2 questions + 2 answers


def test_s11_incidents_are_isolated(fakes, graph):
    ask(graph, "RDS CPU at 98%", thread="INC-a")
    r = ask(graph, "Pods restarting", thread="INC-b")
    assert len(r["messages"]) == 2
    assert fakes.aux_llm.prompts == []   # no history -> contextualize skipped the LLM
