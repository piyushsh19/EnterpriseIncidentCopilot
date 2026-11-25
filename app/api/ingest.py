"""Phase 5: upload runbooks / SOPs / postmortems and list what is indexed."""
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.config import get_settings
from app.db.session import get_conn
from app.ingestion.pipeline import ingest_file
from app.services.audit import write_audit

router = APIRouter(tags=["ingestion"])


@router.post("/ingest")
async def ingest(file: UploadFile = File(...), service: Optional[str] = Form(None),
                 doc_type: Optional[str] = Form(None)) -> dict:
    s = get_settings()
    ext = Path(file.filename or "").suffix.lower()
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
        except ValueError as exc:
            raise HTTPException(400, str(exc))
    write_audit(action="ingest", question=file.filename, status=result["status"])
    return result


@router.get("/documents")
def documents() -> list:
    with get_conn() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM documents ORDER BY ingested_at DESC")]
