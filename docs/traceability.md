# Requirements traceability matrix (starter, D1)

Status: **Done** = implemented and tested in this repo; **Planned** = in the design (see the
technical plan deck), not yet built. Update this file whenever behaviour changes (change control).

| Req | Summary | Status | Implementation | Test evidence |
|-----|---------|--------|----------------|---------------|
| FR10 | Import ~20k spreadsheet records: validation, duplicates, error log, reconciliation, rollback | Done | `src/rfidlib/migration/*` | `tests/test_importer.py`, `tests/test_validate.py` |
| AC01 | Staging, reject invalid, find duplicates, migrate valid, reconcile counts | Done | `importer.run_import` | `test_import_reconciles_and_logs_errors`, `test_xlsx_synthetic_dataset_matches_expected` |
| AC10 | Restore after failed migration; original data intact | Done | `importer.restore_backup`, checksum check | `test_failed_migration_leaves_data_intact`, `test_restore_from_backup_after_damage` |
| NFR01 | Backup first; never modify/delete existing records | Done | backup gate + insert-only import + checksum | `test_existing_records_never_modified` |
| NFR06 | Versioned DB migrations, config outside code | Done | `migrations/`, `config/` | `test_versioned_migrations_up_down` |
| NFR07 | Health check | Partial | `api.py` `/health`, `/version` | `tests/test_api.py` |
| FR11 | Audit log | Partial | append-only `audit_log` (triggers) | `test_audit_log_is_append_only` |
| NFR04 | Pinned deps, licence inventory | Partial | `requirements*.txt`, `docs/licenses.md` | CI `pip-audit` |
| FR01, FR02 | Core ILMS, search | Planned | | |
| FR03, FR05 | RFID middleware, tagging (AC02) | Planned | | |
| FR04 | Circulation, blocks (AC03, AC04) | Planned | | |
| FR06, FR07 | Inventory, gate events (AC05, AC06) | Planned | | |
| FR08, FR09 | Reports, notifications (AC08) | Planned | | |
| FR12 | Offline lifecycle (AC09) | Planned | | |
| AC07 | Smart-card login, RBAC | Planned | | |
