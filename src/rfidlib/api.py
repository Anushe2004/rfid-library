"""Service skeleton: health and version endpoints (FR 11 / NFR 07). Run:
uvicorn rfidlib.api:app  (install uvicorn separately; not needed for tests)."""

import os
import sqlite3

from fastapi import FastAPI

from . import __version__

app = FastAPI(title="RFID Library Service", version=__version__)


@app.get("/version")
def version():
    return {"software_version": __version__}


@app.get("/health")
def health():
    path = os.environ.get("RFIDLIB_DB", "data/library.db")
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)  # read-only: health never writes
        ok = conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        schema = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] or 0
        conn.close()
        return {"status": "ok" if ok else "degraded", "schema_version": schema}
    except Exception as exc:  # noqa: BLE001 - health must never raise
        return {"status": "down", "error": type(exc).__name__}
