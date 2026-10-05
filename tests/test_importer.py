import json
import sqlite3

import pytest

from rfidlib import db
from rfidlib.migration import importer, reader
from rfidlib.migration.importer import checksum_existing, rollback_batch, run_import
from rfidlib.synthetic import generate, write_xlsx

from .conftest import MAPPING, make_csv, seed_existing

ROWS = [
    "ACC1,BC1,9780306406157,Good One,A B,Pub,2001",
    "ACC2,BC2,,Good Two,,,",
    "ACC1,BC9,,Dup of earlier row,,,",  # duplicate accession (earlier row)
    "OLD001,BC10,,Dup of existing,,,",  # duplicate of existing record
    ",BC11,,No accession,,,",  # invalid
    "ACC3,BC12,9780306406158,Bad isbn,,,",  # invalid
]


def _run(env, src, **kw):
    return run_import(env["db"], src, MAPPING, env["backup"], env["reports"], **kw)


def _count(env):
    conn = db.connect(env["db"])
    n = conn.execute("SELECT COUNT(*) FROM bib_record").fetchone()[0]
    conn.close()
    return n


def test_import_reconciles_and_logs_errors(env):
    seed_existing(env["db"])
    res = _run(env, make_csv(env["tmp"], ROWS))
    assert (res["source_rows"], res["migrated"], res["invalid"], res["duplicate"]) == (6, 2, 2, 2)
    assert res["reconciled"] and res["existing_records_unchanged"]
    errors = (env["reports"] / f"{res['batch_id']}_errors.csv").read_text()
    assert "duplicate accession_no (matches existing record)" in errors
    assert "isbn invalid" in errors


def test_existing_records_never_modified(env):
    seed_existing(env["db"])
    conn = db.connect(env["db"])
    before = checksum_existing(conn, 3)
    conn.close()
    _run(env, make_csv(env["tmp"], ROWS))
    conn = db.connect(env["db"])
    assert checksum_existing(conn, 3) == before
    conn.close()


def test_dry_run_writes_nothing(env):
    seed_existing(env["db"])
    res = _run(env, make_csv(env["tmp"], ROWS), dry_run=True)
    assert res["would_migrate"] == 2 and res["migrated"] == 0 and res["reconciled"]
    assert _count(env) == 3
    conn = db.connect(env["db"])
    assert conn.execute("SELECT COUNT(*) FROM import_batch").fetchone()[0] == 0
    conn.close()


def test_rollback_removes_only_that_batch(env):
    seed_existing(env["db"])
    r1 = _run(env, make_csv(env["tmp"], ["N1,,,First batch,,,"], "a.csv"))
    r2 = _run(env, make_csv(env["tmp"], ["N2,,,Second batch,,,"], "b.csv"))
    assert _count(env) == 5
    assert rollback_batch(env["db"], r1["batch_id"]) == 1
    assert _count(env) == 4
    with pytest.raises(ValueError):
        rollback_batch(env["db"], r1["batch_id"])  # already rolled back
    assert r2["batch_id"] != r1["batch_id"]


def test_failed_migration_leaves_data_intact(env, monkeypatch):
    seed_existing(env["db"])
    conn = db.connect(env["db"])
    before = checksum_existing(conn, 3)
    conn.close()

    def boom(*a, **k):
        raise RuntimeError("simulated failure mid-migration")

    monkeypatch.setattr(importer, "_insert_valid", boom)
    with pytest.raises(RuntimeError):
        _run(env, make_csv(env["tmp"], ROWS))
    conn = db.connect(env["db"])
    assert checksum_existing(conn, 3) == before and _count(env) == 3
    assert (
        conn.execute("SELECT COUNT(*) FROM audit_log WHERE action='IMPORT_FAILED'").fetchone()[0]
        == 1
    )
    conn.close()


def test_restore_from_backup_after_damage(env):
    """AC 10: after damage, a restore proves the original data is intact."""
    seed_existing(env["db"])
    conn = db.connect(env["db"])
    before = checksum_existing(conn, 3)
    conn.close()
    res = _run(env, make_csv(env["tmp"], ["N1,,,New,,,"]))
    conn = sqlite3.connect(str(env["db"]))
    conn.execute("DELETE FROM bib_record")  # simulate corruption
    conn.commit()
    conn.close()
    importer.restore_backup(res["backup_file"], env["db"])
    conn = db.connect(env["db"])
    assert checksum_existing(conn, 3) == before and _count(env) == 3
    assert conn.execute("SELECT COUNT(*) FROM audit_log WHERE action='RESTORE'").fetchone()[0] == 1
    conn.close()


def test_audit_log_is_append_only(env):
    conn = db.connect(env["db"])
    db.audit(conn, "tester", "X")
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute("UPDATE audit_log SET action='Y'")
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute("DELETE FROM audit_log")
    conn.close()


def test_missing_required_column(env):
    p = env["tmp"] / "bad.csv"
    p.write_text("Barcode,Author\nB1,X\n")
    with pytest.raises(reader.SchemaError):
        _run(env, p)


def test_versioned_migrations_up_down(env):
    conn = db.connect(env["db"])
    assert db.current_version(conn) == 1
    assert db.migrate_down(conn, 0) == 0
    assert db.migrate_up(conn) == 1
    conn.close()


def test_xlsx_synthetic_dataset_matches_expected(env):
    rows, expected = generate(n=2000, invalid=30, duplicates=20, seed=7)
    src = env["tmp"] / "cat.xlsx"
    write_xlsx(src, rows)
    res = _run(env, src)
    assert res["migrated"] == expected["valid"]
    assert res["invalid"] == expected["invalid"]
    assert res["duplicate"] == expected["duplicate"]
    assert res["reconciled"]
    json.loads((env["reports"] / f"{res['batch_id']}_reconciliation.json").read_text())
