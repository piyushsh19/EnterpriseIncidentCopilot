"""Phase 1: hash -> dedupe -> load -> chunk -> embed -> upsert to Pinecone."""
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.db.session import get_conn
from app.ingestion.chunker import chunk
from app.ingestion.loaders import load_text
from app.services.vectorstore import get_vectorstore


def guess_doc_type(name: str) -> str:
    n = name.lower()
    if "postmortem" in n or "pm-" in n:
        return "postmortem"
    if "sop" in n:
        return "sop"
    return "runbook"


SERVICE_RE = re.compile(r"^\s*service:\s*([\w.-]+)", re.IGNORECASE | re.MULTILINE)


def detect_service(text: str) -> Optional[str]:
    """Read a 'Service: rds' line from the document header, if there is one."""
    m = SERVICE_RE.search(text[:2000])
    return m.group(1).lower() if m else None


def ingest_file(path: Path, service: Optional[str] = None, doc_type: Optional[str] = None,
                force: bool = False) -> dict:
    """force=True re-indexes a file even if its content hash is already stored."""
    data = path.read_bytes()
    doc_id = hashlib.sha256(data).hexdigest()[:16]

    with get_conn() as conn:
        if not force and conn.execute("SELECT 1 FROM documents WHERE doc_id=?", (doc_id,)).fetchone():
            return {"doc_id": doc_id, "status": "duplicate"}
        old = conn.execute("SELECT doc_id, chunks FROM documents WHERE filename=? OR doc_id=?",
                           (path.name, doc_id)).fetchone()

    text = load_text(path).strip()
    if not text:
        raise ValueError("No extractable text (empty or scanned file)")

    meta = {"doc_id": doc_id, "title": path.stem, "source": path.name,
            "doc_type": doc_type or guess_doc_type(path.name),
            "service": service or detect_service(text) or "general"}
    docs = chunk(text, meta)

    vs = get_vectorstore()
    if old:  # same filename, new content -> replace old vectors
        vs.delete(ids=[f"{old['doc_id']}-{i}" for i in range(old["chunks"])])
    vs.add_documents(docs, ids=[f"{doc_id}-{i}" for i in range(len(docs))])

    with get_conn() as conn:
        if old:
            conn.execute("DELETE FROM documents WHERE doc_id=?", (old["doc_id"],))
        conn.execute(
            "INSERT INTO documents VALUES (?,?,?,?,?,?)",
            (doc_id, path.name, meta["doc_type"], meta["service"], len(docs),
             datetime.now(timezone.utc).isoformat()),
        )
    return {"doc_id": doc_id, "status": "updated" if old else "ingested", "chunks": len(docs)}
