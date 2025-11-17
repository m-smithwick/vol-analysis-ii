# 🛠️ Troubleshooting & Best Practices

Centralized reference for diagnosing common failures and keeping caches healthy.

---

## 1. Common Issues

### Missing Dependencies
```
ModuleNotFoundError: No module named 'boto3'
```
Install all required dependencies:
```bash
pip install -r requirements.txt
```

### 403 Forbidden from Massive.com
```
ClientError: An error occurred (403) when calling GetObject
```
Possible causes: expired credentials, unsupported date range, or requesting same-day files too early.  
**Fix**: refresh credentials and rerun with older `--start/--end` dates.

### Weekend/Holiday Files
```
⊘ File not found (holiday/weekend)
```
Normal behavior—weekends and market holidays have no data. The script skips these automatically.

### Slow Performance (>2s/day)
- Saving entire market archive on spinning disk
- Running during peak network hours
- Competing CPU-heavy workloads

**Fixes**:
1. Use `--no-save-others` when you only need tracked tickers.
2. Close other heavy apps and rerun during off-peak times.
3. Start with shorter ranges (`--months 3`) to validate.

---

## 2. Debugging Options

Run scripts through the Python debugger or add temporary logging:
```bash
python -m pdb populate_cache_bulk.py --months 1
```

Use targeted prints around cache writes and S3 downloads to zero in on failures. Remove debug output after reproducing the issue.

---

## 3. Data Hygiene Commands

```bash
ls -lh data_cache/
du -sh data_cache/ massive_cache/
head -20 data_cache/AAPL_1d_data.csv
wc -l data_cache/*.csv
```
Use these regularly to confirm file sizes and row counts stay consistent.

---

## 4. Backup Strategy

```bash
tar -czf data_cache_backup_$(date +%Y%m%d).tar.gz data_cache/
tar -czf massive_cache_backup_$(date +%Y%m%d).tar.gz massive_cache/
```
Keep at least one off-machine copy before running destructive migrations.

---

## 5. Escalation Checklist

1. Re-run `python test_massive_bulk_single_day.py`
2. Confirm credentials in `~/.aws/credentials`
3. Verify free disk space (`df -h`)
4. Capture logs and open an issue

Need the operational routine instead? See `docs/USER_PLAYBOOK.md`.
