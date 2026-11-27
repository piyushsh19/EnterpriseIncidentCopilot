"""Phase 5: API behaviour with the graph and ingestion mocked (scenarios S13-S20)."""
import pytest
from fastapi.testclient import TestClient
from langchain_core.documents import Document

from app.api import chat as chat_api
from app.api import ingest as ingest_api
from app.main import app
from app.services.retry import UpstreamError

DOC = Document(page_content="x", metadata={"doc_id": "abc123", "title": "runbook_rds_high_cpu",
                                            "doc_type": "runbook", "service": "rds"})


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def incident(client):
    return client.post("/api/incidents", json={"title": "RDS CPU 98%", "service": "rds",
                                               "severity": "Sev2"}).json()


def fake_result(**over):
    r = {"generation": "**Probable cause** ...", "documents": [DOC], "web_used": False,
         "route_trace": ["contextualize", "retrieve", "grade_documents", "generate",
                         "check_answer", "finalize"],
         "grader_scores": {"relevant_docs": 1, "grounded": True, "useful": True},
         "rewritten_queries": []}
    r.update(over)
    return r


def chat_audit_rows(client, incident_id):
    return client.get(f"/api/audit?incident_id={incident_id}&action=chat").json()


def test_health(client):
    body = client.get("/health").json()
    assert body["checks"]["sqlite"]["ok"] is True
    assert "llm" in body["checks"]


def test_incident_crud(client, incident):
    assert incident["id"].startswith("INC-") and incident["status"] == "open"
    assert client.get(f"/api/incidents/{incident['id']}").json()["title"] == "RDS CPU 98%"
    upd = client.patch(f"/api/incidents/{incident['id']}", json={"status": "mitigated"}).json()
    assert upd["status"] == "mitigated"
    assert any(i["id"] == incident["id"] for i in client.get("/api/incidents?status=mitigated").json())


def test_incident_validation(client):
    assert client.post("/api/incidents", json={"title": "x"}).status_code == 422
    assert client.post("/api/incidents", json={"title": "abc", "severity": "Sev9"}).status_code == 422
    assert client.get("/api/incidents/INC-nope").status_code == 404


def test_s20_chat_ok_writes_exactly_one_audit_row(client, incident, monkeypatch):
    monkeypatch.setattr(chat_api, "run_incident_query", lambda i, m: fake_result())
    r = client.post("/api/chat", json={"incident_id": incident["id"], "message": "RDS CPU at 98%"},
                    headers={"X-User": "alice"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok" and body["sources"][0]["title"] == "runbook_rds_high_cpu"

    rows = chat_audit_rows(client, incident["id"])
    assert len(rows) == 1
    row = rows[0]
    assert row["user"] == "alice" and row["status"] == "ok"
    assert row["doc_ids"] == ["abc123"]
    assert row["route_trace"][-1] == "finalize"
    assert row["grader_scores"]["grounded"] is True
    assert row["latency_ms"] >= 0


def test_s8_degraded_when_web_fails(client, incident, monkeypatch):
    monkeypatch.setattr(chat_api, "run_incident_query", lambda i, m: fake_result(
        documents=[], web_used=True, web_error="Tavily failed: 503",
        route_trace=["contextualize", "web_search", "give_up", "finalize"]))
    body = client.post("/api/chat", json={"incident_id": incident["id"], "message": "AFD 502"}).json()
    assert body["status"] == "degraded"
    row = chat_audit_rows(client, incident["id"])[0]
    assert row["status"] == "degraded" and "Tavily" in row["error"]


def test_s17_s18_upstream_failure_is_502_and_audited(client, incident, monkeypatch):
    def boom(i, m):
        raise UpstreamError("Pinecone", TimeoutError("read timed out"))
    monkeypatch.setattr(chat_api, "run_incident_query", boom)
    r = client.post("/api/chat", json={"incident_id": incident["id"], "message": "RDS CPU"})
    assert r.status_code == 502 and "Pinecone" in r.json()["detail"]
    rows = chat_audit_rows(client, incident["id"])
    assert len(rows) == 1 and rows[0]["status"] == "error" and "timed out" in rows[0]["error"]


def test_s19_invalid_chat_requests(client, incident):
    assert client.post("/api/chat", json={"incident_id": incident["id"], "message": ""}).status_code == 422
    assert client.post("/api/chat", json={"incident_id": incident["id"], "message": "   "}).status_code == 422
    assert client.post("/api/chat", json={"incident_id": "INC-nope", "message": "hi"}).status_code == 404
    assert client.get("/api/chat/INC-nope/history").status_code == 404


def test_s13_ingest_supported_file(client, monkeypatch):
    monkeypatch.setattr(ingest_api, "ingest_file",
                        lambda path, service=None, doc_type=None: {"doc_id": "d1", "status": "ingested", "chunks": 2})
    r = client.post("/api/ingest", files={"file": ("runbook_x.md", b"# Runbook\nService: x\nsteps")})
    assert r.status_code == 200 and r.json()["status"] == "ingested"
    assert client.get("/api/audit?action=ingest").json()[0]["doc_ids"] == ["d1"]


def test_s14_duplicate_upload(client, monkeypatch):
    monkeypatch.setattr(ingest_api, "ingest_file",
                        lambda path, service=None, doc_type=None: {"doc_id": "d1", "status": "duplicate"})
    r = client.post("/api/ingest", files={"file": ("runbook_x.md", b"same content")})
    assert r.json()["status"] == "duplicate"


def test_s16_bad_files_rejected(client, monkeypatch):
    assert client.post("/api/ingest", files={"file": ("evil.exe", b"MZ")}).status_code == 400
    assert client.post("/api/ingest", files={"file": ("empty.md", b"")}).status_code == 400
    big = b"x" * (10 * 1024 * 1024 + 1)
    assert client.post("/api/ingest", files={"file": ("big.txt", big)}).status_code == 413

    def no_text(path, service=None, doc_type=None):
        raise ValueError("No extractable text (empty or scanned file)")
    monkeypatch.setattr(ingest_api, "ingest_file", no_text)
    r = client.post("/api/ingest", files={"file": ("scan.pdf", b"%PDF-1.4")})
    assert r.status_code == 400 and "No extractable text" in r.json()["detail"]


def test_delete_document(client, monkeypatch):
    monkeypatch.setattr(ingest_api, "delete_document", lambda doc_id: doc_id == "d1")
    assert client.delete("/api/documents/d1").json()["status"] == "deleted"
    assert client.delete("/api/documents/nope").status_code == 404
