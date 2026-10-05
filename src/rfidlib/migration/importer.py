"""Controlled spreadsheet import: backup -> stage -> validate -> dedupe -> migrate -> reconcile.

Guarantees (NFR 01 / AC 01 / AC 10):
  * a verified backup is taken before any write;
  * existing bib_record rows are only ever read, never updated or deleted by an import;
  * the whole import runs in one transaction (dry-run always rolls back);
  * source rows = migrated + invalid + duplicate, and the report proves it.
"""

import csv
import hashlib
import json
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

from .. import db
from .reader import read_rows
from .validate import validate_row


def file_sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def checksum_existing(conn, max_id: int) -> str:
    """Hash of every bib_record row with id <= max_id (i.e. the pre-existing records)."""
    h = hashlib.sha256()
    for row in conn.execute("SELECT * FROM bib_record WHERE id <= ? ORDER BY id", (max_id,)):
        h.update(repr(tuple(row)).encode())
    return h.hexdigest()


def make_backup(db_path, backup_dir, tag: str) -> Path:
    Path(backup_dir).mkdir(parents=True, exist_ok=True)
    dest = Path(backup_dir) / f"{Path(db_path).stem}_{tag}.db"
    src, dst = sqlite3.connect(str(db_path)), sqlite3.connect(str(dest))
    try:
        src.backup(dst)
        if dst.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("Backup failed integrity check; import aborted")
    finally:
        src.close()
        dst.close()
    return dest


def _insert_valid(conn, batch_id, valid_rows):
    conn.executemany(
        "INSERT INTO bib_record(accession_no, barcode, isbn, title, author, publisher,"
        " pub_year, import_batch_id) VALUES (?,?,?,?,?,?,?,?)",
        [
            (
                r["accession_no"],
                r["barcode"] or None,
                r["isbn"] or None,
                r["title"],
                r["author"] or None,
                r["publisher"] or None,
                int(r["pub_year"]) if r["pub_year"] else None,
                batch_id,
            )
            for _, r in valid_rows
        ],
    )


