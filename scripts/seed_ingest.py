"""Phase 1: load every file in data/sample_runbooks into Pinecone (idempotent).

    python scripts/seed_ingest.py           # skip files already indexed
    python scripts/seed_ingest.py --force   # re-index everything (e.g. after changing metadata)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.db.session import init_db  # noqa: E402
from app.ingestion.pipeline import ingest_file  # noqa: E402
from app.services.vectorstore import ensure_index  # noqa: E402


def main() -> None:
    init_db()
    ensure_index()
    force = "--force" in sys.argv
    for path in sorted((ROOT / "data" / "sample_runbooks").iterdir()):
        if path.suffix.lower() in (".md", ".txt", ".pdf", ".docx"):
            print(path.name, "->", ingest_file(path, force=force))


if __name__ == "__main__":
    main()
