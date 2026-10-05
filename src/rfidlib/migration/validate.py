"""Row-level validation rules."""

from datetime import UTC, datetime


def isbn_ok(raw: str) -> bool:
    s = raw.replace("-", "").replace(" ", "").upper()
    if len(s) == 10:
        if not (s[:9].isdigit() and (s[9].isdigit() or s[9] == "X")):
            return False
        total = sum((10 - i) * (10 if c == "X" else int(c)) for i, c in enumerate(s))
        return total % 11 == 0
    if len(s) == 13 and s.isdigit():
        total = sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(s))
        return total % 10 == 0
    return False


def validate_row(r: dict) -> list[str]:
    errs = []
    if not r.get("accession_no"):
        errs.append("accession_no missing")
    elif len(r["accession_no"]) > 32:
        errs.append("accession_no longer than 32 chars")
    if not r.get("title"):
        errs.append("title missing")
    elif len(r["title"]) > 500:
        errs.append("title longer than 500 chars")
    if r.get("barcode") and len(r["barcode"]) > 32:
        errs.append("barcode longer than 32 chars")
    if r.get("isbn") and not isbn_ok(r["isbn"]):
        errs.append("isbn invalid")
    y = r.get("pub_year")
    if y and (not y.isdigit() or not (1400 <= int(y) <= datetime.now(UTC).year + 1)):
        errs.append("pub_year invalid")
    return errs
