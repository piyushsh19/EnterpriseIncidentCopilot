"""Phase 0 done-check: embed 'hello', upsert to Pinecone, query it back."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings  # noqa: E402
from app.services.llm import get_embeddings  # noqa: E402
from app.services.vectorstore import ensure_index, get_pinecone  # noqa: E402


def main() -> None:
    s = get_settings()
    ensure_index()
    vec = get_embeddings().embed_query("hello")
    print(f"Embedding OK, dim={len(vec)}")
    index = get_pinecone().Index(s.pinecone_index)
    index.upsert(vectors=[{"id": "setup-check", "values": vec}], namespace="setup")
    res = index.query(vector=vec, top_k=1, namespace="setup")
    print("Pinecone OK, match:", res["matches"][0]["id"] if res["matches"] else None)
    index.delete(ids=["setup-check"], namespace="setup")


if __name__ == "__main__":
    main()
