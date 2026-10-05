CREATE TABLE bib_record (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    accession_no TEXT NOT NULL UNIQUE,
    barcode TEXT UNIQUE,
    isbn TEXT,
    title TEXT NOT NULL,
    author TEXT,
    publisher TEXT,
    pub_year INTEGER,
    import_batch_id TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX ix_bib_isbn ON bib_record(isbn);
CREATE INDEX ix_bib_batch ON bib_record(import_batch_id);

CREATE TABLE import_batch (
    batch_id TEXT PRIMARY KEY,
    source_file TEXT NOT NULL,
    source_sha256 TEXT NOT NULL,
    status TEXT NOT NULL,
    total_rows INTEGER NOT NULL DEFAULT 0,
    migrated_rows INTEGER NOT NULL DEFAULT 0,
    invalid_rows INTEGER NOT NULL DEFAULT 0,
    duplicate_rows INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE stg_import_row (
    batch_id TEXT NOT NULL,
    row_no INTEGER NOT NULL,
    accession_no TEXT, barcode TEXT, isbn TEXT, title TEXT,
    author TEXT, publisher TEXT, pub_year TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    reason TEXT,
    PRIMARY KEY (batch_id, row_no)
);

CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL DEFAULT (datetime('now')),
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    entity TEXT,
    detail TEXT
);
CREATE TRIGGER audit_no_update BEFORE UPDATE ON audit_log
BEGIN SELECT RAISE(ABORT, 'audit_log is append-only'); END;
CREATE TRIGGER audit_no_delete BEFORE DELETE ON audit_log
BEGIN SELECT RAISE(ABORT, 'audit_log is append-only'); END;
