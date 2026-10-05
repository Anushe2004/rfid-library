from rfidlib.migration.validate import isbn_ok, validate_row


def test_isbn_checksums():
    assert isbn_ok("978-0-306-40615-7")
    assert isbn_ok("0306406152")
    assert not isbn_ok("978-0-306-40615-8")
    assert not isbn_ok("12345")


def test_row_rules():
    good = {"accession_no": "A1", "title": "T", "isbn": "", "pub_year": "2001", "barcode": ""}
    assert validate_row(good) == []
    assert "title missing" in validate_row({**good, "title": ""})
    assert "accession_no missing" in validate_row({**good, "accession_no": ""})
    assert "pub_year invalid" in validate_row({**good, "pub_year": "1066"})
    assert "isbn invalid" in validate_row({**good, "isbn": "9780306406158"})
