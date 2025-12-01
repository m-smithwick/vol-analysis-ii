# 🧭 User Playbook

Field guide for running the full workflow—from first-time setup to daily, monthly, and quarterly maintenance routines.

---

## 1. Initial Setup (≈5-15 minutes)

### 1️⃣ Install Dependencies
```bash
pip install -r requirements.txt
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

### 3️⃣ Optional: DuckDB Optimization (Advanced - 10-20x faster)

**For Massive.com users only** - Enables ultra-fast cache population:

```bash
# Build DuckDB index once (30-60 seconds, one-time operation)
python scripts/build_massive_index.py

# Verify it worked
python scripts/query_massive_index.py --stats
```

This creates a SQL-indexed database of your massive_cache/ for instant queries.
Now use `--use-duckdb` flag with populate_cache_bulk.py (see next section).

📖 **Full details**: `docs/DUCKDB_OPTIMIZATION.md`

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
# Standard mode (~8-10 minutes for 24 months)
# Default: uses stocks.txt only
python populate_cache_bulk.py --months 24

# Specify different ticker files
python populate_cache_bulk.py --months 24 --ticker-files ibd20.txt alt.txt

# Fast mode with DuckDB (if index built - ~1 minute for 24 months!)
python populate_cache_bulk.py --months 24 --use-duckdb
python populate_cache_bulk.py --months 24 --ticker-files ibd20.txt --use-duckdb
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

## 4. Monthly Routine (45-60 minutes)

### Workflow: Sector Analysis → Ticker Selection → Validation

**Step 1: Refresh Cache (5-10 min)**
```bash
# Yahoo Finance
python populate_cache.py --all -m 24

# Massive.com (standard - uses stocks.txt by default)
python populate_cache_bulk.py --months 24

# Massive.com (fast mode - if DuckDB index built)
python populate_cache_bulk.py --months 24 --use-duckdb

# Or specify which ticker files to refresh
python populate_cache_bulk.py --months 24 --ticker-files ibd20.txt alt.txt --use-duckdb
```

**Step 2: Sector Rotation Analysis (15-20 min)**
```bash
# Identify strongest sectors
python sector_dashboard.py --top 5 --compare

# Deep dive with backtests on top sectors
python sector_dashboard_with_backtest.py --top 3

# Review sector_cache/sector_dashboard_*.txt for detailed metrics
```

**Key questions to answer:**
- Which sectors are showing strongest momentum?
- Are my current holdings in strong or weak sectors?
- Should I rotate capital to stronger sectors?

**Step 3: Update Ticker Selection (10-15 min)**

Based on sector analysis:
```bash
# Example: Create new watchlist from strong sectors
# If XLK (Tech) and XLF (Financial) are strong:
cat ticker_lists/tech_leaders.txt ticker_lists/financial_leaders.txt > ticker_lists/current_watchlist.txt

# Or manually edit to:
# - Add tickers from strong sectors
# - Reduce/remove tickers from weak sectors
# - Maintain 15-25 ticker diversification
```

**Step 4: Validate with Backtests (15-20 min)**
```bash
# Test your updated watchlist
python batch_backtest.py -f ticker_lists/current_watchlist.txt -p 12mo

# Compare configurations if needed
python batch_config_test.py -c configs/balanced_config.yaml configs/conservative_config.yaml \
  -f ticker_lists/current_watchlist.txt
```

**Review metrics:**
- Win rate and expectancy
- Maximum drawdown
- Sharpe ratio
- Per-sector contribution to returns

**Step 5: Document & Adjust (5 min)**
- Log sector rotation decisions
- Note why specific tickers were added/removed
- Update stop-loss settings if needed
- Archive old watchlists for future reference

### Monthly Maintenance Checklist

- [ ] Cache refreshed (24-month window)
- [ ] Sector dashboard reviewed
- [ ] Watchlist updated based on sector strength
- [ ] Backtests validated new watchlist
- [ ] Changes documented
- [ ] Old artifacts archived

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
   - Massive.com (standard): `python populate_cache_bulk.py --months 3`
   - Massive.com (fast): `python populate_cache_bulk.py --months 3 --use-duckdb`
3. **Extract full history** if needed immediately:
   - Yahoo Finance users: Cache will be built on first analysis
   - Massive.com users: Data already in massive_cache/, just extract to data_cache/

---

## 7. Quick Reference Commands

```bash
# Populate cache (Yahoo Finance - recommended for new users)
python populate_cache.py --all -m 24

# Populate cache (Massive.com - standard)
python populate_cache_bulk.py --months 24

# Populate cache (Massive.com - fast mode, 10-20x faster)
python populate_cache_bulk.py --months 24 --use-duckdb

# Analyze single ticker
python vol_analysis.py MSFT --period 6mo

# Batch backtest
python batch_backtest.py -f stocks.txt -p 12mo

