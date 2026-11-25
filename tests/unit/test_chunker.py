from app.ingestion.chunker import chunk


def test_chunks_carry_metadata():
    docs = chunk("word " * 2000, {"doc_id": "abc"})
    assert len(docs) > 1
    assert docs[0].metadata["doc_id"] == "abc"
    assert docs[1].metadata["chunk_index"] == 1
