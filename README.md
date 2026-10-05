# RFID Library Solution: foundation and migration utility

Synthetic-data prototype for the AISYS technical evaluation. This first slice delivers
the repository skeleton, versioned database migrations, an append-only audit log, a health
endpoint, and the **controlled spreadsheet migration utility** (FR10, AC01, AC10, NFR01).
The remaining workflows (RFID middleware, circulation, gate events, offline installer, ...) are
designed in the technical plan and tracked in `docs/traceability.md`.

## Quick start (Python 3.12+)
```bash
pip install -r requirements-dev.txt
cp config/sample.ini config/local.ini
export PYTHONPATH=src                      # Windows PowerShell: $env:PYTHONPATH="src"
python scripts/generate_synthetic.py       # 20,000 synthetic rows (150 invalid, 100 duplicates)
python -m rfidlib.cli init-db
python -m rfidlib.cli profile data/synthetic/catalogue_20k.xlsx
python -m rfidlib.cli import data/synthetic/catalogue_20k.xlsx --dry-run
python -m rfidlib.cli import data/synthetic/catalogue_20k.xlsx
python -m rfidlib.cli rollback <batch_id>              # undo one batch
python -m rfidlib.cli restore data/backups/<file>.db   # full restore
pytest -q
```
Expected result for the synthetic file: 19,750 migrated, 150 invalid, 100 duplicate, reconciled.

## How the import protects existing data
1. Source is read and header-mapped first; a missing required column stops the run.
2. A backup is taken and integrity-checked **before** any write. No backup, no import.
3. Rows go to a staging table with a status and reason, then valid rows move to `bib_record`
   by INSERT only; existing rows are never updated or deleted.
4. Everything runs in one transaction. `--dry-run` always rolls back.
5. Report: `source = migrated + invalid + duplicate`, target count check, and a checksum of
   the pre-existing records before vs after (`data/reports/<batch>_reconciliation.json`;
   row-level reasons in `<batch>_errors.csv`).
6. `rollback <batch_id>` deletes only that batch; `restore` brings back the pre-import backup.

## Layout
`src/rfidlib/` code, `migrations/` versioned SQL (up/down), `config/` sample configuration
(no secrets), `tests/` automated tests, `docs/` traceability, assumptions, licences.

## Branch strategy
`main` is protected and tagged for releases; work happens in `feature/<id>-<name>` branches
merged by reviewed pull request; CI runs lint, bandit, pip-audit and tests.

## Known limitations
SQLite stands in for PostgreSQL in this slice. No real RFID devices, ILMS, or vendor
SDKs are used. No NCIP/SIP2/security/performance certification is claimed.