# Sector rotation analysis
python sector_dashboard.py --top 5 --compare
python sector_dashboard_with_backtest.py --top 3
```

---

## 8. Time Investment Snapshot

| Activity | Frequency | Time | Notes |
|----------|-----------|------|-------|
| Initial setup (Yahoo) | Once | 5 min | Install dependencies only |
| Initial setup (Massive) | Once | 15 min | Install + AWS credentials + connectivity test |
| Initial setup (DuckDB) | Once | 1 min | Build index (optional, for 10-20x speedup) |
| Full cache build (Yahoo) | Once per workspace | 15‑30 min | 24 months, ticker-by-ticker |
| Full cache build (Massive) | Once per workspace | 8‑10 min | 24 months, bulk download |
| Full cache build (Massive+DuckDB) | Once per workspace | ~1 min | 24 months, indexed queries |
| Daily workflow | Trading days | 10‑15 min | Cache update + scans + journaling |
| Monthly maintenance | Monthly | 45‑60 min | Cache, sector analysis, ticker rotation, backtests |
| Quarterly audit | Quarterly | 1‑2 hr | Validation + archiving |

---

## 9. Best Practices Checklist

- **Start small**: Begin with 1‑month cache runs before attempting 24 months
- **Yahoo Finance users**: Expect 15-30 minutes for full 24-month cache build
- **Massive.com users**: Keep `massive_cache/` intact for quick historical extraction
- **DuckDB optimization**: Build index once, then use `--use-duckdb` for 10-20x speedup
- **Default ticker list**: `populate_cache_bulk.py` uses `stocks.txt` by default—specify others with `--ticker-files`
- **Testing runs**: Use `--no-save-others` flag with Massive.com for faster iteration
- **Scheduling**: Run long batch jobs during off-peak hours
- **Validation**: Verify cache integrity (`wc -l data_cache/*.csv`) before critical backtests
- **Incremental updates**: Both tools support resumable downloads—rerun same command to update
- **Sector rotation**: Review sector strength monthly, rotate capital to strong sectors
- **Workflow discipline**: Always validate watchlist changes with backtests before live trading

---

## 10. Multi-Computer Workflow (≈10-15 minutes per computer)

### What Syncs via Git vs What Doesn't

**✅ Synced automatically (in git):**
- All Python code
- Ticker lists (ticker_lists/*.txt)
- Configuration files (configs/*.yaml)
- Documentation

**❌ NOT synced (in .gitignore):**
- `data_cache/` (your processed cache files)
- `massive_cache/` (raw Massive.com downloads)
- `massive_index.duckdb` (DuckDB index)
- `backtest_results/`
- All output directories

### Setting Up on a New Computer

**Step 1: Clone and install**
```bash
git clone <your-repo-url>
cd vol-analysis-ii
pip install -r requirements.txt
```

**Step 2: Choose cache population approach**

**Option A: Yahoo Finance (Simplest - no credentials needed)**
```bash
# Populates from Yahoo Finance for all tickers
python populate_cache.py --all -m 24
```

**Option B: Massive.com (Requires AWS credentials setup)**
1. Configure AWS credentials on new computer (see Section 1)
2. Populate massive_cache (default: uses stocks.txt only):
   ```bash
   # Default: populates stocks.txt
   python populate_cache_bulk.py --months 24
   
   # Or specify which ticker lists to populate
   python populate_cache_bulk.py --months 24 --ticker-files stocks.txt ibd20.txt alt.txt
   ```
3. Build DuckDB index (optional, for 10-20x speedup):
   ```bash
   python scripts/build_massive_index.py
   ```
4. Populate data_cache with fast mode:
   ```bash
   python populate_cache_bulk.py --months 24 --use-duckdb
   ```

### Keeping Caches in Sync

**Daily updates work the same on each computer:**
```bash
# Pull latest code and ticker lists
git pull

# Update cache (uses stocks.txt by default)
python populate_cache_bulk.py --months 1

# Or with fast mode
python populate_cache_bulk.py --months 1 --use-duckdb
```

**⚠️ Important:** If you add new ticker lists on Computer A:
1. Commit and push: `git add ticker_lists/new_list.txt && git commit && git push`
2. On Computer B: `git pull` (gets new ticker list)
3. Populate for new list: `python populate_cache_bulk.py --months 24 --ticker-files new_list.txt`

### Alternative: Share massive_cache/ (Advanced)

If you have a shared network drive or NAS:
1. Keep one central copy of `massive_cache/` (saves ~5-10 GB per computer)
2. Symlink to it from each computer:
   ```bash
   ln -s /path/to/shared/massive_cache massive_cache
   ```
3. Build DuckDB index separately on each computer:
   ```bash
   python scripts/build_massive_index.py
   ```
4. Each computer maintains its own `data_cache/` and `massive_index.duckdb`

**Benefits:**
- Download massive_cache/ once, use on all computers
- Save network bandwidth and storage space
- Faster setup on new computers

**Considerations:**
- Network performance affects query speed
- Each computer needs its own DuckDB index
- Best for home networks with fast NAS

---

Need help? See `docs/TROUBLESHOOTING.md` for failure scenarios and recovery steps.
