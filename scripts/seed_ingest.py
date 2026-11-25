"""Phase 1: load every file in data/sample_runbooks into Pinecone (idempotent)."""
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
    for path in sorted((ROOT / "data" / "sample_runbooks").iterdir()):
        if path.suffix.lower() in (".md", ".txt", ".pdf", ".docx"):
            service = path.stem.split("_")[1] if path.stem.count("_") >= 2 else None
            print(path.name, "->", ingest_file(path, service=service))


if __name__ == "__main__":
    main()
