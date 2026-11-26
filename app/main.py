"""Phase 5: FastAPI entry point. Mounts API routers and the static UI."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import audit, chat, health, incidents, ingest
from app.config import get_settings
from app.db.session import init_db

logging.basicConfig(level=get_settings().log_level,
                    format="%(asctime)s %(levelname)s %(name)s %(message)s")



@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Enterprise Incident Response Copilot", version="0.2.0", lifespan=lifespan)


app.include_router(health.router)
app.include_router(incidents.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(ingest.router, prefix="/api")
app.include_router(audit.router, prefix="/api")

app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse("app/static/index.html")
