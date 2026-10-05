"""Profile a source spreadsheet before import (stage 6, step 1)."""

from collections import Counter

from .reader import read_rows


def profile(source, mapping) -> dict:
    total = 0
    nulls = Counter()
    distinct = {}
    acc = Counter()
    for _, r in read_rows(source, mapping):
        total += 1
        for k, v in r.items():
            if v == "":
                nulls[k] += 1
            distinct.setdefault(k, set()).add(v)
        acc[r.get("accession_no", "")] += 1
    return {
        "rows": total,
        "null_counts": dict(nulls),
        "distinct_counts": {k: len(v) for k, v in distinct.items()},
        "repeated_accession_numbers": sum(1 for c in acc.values() if c > 1),
    }
