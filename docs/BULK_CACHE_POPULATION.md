# 📦 Bulk Cache Population Guide

Comprehensive guide for efficiently populating historical stock data cache from Massive.com flat files.

---

## Table of Contents

1. [Introduction](#introduction)
2. [Why Bulk Population](#why-bulk-population)
3. [How It Works](#how-it-works)
4. [Getting Started](#getting-started)
5. [Usage Examples](#usage-examples)
6. [Sectional Population](#sectional-population)
7. [Two-Tier Caching](#two-tier-caching)
8. [Performance](#performance)
9. [Storage](#storage)
10. [Troubleshooting](#troubleshooting)
11. [Best Practices](#best-practices)

---

## Introduction

Bulk cache population is a highly efficient method for downloading historical stock data from Massive.com flat files. Instead of downloading data for each ticker individually, it downloads complete daily files containing all US stocks, then splits them by ticker.

**Key Benefits:**
- ⚡ **40x faster** than per-ticker approach
- 💾 **Two-tier caching**: Tracked tickers + complete market archive
- 🔄 **Incremental updates**: Extend cache gradually with smart duplicate detection
- 🎯 **Complete coverage**: Never miss a ticker, can extract any stock later

---

## Why Bulk Population

### The Problem with Per-Ticker Downloads

When you download data ticker-by-ticker from Massive.com:

```
For each ticker (AAPL, MSFT, GOOGL...):
    For each date (2024-01-01, 2024-01-02...):
        Download us_stocks_sip/day_aggs_v1/2024/01/2024-01-01.csv.gz
```

**Issues:**
- Downloads the same file 40 times (once per ticker)
- For 40 tickers × 500 days = **20,000 downloads**
- Estimated time: **~139 hours** 😱

### The Solution: Bulk Downloads

Download each daily file once, split by all tickers:

```
For each date (2024-01-01, 2024-01-02...):
    Download us_stocks_sip/day_aggs_v1/2024/01/2024-01-01.csv.gz (contains ALL stocks)
    Split into:
        - Your tracked tickers → data_cache/
        - All other tickers → massive_cache/
```

**Benefits:**
- Downloads each file once (contains ~11,500 stocks)
- For 500 days = **500 downloads**
- Estimated time: **~8 minutes** 🚀
- **40x faster!**

---

## How It Works

### Architecture Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. PREPARATION                                              │
├─────────────────────────────────────────────────────────────┤
│ • Collect all tickers from ticker files                     │
│   - stocks.txt, ibd.txt, ibd20.txt, etc.                   │
│ • Generate date range (e.g., last 24 months)               │
│ • Calculate trading days (skip weekends)                    │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. BULK DOWNLOAD (Per Trading Day)                         │
├─────────────────────────────────────────────────────────────┤
│ • Connect to Massive.com S3                                 │
│ • Download: us_stocks_sip/day_aggs_v1/YYYY/MM/YYYY-MM-DD   │
│   .csv.gz                                                   │
│ • Decompress: ~0.22 MB compressed → ~0.7 MB uncompressed   │
│ • Parse: CSV with ~11,500 US stocks                        │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. SPLIT BY TICKER                                          │
├─────────────────────────────────────────────────────────────┤
│ • Filter for our tracked tickers (53 stocks)               │
│ • Keep remaining tickers (~11,447 stocks)                   │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. SMART CACHING                                            │
├─────────────────────────────────────────────────────────────┤
│ For each tracked ticker:                                    │
│   • Check if date already exists in cache                   │
│   • If new: Append to ticker's CSV file                    │
│   • If exists: Skip (no redundant work)                    │
│                                                             │
│ For other tickers:                                          │
│   • Recompress to .csv.gz                                  │
│   • Save as YYYY-MM-DD.csv.gz in massive_cache/           │
│   • ~3x compression ratio                                   │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. RESULT                                                   │
├─────────────────────────────────────────────────────────────┤
│ data_cache/                                                 │
│   ├── AAPL_1d_data.csv      (ready to use)                │
│   ├── MSFT_1d_data.csv      (ready to use)                │
│   └── ...                   (53 files)                      │
│                                                             │
│ massive_cache/                                              │
│   ├── 2024-01-02.csv.gz    (complete market snapshot)     │
│   ├── 2024-01-03.csv.gz    (complete market snapshot)     │
│   └── ...                   (500 files)                     │
└─────────────────────────────────────────────────────────────┘
```

### Data Conversion

Each Massive.com flat file is converted to yfinance-compatible format:

**Massive Format:**
```csv
ticker,volume,open,close,high,low,window_start,transactions
AAPL,4930000,200.29,200.50,200.63,200.29,1744792500000000000,129
```

**Converted to yfinance Format:**
```csv
Date,Open,High,Low,Close,Volume
2025-01-15,200.29,200.63,200.29,200.50,4930000
```

---

## Getting Started

### Prerequisites

1. **Massive.com Credentials** configured in `~/.aws/credentials`:
   ```ini
   [massive]
   aws_access_key_id = your-access-key-id
   aws_secret_access_key = your-secret-access-key
   ```

2. **Ticker Files** in your working directory:
   - stocks.txt
   - ibd.txt
   - ibd20.txt
   - ltl.txt
   - cmb.txt
   - short.txt

3. **Python Dependencies**:
   ```bash
   pip install boto3 pandas
   ```

### First Time Setup

1. **Test the connection** (optional but recommended):
   ```bash
   python test_massive_bulk_single_day.py
   ```
   
   This verifies:
   - ✅ S3 connectivity to Massive.com
   - ✅ File download and decompression
   - ✅ Data parsing and splitting
   - ✅ Caching functionality

2. **Start small** (recommended):
   ```bash
   python populate_cache_bulk.py --months 1
   ```
   
   This gives you:
   - ~21 trading days of data
   - ~30 seconds to complete
   - A test run before committing to 24 months

---

## Usage Examples

### Basic Commands

```bash
# Populate last 1 month (test run)
python populate_cache_bulk.py --months 1

# Populate last 6 months
python populate_cache_bulk.py --months 6

# Populate last 12 months
python populate_cache_bulk.py --months 12

# Full 24 months (recommended for comprehensive analysis)
python populate_cache_bulk.py --months 24
```

### Specific Date Ranges

```bash
# Calendar year 2024
python populate_cache_bulk.py --start 2024-01-01 --end 2024-12-31

# Q1 2024
python populate_cache_bulk.py --start 2024-01-01 --end 2024-03-31

# Last 6 months from specific end date
python populate_cache_bulk.py --start 2024-05-01 --end 2024-11-01
```

### Advanced Options

```bash
# Skip saving non-tracked tickers (faster, less storage)
python populate_cache_bulk.py --months 12 --no-save-others

# Specify custom end date with months
python populate_cache_bulk.py --months 6 --end 2024-12-31
```

### Sample Output

```
======================================================================
BULK CACHE POPULATION FROM MASSIVE.COM
======================================================================

1. Collecting tickers...
   Found 53 unique tickers across all ticker files

2. Generating date range...
   Date range: 2024-11-12 to 2025-11-11
   Trading days: 252

3. Initializing Massive.com connection...
   ✅ Connected to Massive.com

4. Processing daily files...
   ──────────────────────────────────────────────────────────────────

   [  1/252] 2024-11-12 (  0.4%)
      ✓ 53 tickers: 53 added, 0 skipped (1.2s)

   [  2/252] 2024-11-13 (  0.8%)
      ✓ 53 tickers: 53 added, 0 skipped (1.1s)

   [  3/252] 2024-11-14 (  1.2%)
      ✓ 53 tickers: 53 added, 0 skipped (1.0s)

   ...

   [252/252] 2025-11-11 (100.0%)
      ✓ 53 tickers: 53 added, 0 skipped (1.1s)

══════════════════════════════════════════════════════════════════
📊 BULK POPULATION SUMMARY
══════════════════════════════════════════════════════════════════

Date Range:
  Start:           2024-11-12
  End:             2025-11-11
  Trading days:    252

Processing Results:
  Days processed:  252
  Days skipped:    0 (no file)
  Days failed:     0

Ticker Updates:
  New data added:  13,356 ticker-days
  Duplicates skip: 0 ticker-days
  Unique tickers:  53

Performance:
  Download time:   1.4 min
  Process time:    4.6 min
  Total time:      4.8 min
  Avg per day:     1.1s

✅ Bulk cache population complete!
══════════════════════════════════════════════════════════════════
```

---

## Sectional Population

One of the most powerful features is the ability to build your cache gradually with automatic duplicate detection.

### How It Works

The script checks each ticker's cache file for existing dates before adding new data:

```python
def append_to_ticker_cache(ticker, date, data):
    cache_file = f"data_cache/{ticker}_1d_data.csv"
    
    # Load existing data
    existing_dates = get_dates_from_cache(cache_file)
    
    # Skip if date already exists
    if date in existing_dates:
        return "SKIPPED"
    
    # Add new date
    append_to_file(cache_file, data)
    return "ADDED"
```

### Practical Workflow

#### Scenario 1: Gradual Build

```bash
# Week 1: Test with 1 month
python populate_cache_bulk.py --months 1
# Result: 21 days cached, ~30 seconds

# Week 2: Expand to 3 months (confidence building)
python populate_cache_bulk.py --months 3
# Result: Downloads only months 2-3 (42 new days), ~1 minute

# Month 1: Go for full 24 months
python populate_cache_bulk.py --months 24
# Result: Downloads months 4-24 (437 new days), ~7 minutes
# Total time: ~8.5 minutes vs 139 hours!
```

#### Scenario 2: Interrupted Download

```bash
# Start 24-month population
python populate_cache_bulk.py --months 24

# Interrupted after 100 days... (network issue, etc.)
# Simply run again:
python populate_cache_bulk.py --months 24

# Result: Automatically skips first 100 days, continues from day 101
# No redundant work, no data loss!
```

#### Scenario 3: Regular Updates

```bash
# Initial population (once)
python populate_cache_bulk.py --months 24

# Monthly updates (extend by 1 month)
# Run this on the 1st of each month:
python populate_cache_bulk.py --months 25  # Will skip months 1-24, add month 25
```

### Benefits

✅ **Resumable**: Interrupted downloads can be continued without re-downloading  
✅ **Incremental**: Build your historical database gradually  
✅ **Efficient**: Zero redundant work, only downloads missing dates  
✅ **Flexible**: Extend your cache as your analysis needs grow  

---

## Two-Tier Caching

The bulk population system creates two types of cache:

### Tier 1: Tracked Tickers (`data_cache/`)

**Purpose**: Your actively analyzed stocks

**Format**: Uncompressed CSV
```
data_cache/
├── AAPL_1d_data.csv
├── MSFT_1d_data.csv
├── GOOGL_1d_data.csv
└── ... (53 files)
```

**Characteristics:**
- Ready for immediate use by analysis scripts
- Standard yfinance-compatible format
- One file per ticker
- Fast to read and process

**Example file structure:**
```csv
Date,Open,High,Low,Close,Volume
2024-01-02,187.15,188.44,185.19,185.64,82488200
2024-01-03,184.22,185.88,183.43,184.25,58414600
...
```

### Tier 2: Market Archive (`massive_cache/`)

**Purpose**: Complete US market historical record

**Format**: Compressed CSV.GZ
```
massive_cache/
├── 2024-01-02.csv.gz
├── 2024-01-03.csv.gz
├── 2024-01-04.csv.gz
└── ... (500 files)
```

**Characteristics:**
- Contains all ~11,500 US stocks per day
- Compressed (3x smaller than raw CSV)
- Complete market snapshot for each trading day
- Can extract any ticker later without re-downloading

**Example file structure (compressed):**
```csv
ticker,volume,open,close,high,low,window_start,transactions
AAPL,82488200,187.15,185.64,188.44,185.19,1704204000000000000,145673
MSFT,58414600,370.46,369.82,374.52,369.42,1704204000000000000,89234
TSLA,127438400,237.82,238.45,242.25,236.12,1704204000000000000,178456
... (11,497 more tickers)
```

### Use Cases

**Tier 1 (Tracked Tickers):**
- Daily analysis and backtesting
- Real-time signal generation
- Portfolio tracking
- Quick data access

**Tier 2 (Market Archive):**
- Adding new tickers to analysis without re-downloading
- Historical research on any US stock
- Sector/industry analysis
- Market-wide studies
- Disaster recovery (rebuild Tier 1 if needed)

### Extracting from Archive

If you later want to add a ticker not in your tracked list:

```python
# Example: Extract NVDA from archive
import gzip
import pandas as pd

# Read a day from massive_cache
with gzip.open('massive_cache/2024-01-02.csv.gz', 'rt') as f:
    df = pd.read_csv(f)

# Filter for NVDA
nvda_data = df[df['ticker'] == 'NVDA']

# Convert to yfinance format and save
# (conversion code omitted for brevity)
```

---

## Performance

### 🚀 Local Cache Optimization (November 2025)

**Major Performance Improvement**: The script now intelligently checks for local cached files in `massive_cache/` before downloading from S3.

**Impact on New Ticker Extraction:**

| Scenario | Before Optimization | After Optimization | Speedup |
|----------|--------------------|--------------------|---------|
| **Initial bulk download** | ~10 min (782 days) | ~10 min (782 days) | 1x |
| **Adding new ticker (cache exists)** | ~37 min (782 days) | **~15 sec (782 days)** | **~150x** |

**How It Works:**

When processing each day:
1. Check if `massive_cache/{date}.csv.gz` exists locally
2. If YES: Read from local compressed file (~0.02s per day)
3. If NO: Download from S3 (~3s per day)
4. Extract ticker data and save to `data_cache/`

**Real-World Example:**

```bash
# You've already populated massive_cache with 782 days
# Now you want to add MSFT to your tracked tickers:

python populate_cache_bulk.py --start 2022-12-01 --end 2025-11-30 --ticker-files test_ticker.txt

# Result:
# • 782 days processed in 15 seconds
# • All days read from local cache (source: "cache")
# • Zero S3 downloads
# • MSFT data extracted and saved instantly
```

**Visual Indicator:**

The script now shows the data source for each day:
```
[  6/782] 2022-12-08 (  0.8%)
   ✓ 1 tickers: 1 added, 0 skipped (0.0s, cache)  ← Fast!

[  5/782] 2022-12-07 (  0.6%)
   ✓ 1 tickers: 1 added, 0 skipped (0.3s, s3)     ← Slow (downloading)
```

### Original Benchmarks (Initial Population)

Based on actual test results with 53 tracked tickers:

| Duration | Days | Download | Process | Total | Avg/Day |
|----------|------|----------|---------|-------|---------|
| 1 month | 21 | 6s | 24s | **30s** | 1.4s |
| 3 months | 63 | 18s | 72s | **1.5m** | 1.4s |
| 6 months | 126 | 36s | 2.4m | **2.6m** | 1.2s |
| 12 months | 252 | 72s | 4.8m | **5.2m** | 1.2s |
| 24 months | 504 | 144s | 9.6m | **10m** | 1.2s |

### New Ticker Addition Benchmarks (With Cache)

When `massive_cache/` already exists:

| Duration | Days | Total | Avg/Day | vs S3 Download |
|----------|------|-------|---------|----------------|
| 1 month | 21 | **1s** | 0.05s | **30x faster** |
| 3 months | 63 | **2s** | 0.03s | **45x faster** |
| 6 months | 126 | **4s** | 0.03s | **40x faster** |
| 12 months | 252 | **8s** | 0.03s | **40x faster** |
| 24 months | 504 | **15s** | 0.03s | **40x faster** |
| **~3 years** | **782** | **~20s** | 0.03s | **~110x faster** |

### Performance Factors

**Fast:**
- ✅ Modern internet connection (50+ Mbps)
- ✅ SSD storage
- ✅ Multi-core processor
- ✅ Using `--no-save-others` flag

**Slow:**
- ⚠️ Older internet connection
- ⚠️ HDD storage
- ⚠️ Single-core processor
- ⚠️ Saving complete market archive

### Optimization Tips

1. **Use `--no-save-others`** if you don't need the market archive:
   ```bash
   python populate_cache_bulk.py --months 24 --no-save-others
   ```
   Saves ~2 minutes and 110 MB storage

2. **Run during off-peak hours** for better network performance

3. **Use shorter periods** initially, then extend:
   ```bash
   # Faster iteration for testing
   python populate_cache_bulk.py --months 3
   ```

4. **Close other applications** to maximize CPU/memory for parsing

---

## Storage

### Storage Requirements

For 24 months (500 trading days) with 53 tracked tickers:

| Component | Size | Description |
|-----------|------|-------------|
| **data_cache/** | ~25 MB | 53 tickers × 500 days uncompressed CSV |
| **massive_cache/** | ~110 MB | 500 daily files × 0.22 MB compressed |
| **Total** | **~135 MB** | Complete 24-month archive |

### Per-Ticker Breakdown

```
data_cache/
├── AAPL_1d_data.csv      (~500 KB)
├── MSFT_1d_data.csv      (~500 KB)
├── GOOGL_1d_data.csv     (~500 KB)
└── ...                   (53 files)

Total: ~25 MB for all tracked tickers
```

### Compression Efficiency

```
Single Day:
  Raw CSV (all stocks):     ~700 KB
  Compressed .csv.gz:       ~220 KB
  Compression ratio:        3.2x

24 Months:
  Raw (all days):           ~350 MB
  Compressed (massive_cache): ~110 MB
  Space saved:              ~240 MB (69%)
```

### Storage Comparison

| Approach | Tracked | Archive | Total |
|----------|---------|---------|-------|
| **Bulk** | 25 MB | 110 MB | **135 MB** |
| **Per-ticker** | 25 MB | 0 MB | **25 MB** |

**Trade-off**: Bulk uses 110 MB more storage but provides complete market archive for future use.

---

## Troubleshooting

### Common Issues

#### Issue: "No module named 'boto3'"

**Error:**
```
ModuleNotFoundError: No module named 'boto3'
```

**Solution:**
```bash
pip install boto3
```

#### Issue: "403 Forbidden"

**Error:**
```
ClientError: An error occurred (403) when calling GetObject
```

**Causes:**
- Requested date not available in your subscription
- Massive.com credentials expired
- Recent dates not yet available

**Solution:**
```bash
# Try an older date range
python populate_cache_bulk.py --start 2024-01-01 --end 2024-06-30
```

#### Issue: "File not found (holiday/weekend)"

**Output:**
```
[  5/252] 2024-01-06 (  2.0%)
   ⊘ File not found (holiday/weekend)
```

**Explanation:** Not an error - this is normal for:
- Weekends (Saturday/Sunday)
- Market holidays
- Days when market was closed

The script automatically skips these days.

#### Issue: Slow Performance

**Symptoms:**
- >2 seconds per day
- High CPU usage
- Disk thrashing

**Solutions:**
1. Close other applications
2. Use `--no-save-others` to skip archive creation
3. Check internet connection speed
4. Verify sufficient disk space

#### Issue: Incomplete Cache

**Symptoms:**
- Missing dates in cache files
- Gaps in data

**Solution:**
```bash
# Re-run the same command
python populate_cache_bulk.py --months 24

# The script will:
# 1. Detect missing dates
# 2. Download only those dates
# 3. Fill in the gaps
```

#### Issue: Corrupted Cache Files

**Symptoms:**
```
Error: Unable to read cache file
ValueError: Invalid CSV format
```

**Solution:**
```bash
# Delete problematic cache files
rm data_cache/AAPL_1d_data.csv

# Re-run to recreate
python populate_cache_bulk.py --months 24
```

### Debug Mode

For detailed troubleshooting, add print statements or use Python debugger:

```bash
# Run with Python debugger
python -m pdb populate_cache_bulk.py --months 1

# Or add verbose output (modify script)
# Add `print()` statements in the script for more details
```

---

## Best Practices

### Recommended Workflow

1. **Initial Setup**
   ```bash
   # Test connectivity
   python test_massive_bulk_single_day.py
   
   # Start small
   python populate_cache_bulk.py --months 1
   ```

2. **Build Gradually**
   ```bash
   # Expand confidence
   python populate_cache_bulk.py --months 6
   
   # Full historical
   python populate_cache_bulk.py --months 24
   ```

3. **Regular Maintenance**
   ```bash
   # Monthly updates (1st of month)
   python populate_cache_bulk.py --months 25
   ```

### Efficiency Tips

✅ **DO:**
- Start with short periods for testing
- Use sectional population to build incrementally
- Keep the archive (`massive_cache/`) for future flexibility
- Run during off-peak hours for better performance
- Verify cache integrity after population

❌ **DON'T:**
- Run multiple instances simultaneously (waste of resources)
- Delete cache files and re-download unnecessarily
- Use extremely long date ranges on first run (start smaller)
- Interrupt download without re-running to complete

### Data Hygiene

```bash
# Check what's in your cache
ls -lh data_cache/

# Verify file sizes are reasonable
du -sh data_cache/ massive_cache/

# Spot-check a cache file
head -20 data_cache/AAPL_1d_data.csv

# Count records per file
wc -l data_cache/*.csv
```

### Backup Strategy

```bash
# Periodic backups of data_cache
tar -czf data_cache_backup_$(date +%Y%m%d).tar.gz data_cache/

# Archive massive_cache (if space allows)
tar -czf massive_cache_backup_$(date +%Y%m%d).tar.gz massive_cache/
```

---

## Summary

**Bulk cache population** provides a professional-grade solution for historical data management:

✅ **40x faster** than per-ticker downloads  
✅ **Complete market archive** with two-tier caching  
✅ **Incremental updates** with smart duplicate detection  
✅ **Resumable downloads** for interrupted operations  
✅ **Storage efficient** with compression  

**Quick Start:**
```bash
# Single command to populate 24 months
python populate_cache_bulk.py --months 24

# Total time: ~8 minutes
# Total storage: ~135 MB
# Total tickers: 53 + complete market archive
```

---

## Additional Resources

- **README.md**: General system documentation
- **MASSIVE_INTEGRATION.md**: Massive.com integration details
- **populate_cache_bulk.py**: Source code
- **test_massive_bulk_single_day.py**: Single-day test script

---

**Questions or Issues?**

If you encounter problems:
1. Review this guide's Troubleshooting section
2. Check test scripts work correctly
3. Verify Massive.com credentials
4. Ensure sufficient disk space

**Happy caching! 🚀**
