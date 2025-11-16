# 🧭 User Playbook

Field guide for running the full workflow—from first-time setup to daily, monthly, and quarterly maintenance routines.

---

## 1. Initial Setup (≈15 minutes)

### 1️⃣ Install Dependencies
```bash
pip install pandas numpy yfinance matplotlib boto3
```

### 2️⃣ Configure Massive.com Credentials (optional but highly recommended)
Add credentials to `~/.aws/credentials`:
```ini
[massive]
aws_access_key_id = your-key-id
aws_secret_access_key = your-secret-key
```

### 3️⃣ Validate Connectivity
```bash
python test_massive_bulk_single_day.py
```
Confirms S3 access, file download/decompression, ticker splitting, and cache writes.

---

## 2. Build the Historical Cache

### Step 1 – Populate Cache (~10 minutes)
```bash
# Fast smoke test
python populate_cache_bulk.py --months 1

# Full 24-month snapshot
python populate_cache_bulk.py --months 24
```
- Downloads daily Massive.com files once and splits by ticker
- Resumable and incremental—rerun to extend without duplication

### Step 2 – Organize Ticker Lists (~5 minutes)
Create watchlists with one ticker per line:
```bash
cat > stocks.txt <<'EOF'
AAPL
MSFT
GOOGL
NVDA
TSLA
EOF
```
Maintain additional lists (`ibd.txt`, `ibd20.txt`, `sector_etfs.txt`, etc.) for scans and sector workflows.

### Step 3 – Validate Strategy with Backtests (~30 minutes)
```bash
python batch_backtest.py -f stocks.txt -p 12mo
python batch_backtest.py -f ibd.txt -p 12mo
```
Review win rates, expectancy, and exit behavior before trusting signals with capital.

---

## 3. Daily Routine (10‑15 minutes)

1. **Update cache** (if needed): `python populate_cache_bulk.py --months 2`
2. **Run core analysis**: `python vol_analysis.py --ticker AAPL`
3. **Review signal dashboard**: focus on Moderate Buy entries and exit warnings
4. **Log trades & notes**: capture key signals for journaling

---

## 4. Monthly Routine (30‑45 minutes)

1. Refresh cache with rolling 24‑month window
2. Run batch backtests for tracked lists to confirm signal health
3. Audit stop-loss performance and update configs if necessary
4. Rotate sector allocations using `sector_dashboard.py`

---

## 5. Quarterly Deep Dive (1‑2 hours)

1. Re-run out-of-sample validation scripts
2. Update `docs/VALIDATION_STATUS.md` with new findings
3. Evaluate stealth ranking changes and new tickers
4. Archive prior quarter’s cache/backtest artifacts

---

## 6. Adding New Tickers (≈5 minutes)

1. Append ticker to appropriate list (`stocks.txt`, `ltl.txt`, etc.)
2. Rerun bulk population with `--months 3` (fast catch-up)
3. Extract historical data from `massive_cache/` if full history is needed immediately

---

## 7. Quick Reference Commands

```bash
# Populate cache
python populate_cache_bulk.py --months 24

# Analyze single ticker
python vol_analysis.py --ticker MSFT --period 6mo

# Batch backtest
python batch_backtest.py -f stocks.txt -p 12mo

# Sector dashboard
python sector_dashboard.py --top 5 --compare
```

---

## 8. Time Investment Snapshot

| Activity | Frequency | Time | Notes |
|----------|-----------|------|-------|
| Initial setup | Once | 15 min | Install + credentials + smoke test |
| Full cache build | Once per workspace | 8‑10 min | 24 months of history |
| Daily workflow | Trading days | 10‑15 min | Cache update + scans + journaling |
| Monthly maintenance | Monthly | 30‑45 min | Rolling cache, backtests, sector rotation |
| Quarterly audit | Quarterly | 1‑2 hr | Validation + archiving |

---

## 9. Best Practices Checklist

- Start with 1‑month cache runs before attempting 24 months
- Keep `massive_cache/` intact for quick historical extraction
- Use `--no-save-others` for faster testing runs
- Run long batch jobs during off-peak hours
- Verify cache integrity (`wc -l data_cache/*.csv`) before critical backtests

---

Need help? See `docs/TROUBLESHOOTING.md` for failure scenarios and recovery steps.

