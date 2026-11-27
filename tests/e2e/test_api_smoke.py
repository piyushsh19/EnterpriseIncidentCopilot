"""Phase 7: end-to-end smoke tests against a RUNNING server (normally the container).

These call the real models, Pinecone and Tavily, so they are skipped unless you opt in:

    docker compose up -d
    docker compose exec copilot python scripts/seed_ingest.py
    E2E_BASE_URL=http://localhost:8000 pytest tests/e2e -v      # or: make e2e
"""
import os
import uuid

import httpx
import pytest

BASE = os.environ.get("E2E_BASE_URL")
pytestmark = pytest.mark.skipif(not BASE, reason="set E2E_BASE_URL to run end-to-end tests")

USER = {"X-User": "e2e-test"}


@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE, timeout=300, headers=USER) as c:
        yield c


@pytest.fixture(scope="module")
def incident(client):
    r = client.post("/api/incidents", json={"title": "E2E: RDS CPU at 98%", "service": "rds",
                                            "severity": "Sev2"})
    assert r.status_code == 201
    return r.json()


def test_deep_health(client):
    body = client.get("/health", params={"deep": "true"}).json()
    failing = {k: v for k, v in body["checks"].items() if not v["ok"]}
    assert body["status"] == "ok", f"failing checks: {failing}"


def test_ui_and_docs_are_served(client):
    assert "Incident Response Copilot" in client.get("/").text
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/docs").status_code == 200


def test_runbooks_are_indexed(client):
    names = {d["filename"] for d in client.get("/api/documents").json()}
    assert "runbook_rds_high_cpu.md" in names, "run scripts/seed_ingest.py inside the container"


def test_s1_chat_cites_runbook_and_writes_one_audit_row(client, incident):
    r = client.post("/api/chat", json={"incident_id": incident["id"],
                                       "message": "RDS CPU at 98%, queries slow"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["answer"]
    assert any(s["title"] == "runbook_rds_high_cpu" for s in body["sources"])
    assert body["route_trace"][0] == "contextualize" and body["route_trace"][-1] == "finalize"

    rows = client.get("/api/audit", params={"incident_id": incident["id"], "action": "chat"}).json()
    assert len(rows) == 1
    assert rows[0]["user"] == "e2e-test" and rows[0]["latency_ms"] > 0


def test_s9_follow_up_uses_memory(client, incident):
    r = client.post("/api/chat", json={"incident_id": incident["id"],
                                       "message": "what if that doesn't help?"})
    assert r.status_code == 200, r.text
    history = client.get(f"/api/chat/{incident['id']}/history").json()
    assert [m["role"] for m in history] == ["human", "ai", "human", "ai"]


def test_s14_duplicate_upload(client):
    content = f"# Runbook: E2E test\nService: e2e\n\n1. Step one ({uuid.uuid4().hex}).\n".encode()
    files = {"file": ("runbook_e2e_test.md", content)}
    first = client.post("/api/ingest", files=files).json()
    second = client.post("/api/ingest", files={"file": ("runbook_e2e_test.md", content)}).json()
    try:
        assert first["status"] in ("ingested", "updated")
        assert second["status"] == "duplicate"
    finally:  # keep the shared Pinecone index clean
        assert client.delete(f"/api/documents/{first['doc_id']}").status_code == 200


def test_s9b_short_follow_up_keeps_the_incident_topic(client, incident):
    r = client.post("/api/chat", json={"incident_id": incident["id"], "message": "who should I page?"})
    assert r.status_code == 200, r.text
    titles = [s["title"] for s in r.json()["sources"]]
    assert "runbook_rds_high_cpu" in titles, titles


def test_s16_s19_bad_requests(client, incident):
    assert client.post("/api/ingest", files={"file": ("x.exe", b"MZ")}).status_code == 400
    assert client.post("/api/chat", json={"incident_id": "INC-nope", "message": "hi"}).status_code == 404
    assert client.post("/api/chat", json={"incident_id": incident["id"], "message": " "}).status_code == 422
