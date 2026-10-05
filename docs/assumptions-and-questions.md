# Assumptions, clarification log and risks (D0/D1)

## Assumptions
- All data and credentials are synthetic; no production system is touched.
- The source spreadsheet columns are unknown, so import is driven by `config/column_mapping.json`
  (header aliases). Required fields assumed: accession number and title.
- A duplicate is an accession number or barcode already seen (in the file or in the target).
  Several copies of one title with different accession numbers are valid, not duplicates.
- "First occurrence wins": later duplicate rows are rejected and logged, never merged silently.
- Prototype database is SQLite for a zero-setup demo; SQL is kept portable for PostgreSQL 16.

## Questions for AISYS (send through the email thread)
1. Which columns does the real 20,000-row spreadsheet contain, and which are mandatory?
2. What defines a duplicate for the library (accession number, ISBN + edition, barcode)?
3. Is PostgreSQL acceptable as the production database, or must the existing ILMS DB engine be used?
4. Is a working demo expected in addition to the document, or is the plan itself the evaluation?

## Risks
- Unknown ILMS schema: mitigated by an adapter boundary and read-only access.
- Spreadsheet quality (encodings, merged cells): mitigated by profiling and an error log.
- Time: remaining workflows are planned in the deck; the migration utility is the first built slice.
