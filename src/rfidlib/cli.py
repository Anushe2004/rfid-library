"""Command-line entry: python -m rfidlib.cli --help"""

import argparse
import configparser
import json
import sys
from pathlib import Path

from . import db
from .migration import importer, profile, reader


def _cfg(path):
    c = configparser.ConfigParser()
    c.read(path)
    if not c.sections():
        sys.exit(f"Config not found or empty: {path} (copy config/sample.ini to config/local.ini)")
    return c


def main(argv=None):
    ap = argparse.ArgumentParser(prog="rfidlib")
    ap.add_argument("--config", default="config/local.ini")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init-db", help="apply versioned migrations")
    sub.add_parser("verify", help="schema version and integrity check")
    p = sub.add_parser("profile", help="profile a source spreadsheet")
    p.add_argument("source")
    p = sub.add_parser("import", help="validate and import a spreadsheet")
    p.add_argument("source")
    p.add_argument("--dry-run", action="store_true")
    p = sub.add_parser("rollback", help="undo one import batch")
    p.add_argument("batch_id")
    p = sub.add_parser("restore", help="restore database from a backup file")
    p.add_argument("backup_file")
    a = ap.parse_args(argv)

    c = _cfg(a.config)
    db_path = c["database"]["path"]
    mapping = reader.load_mapping(c["migration"]["column_mapping"])
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    if a.cmd == "init-db":
        conn = db.connect(db_path)
        print("schema version:", db.migrate_up(conn))
    elif a.cmd == "verify":
        conn = db.connect(db_path)
        print("schema version:", db.current_version(conn))
        print("integrity:", conn.execute("PRAGMA integrity_check").fetchone()[0])
    elif a.cmd == "profile":
        print(json.dumps(profile.profile(a.source, mapping), indent=2))
    elif a.cmd == "import":
        res = importer.run_import(
            db_path,
            a.source,
            mapping,
            c["migration"]["backup_dir"],
            c["migration"]["report_dir"],
            dry_run=a.dry_run,
        )
        print(json.dumps({k: v for k, v in res.items() if "checksum" not in k}, indent=2))
        sys.exit(0 if res["reconciled"] and res["existing_records_unchanged"] else 1)
    elif a.cmd == "rollback":
        print("records removed:", importer.rollback_batch(db_path, a.batch_id))
    elif a.cmd == "restore":
        importer.restore_backup(a.backup_file, db_path)
        print("restored from", a.backup_file)


if __name__ == "__main__":
    main()
