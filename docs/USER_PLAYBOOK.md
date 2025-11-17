# 🧭 User Playbook

Field guide for running the full workflow—from first-time setup to daily, monthly, and quarterly maintenance routines.

---

## 1. Initial Setup (≈5 minutes)

### 1️⃣ Install Dependencies
```bash
pip install pandas numpy yfinance matplotlib boto3 requests
```

### 2️⃣ Choose Your Data Source

**Option A: Yahoo Finance (Recommended for new users)**
- ✅ No configuration needed - works immediately
- ✅ Free and reliable
- ⚠️ Slower for large datasets (downloads ticker-by-ticker)

**Option B: Massive.com (Optional - for advanced users)**
- ⚠️ Requires paid subscription and AWS credentials
- ✅ Much faster for bulk historical downloads
- ✅ Can download years of data for thousands of tickers quickly

**To use Massive.com**, add credentials to `~/.aws/credentials`:
```ini
[massive]
aws_access_key_id = your-key-id
aws_secret_access_key = your-secret-key
```

Then validate connectivity:
```bash
python test_massive_bulk_single_day.py
```

> 💡 **New users**: Start with Yahoo Finance. You can always add Massive.com later if needed.

---

## 2. Build the Historical Cache

### Step 1 – Populate Cache

**Using Yahoo Finance (Recommended for new users)**
```bash
# Fast smoke test (1 month, ~2-5 minutes depending on number of tickers)
python populate_cache.py --all -m 1

# Full 24-month snapshot (~15-30 minutes depending on number of tickers)
python populate_cache.py --all -m 24

# Or populate a specific ticker file
python populate_cache.py -f stocks.txt -m 12
```

**Using Massive.com (Advanced users with credentials)**
```bash
# Fast smoke test (~30 seconds for 1 month)
python populate_cache_bulk.py --months 1

# Full 24-month snapshot (~8-10 minutes)
python populate_cache_bulk.py --months 24
```

**Key Differences:**
- Yahoo Finance: Downloads ticker-by-ticker, slower but no credentials needed
- Massive.com: Downloads daily files once (all tickers), much faster but requires subscription
- Both create identical cache format and work with all analysis tools
- Both are resumable and incremental—rerun to extend without duplication

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

1. **Update cache** (if needed):
   - Yahoo Finance: `python populate_cache.py --all -m 2`
   - Massive.com: `python populate_cache_bulk.py --months 2`
2. **Run core analysis**: `python vol_analysis.py AAPL`
3. **Review signal dashboard**: focus on Moderate Buy entries and exit warnings
4. **Log trades & notes**: capture key signals for journaling

---

## 4. Monthly Routine (30‑45 minutes)

1. **Refresh cache** with rolling 24‑month window:
   - Yahoo Finance: `python populate_cache.py --all -m 24`
   - Massive.com: `python populate_cache_bulk.py --months 24`
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
2. **Repopulate cache** with recent history:
   - Yahoo Finance: `python populate_cache.py -f stocks.txt -m 3`
   - Massive.com: `python populate_cache_bulk.py --months 3` (will include all tickers)
3. **Extract full history** if needed immediately:
   - Yahoo Finance users: Cache will be built on first analysis
   - Massive.com users: Extract from `massive_cache/` directory

---

## 7. Quick Reference Commands

```bash
# Populate cache (Yahoo Finance - recommended for new users)
python populate_cache.py --all -m 24

# Populate cache (Massive.com - advanced users)
python populate_cache_bulk.py --months 24

# Analyze single ticker
python vol_analysis.py MSFT --period 6mo

# Batch backtest
python batch_backtest.py -f stocks.txt -p 12mo

# Sector dashboard
python sector_dashboard.py --top 5 --compare
```

---

## 8. Time Investment Snapshot

| Activity | Frequency | Time | Notes |
|----------|-----------|------|-------|
| Initial setup (Yahoo) | Once | 5 min | Install dependencies only |
| Initial setup (Massive) | Once | 15 min | Install + AWS credentials + connectivity test |
| Full cache build (Yahoo) | Once per workspace | 15‑30 min | 24 months, ticker-by-ticker |
| Full cache build (Massive) | Once per workspace | 8‑10 min | 24 months, bulk download |
| Daily workflow | Trading days | 10‑15 min | Cache update + scans + journaling |
| Monthly maintenance | Monthly | 30‑45 min | Rolling cache, backtests, sector rotation |
| Quarterly audit | Quarterly | 1‑2 hr | Validation + archiving |

---

## 9. Best Practices Checklist

- **Start small**: Begin with 1‑month cache runs before attempting 24 months
- **Yahoo Finance users**: Expect 15-30 minutes for full 24-month cache build
- **Massive.com users**: Keep `massive_cache/` intact for quick historical extraction
- **Testing runs**: Use `--no-save-others` flag with Massive.com for faster iteration
- **Scheduling**: Run long batch jobs during off-peak hours
- **Validation**: Verify cache integrity (`wc -l data_cache/*.csv`) before critical backtests
- **Incremental updates**: Both tools support resumable downloads—rerun same command to update

---

Need help? See `docs/TROUBLESHOOTING.md` for failure scenarios and recovery steps.