def run_import(
    db_path, source, mapping, backup_dir, report_dir, dry_run=False, actor="migration"
) -> dict:
    conn = db.connect(db_path)
    if db.current_version(conn) == 0:
        conn.close()
        raise RuntimeError("Database has no schema; run init-db first")

    batch_id = datetime.now(UTC).strftime("%Y%m%d%H%M%S") + "-" + uuid.uuid4().hex[:6]
    source = Path(source)
    rows = list(read_rows(source, mapping))  # fails fast on schema errors
    backup = make_backup(db_path, backup_dir, batch_id)  # gate: no backup, no import
    max_id = conn.execute("SELECT COALESCE(MAX(id), 0) FROM bib_record").fetchone()[0]
    before = checksum_existing(conn, max_id)

    existing_acc = {r[0] for r in conn.execute("SELECT accession_no FROM bib_record")}
    existing_bc = {
        r[0] for r in conn.execute("SELECT barcode FROM bib_record WHERE barcode IS NOT NULL")
    }
    seen_acc, seen_bc = set(existing_acc), set(existing_bc)

    staged, valid_rows = [], []
    counts = {"invalid": 0, "duplicate": 0, "valid": 0}
    for n, r in rows:
        errs = validate_row(r)
        if errs:
            status, reason = "invalid", "; ".join(errs)
        elif r["accession_no"] in seen_acc:
            where = "existing record" if r["accession_no"] in existing_acc else "earlier row"
            status, reason = "duplicate", f"duplicate accession_no (matches {where})"
        elif r.get("barcode") and r["barcode"] in seen_bc:
            status, reason = "duplicate", "duplicate barcode"
        else:
            status, reason = "valid", ""
            seen_acc.add(r["accession_no"])
            if r.get("barcode"):
                seen_bc.add(r["barcode"])
            valid_rows.append((n, r))
        counts[status] += 1
        staged.append(
            (
                batch_id,
                n,
                r["accession_no"],
                r.get("barcode"),
                r.get("isbn"),
                r["title"],
                r.get("author"),
                r.get("publisher"),
                r.get("pub_year"),
                status,
                reason,
            )
        )

    try:
        conn.execute("BEGIN")
        conn.execute(
            "INSERT INTO import_batch(batch_id, source_file, source_sha256, status, total_rows)"
            " VALUES (?,?,?,?,?)",
            (batch_id, source.name, file_sha256(source), "running", len(rows)),
        )
        conn.executemany(
            "INSERT INTO stg_import_row(batch_id,row_no,accession_no,barcode,isbn,title,"
            "author,publisher,pub_year,status,reason) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            staged,
        )
        _insert_valid(conn, batch_id, valid_rows)
        conn.execute(
            "UPDATE stg_import_row SET status='migrated' WHERE batch_id=? AND status='valid'",
            (batch_id,),
        )
        conn.execute(
            "UPDATE import_batch SET status='migrated', migrated_rows=?, invalid_rows=?,"
            " duplicate_rows=? WHERE batch_id=?",
            (counts["valid"], counts["invalid"], counts["duplicate"], batch_id),
        )
        db.audit(
            conn, actor, "IMPORT_DRY_RUN" if dry_run else "IMPORT", batch_id, json.dumps(counts)
        )
        conn.execute("ROLLBACK" if dry_run else "COMMIT")
    except Exception as exc:
        conn.execute("ROLLBACK")
        db.audit(conn, actor, "IMPORT_FAILED", batch_id, str(exc)[:200])
        conn.close()
        raise

    after = checksum_existing(conn, max_id)
    actual_migrated = conn.execute(
        "SELECT COUNT(*) FROM bib_record WHERE import_batch_id=?", (batch_id,)
    ).fetchone()[0]
    conn.close()

    total = len(rows)
    result = {
        "batch_id": batch_id,
        "dry_run": dry_run,
        "source_file": source.name,
        "source_rows": total,
        "migrated": counts["valid"] if not dry_run else 0,
        "would_migrate": counts["valid"],
        "invalid": counts["invalid"],
        "duplicate": counts["duplicate"],
        "rows_in_target_for_batch": actual_migrated,
        "reconciled": total == counts["valid"] + counts["invalid"] + counts["duplicate"]
        and actual_migrated == (0 if dry_run else counts["valid"]),
        "existing_records_unchanged": before == after,
        "existing_checksum_before": before,
        "existing_checksum_after": after,
        "backup_file": str(backup),
    }
    _write_reports(Path(report_dir), batch_id, result, staged)
    return result


def _write_reports(report_dir: Path, batch_id: str, result: dict, staged: list):
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / f"{batch_id}_reconciliation.json").write_text(json.dumps(result, indent=2))
    with (report_dir / f"{batch_id}_errors.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["row_no", "accession_no", "title", "status", "reason"])
        for s in staged:
            if s[9] in ("invalid", "duplicate"):
                w.writerow([s[1], s[2], s[5], s[9], s[10]])


def rollback_batch(db_path, batch_id: str, actor="migration") -> int:
    conn = db.connect(db_path)
    row = conn.execute("SELECT status FROM import_batch WHERE batch_id=?", (batch_id,)).fetchone()
    if row is None or row["status"] != "migrated":
        conn.close()
        raise ValueError(f"Batch {batch_id} not found or not in 'migrated' state")
    conn.execute("BEGIN")
    n = conn.execute("DELETE FROM bib_record WHERE import_batch_id=?", (batch_id,)).rowcount
    conn.execute("UPDATE import_batch SET status='rolled_back' WHERE batch_id=?", (batch_id,))
    conn.execute(
        "UPDATE stg_import_row SET status='rolled_back' WHERE batch_id=? AND status='migrated'",
        (batch_id,),
    )
    db.audit(conn, actor, "IMPORT_ROLLBACK", batch_id, f"removed {n} records")
    conn.execute("COMMIT")
    conn.close()
    return n


def restore_backup(backup_path, db_path, actor="migration") -> None:
    src = sqlite3.connect(str(backup_path))
    try:
        if src.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("Backup failed integrity check; restore aborted")
        dst = sqlite3.connect(str(db_path))
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()
    conn = db.connect(db_path)
    db.audit(conn, actor, "RESTORE", Path(backup_path).name, "restored from backup")
    conn.close()
