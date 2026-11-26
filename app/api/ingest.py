"""Phase 5: upload runbooks / SOPs / postmortems and list what is indexed."""
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile

from app.config import get_settings
from app.db.session import get_conn
from app.ingestion.pipeline import ingest_file
from app.services.audit import write_audit
from app.services.retry import UpstreamError

router = APIRouter(tags=["ingestion"])


@router.post("/ingest")
async def ingest(file: UploadFile = File(...), service: Optional[str] = Form(None),
                 doc_type: Optional[str] = Form(None),
                 x_user: str = Header(default="anonymous")) -> dict:
    s = get_settings()
    ext = Path(file.filename or "").suffix.lower()
    if doc_type and doc_type not in ("runbook", "sop", "postmortem"):
        raise HTTPException(400, "doc_type must be runbook, sop or postmortem")
    if ext not in s.allowed_extensions.split(","):
        raise HTTPException(400, f"Unsupported file type '{ext}'")
    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty file")
    if len(data) > s.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"File larger than {s.max_upload_mb} MB")

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / Path(file.filename).name
        path.write_bytes(data)
        try:
            result = ingest_file(path, service=service, doc_type=doc_type)
        except ValueError as exc:  # empty / scanned / unreadable file
            write_audit(user=x_user, action="ingest", question=file.filename,
                        status="rejected", error=str(exc))
            raise HTTPException(400, str(exc))
        except Exception as exc:  # embeddings or Pinecone down
            write_audit(user=x_user, action="ingest", question=file.filename,
                        status="error", error=str(exc))
            raise HTTPException(502, f"Could not index the file: {exc}")
    write_audit(user=x_user, action="ingest", question=file.filename, status=result["status"],
                doc_ids=[result["doc_id"]])
    return result


@router.get("/documents")
def documents() -> list:
    with get_conn() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM documents ORDER BY ingested_at DESC")]
