"""Synthetic catalogue data (no real personal data). Known defects are injected so the
expected import outcome is deterministic and testable."""

import csv
import random
from pathlib import Path

FIRST = ["Asha", "Ravi", "Meera", "Kiran", "Lakshmi", "Arjun", "Divya", "Sanjay", "Nila", "José"]
LAST = ["Iyer", "Reddy", "Nair", "Sharma", "Menon", "Das", "Rao", "Pillai", "Verma", "Müller"]
WORDS = [
    "Algorithms",
    "Rivers",
    "Signals",
    "Networks",
    "Gardens",
    "Machines",
    "Letters",
    "Oceans",
    "Systems",
    "Stories",
    "Maps",
    "Engines",
    "Poems",
    "Circuits",
    "Histories",
]
PUBS = ["Orbit Press", "Lakeview Books", "Deccan House", "Northgate", "Sunrise Publishing"]
HEADER = ["Accession No", "Barcode", "ISBN", "Title", "Author", "Publisher", "Year"]


def _isbn13(rng):
    d = [9, 7, 8] + [rng.randint(0, 9) for _ in range(9)]
    check = (10 - sum(x * (1 if i % 2 == 0 else 3) for i, x in enumerate(d)) % 10) % 10
    return "".join(map(str, d + [check]))


def generate(n=20000, invalid=150, duplicates=100, seed=42):
    # Seeded RNG for reproducible synthetic test data; not used for anything security related.
    rng = random.Random(seed)  # nosec B311
    idx = list(range(10, n))  # keep first rows clean so dupes have sources
    bad = set(rng.sample(idx, invalid))
    dup = set(rng.sample([i for i in idx if i not in bad], duplicates))
    rows, valid_acc = [], []
    for i in range(n):
        acc, bc = f"ACC{i + 1:06d}", f"BC{i + 1:07d}"
        row = [
            acc,
            bc,
            _isbn13(rng),
            f"{rng.choice(WORDS)} of {rng.choice(WORDS)} {i}",
            f"{rng.choice(FIRST)} {rng.choice(LAST)}",
            rng.choice(PUBS),
            rng.randint(1950, 2025),
        ]
        if i in bad:
            kind = i % 4
            if kind == 0:
                row[3] = ""
            elif kind == 1:
                row[2] = row[2][:-1] + str((int(row[2][-1]) + 1) % 10)
            elif kind == 2:
                row[6] = rng.choice([1066, "abcd", 2999])
            else:
                row[0] = ""
        elif i in dup:
            row[0] = rng.choice(valid_acc)
        else:
            valid_acc.append(acc)
        rows.append(row)
    expected = {
        "source_rows": n,
        "invalid": invalid,
        "duplicate": duplicates,
        "valid": n - invalid - duplicates,
    }
    return rows, expected


def write_csv(path, rows):
    with Path(path).open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(HEADER)
        w.writerows(rows)


def write_xlsx(path, rows):
    from openpyxl import Workbook

    wb = Workbook(write_only=True)
    ws = wb.create_sheet("Catalogue")
    ws.append(HEADER)
    for r in rows:
        ws.append(r)
    wb.save(path)
