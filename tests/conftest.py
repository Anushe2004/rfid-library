import pytest

from rfidlib import db
from rfidlib.migration import reader

MAPPING = reader.load_mapping("config/column_mapping.json")
HEADER = "Accession No,Barcode,ISBN,Title,Author,Publisher,Year\n"


@pytest.fixture
def env(tmp_path):
    path = tmp_path / "library.db"
    conn = db.connect(path)
    db.migrate_up(conn)
    conn.close()
    return {
        "db": path,
        "backup": tmp_path / "backups",
        "reports": tmp_path / "reports",
        "tmp": tmp_path,
    }


def make_csv(tmp_path, lines, name="src.csv"):
    p = tmp_path / name
    p.write_text(HEADER + "\n".join(lines) + "\n", encoding="utf-8")
    return p


def seed_existing(db_path, n=3):
    conn = db.connect(db_path)
    for i in range(1, n + 1):
        conn.execute(
            "INSERT INTO bib_record(accession_no, barcode, title) VALUES (?,?,?)",
            (f"OLD{i:03d}", f"OB{i:03d}", f"Existing title {i}"),
        )
    conn.close()
