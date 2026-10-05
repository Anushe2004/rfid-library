"""SQLite access and versioned migrations (prototype; production target is PostgreSQL)."""

import sqlite3
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"


def connect(db_path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _versions():
    return sorted({int(p.name.split("_")[0]) for p in MIGRATIONS_DIR.glob("*.up.sql")})


def _file(version: int, direction: str) -> Path:
    return next(MIGRATIONS_DIR.glob(f"{version:04d}_*.{direction}.sql"))


def current_version(conn) -> int:
    conn.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY)")
    row = conn.execute("SELECT MAX(version) AS v FROM schema_version").fetchone()
    return row["v"] or 0


def migrate_up(conn, target: int | None = None) -> int:
    cur = current_version(conn)
    for v in _versions():
        if v > cur and (target is None or v <= target):
            conn.executescript(_file(v, "up").read_text())
            conn.execute("INSERT INTO schema_version(version) VALUES (?)", (v,))
    return current_version(conn)


def migrate_down(conn, target: int = 0) -> int:
    cur = current_version(conn)
    for v in sorted(_versions(), reverse=True):
        if target < v <= cur:
            conn.executescript(_file(v, "down").read_text())
            conn.execute("DELETE FROM schema_version WHERE version = ?", (v,))
    return current_version(conn)


def audit(conn, actor: str, action: str, entity: str = "", detail: str = ""):
    conn.execute(
        "INSERT INTO audit_log(actor, action, entity, detail) VALUES (?,?,?,?)",
        (actor, action, entity, detail),
    )
