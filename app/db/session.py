"""Phase 5: tiny SQLite helper (no ORM needed for this project)."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from app.config import get_settings
from app.db.models import SCHEMA


def _connect() -> sqlite3.Connection:
    path = Path(get_settings().app_db)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_conn():
    conn = _connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA)
