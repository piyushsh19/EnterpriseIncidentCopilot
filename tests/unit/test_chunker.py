from app.ingestion.chunker import chunk


def test_chunks_carry_metadata():
    docs = chunk("word " * 2000, {"doc_id": "abc"})
    assert len(docs) > 1
    assert docs[0].metadata["doc_id"] == "abc"
    assert docs[1].metadata["chunk_index"] == 1


def test_detect_service_from_header():
    from app.ingestion.pipeline import detect_service
    assert detect_service("# Runbook\nService: rds | Severity: Sev2\n") == "rds"
    assert detect_service("# SOP with no service line") is None
