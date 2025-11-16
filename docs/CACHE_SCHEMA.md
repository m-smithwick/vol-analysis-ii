# 🔧 Cache Schema & Migration Guide

Detailed reference for how cached Massive.com data is stored, validated, and migrated across schema versions.

---

## 1. Schema Features

### Metadata Headers
- Each cache file begins with a JSON header that captures:
  - `schema_version`
  - `created_at`
  - Source (`massive` vs `yfinance`)
  - SHA‑256 checksum of the payload

### Data Integrity Validation
- Checksums verified on every load; mismatches trigger automatic refresh of the affected file.
- Timestamp normalization ensures timezone-aware vs naive data does not corrupt comparisons.

### Automatic Migration
- Legacy cache files are detected via header version and upgraded in place.
- Migration logs are written to `cache_migration.log` for auditing.

---

## 2. Bulk Migration Utility

Run the migration helper whenever upgrading schema versions:
```bash
python populate_cache.py --migrate-only
```
**Output Highlights**
```
Scanning data_cache/... 
✓ AAPL_1d_data.csv upgraded v2 → v3
✓ MSFT_1d_data.csv already at v3
```

---

## 3. Troubleshooting Cache Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| `SchemaValidationError` | Header missing or outdated | Delete the file or run `--migrate-only` |
| `Checksum mismatch` | Manual edit or partial write | File is automatically re-downloaded, verify disk space |
| New ticker missing data | Not included in tracked lists | Add ticker to `stocks.txt` and rerun `populate_cache_bulk.py` |

---

## 4. Maintenance Tips

- Keep `massive_cache/` backups so you can rebuild yfinance-format caches quickly.
- Avoid manual edits to files inside `data_cache/`; use scripts to rewrite.
- Document schema changes inside `upgrade_spec.md` and update the header version constants.

For general workflow tips see `docs/USER_PLAYBOOK.md`; for runtime failures see `docs/TROUBLESHOOTING.md`.

