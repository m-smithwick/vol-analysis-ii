# End-of-Day Data Workflow for Trading

**Last Updated**: 2025-11-24  
**Use Case**: Get EOD data each evening to analyze for next-day opening trades

---

## Your Trading Workflow

### Timeline
1. **Market Close**: 1:00 PM PT / 4:00 PM ET
2. **Data Refresh**: Evening (after market close)
3. **Analysis**: Overnight
4. **Execute Trades**: Next day at market open

### Requirements
- ✅ End-of-day OHLC data (daily bars)
- ✅ Available same evening after market close
- ✅ Includes SPY + all 11 sector ETFs for regime filtering
- ✅ Updates cache for backtesting/analysis

---

## The Correct Solution: Flat Files via S3

### Why Flat Files?

**✅ Perfect for EOD Trading:**
- Available end-of-day (T+0) after market close
- Provides complete daily OHLC bars
- Bulk download is faster than per-ticker API calls
- Already included in your subscription
- Reliable and consistent

**Use `populate_cache_bulk.py`** - this is your production workflow!

### Daily Update Command

**Run every evening after market close:**

```bash
# Update today's data for regime filtering (SPY + sectors)
python populate_cache_bulk.py --start $(date +%Y-%m-%d) --end $(date +%Y-%m-%d) \
  --ticker-files ticker_lists/indices.txt ticker_lists/sector_etfs.txt

# Update your trading universe
python populate_cache_bulk.py --start $(date +%Y-%m-%d) --end $(date +%Y-%m-%d) \
  --ticker-files ticker_lists/stocks.txt
```

Or manually:
```bash
# Monday evening (2025-11-24):
python populate_cache_bulk.py --start 2025-11-24 --end 2025-11-24 \
  --ticker-files ticker_lists/indices.txt ticker_lists/sector_etfs.txt ticker_lists/stocks.txt
```

### Automation (Recommended)

Create a cron job to run daily at 5:00 PM PT (1 hour after market close):

```bash
# Add to crontab (run: crontab -e)
0 17 * * 1-5 cd /Users/jimknapik/py37/vol-analysis-ii && python populate_cache_bulk.py --start $(date +\%Y-\%m-\%d) --end $(date +\%Y-\%m-\%d) --ticker-files ticker_lists/indices.txt ticker_lists/sector_etfs.txt ticker_lists/stocks.txt >> logs/cache_update.log 2>&1
```

This runs Monday-Friday at 5 PM PT automatically.

---

## Why NOT REST API?

### `refresh_cache_rest.py` Limitations

The REST API script (`refresh_cache_rest.py`) was created to solve Yahoo Finance weekend issues, but has critical limitations:

**❌ Doesn't Work for Your Use Case:**
- Requires Developer/Advanced subscription tier (not included in Starter)
- "15-minute delayed" refers to intraday streaming, not daily aggregates
- REST aggregates endpoint returns "DELAYED" status with Starter plan
- Slower (per-ticker API calls vs bulk download)
- Unnecessary complexity for EOD data

**When REST API Would Be Useful:**
- If you needed **intraday data** (1-minute, 5-minute bars)
- If you needed **real-time/near-real-time** updates during market hours
- If you had **Developer/Advanced subscription**

**Your use case (EOD data for next-day trading) doesn't need REST API.**

---

## Data Availability Timeline

### Massive.com Flat Files (S3)
- **Available**: End of trading day (typically by 6 PM ET / 3 PM PT)
- **Latency**: T+0 (same day)
- **Format**: Complete daily OHLC bars
- **Your Access**: ✅ Included in subscription

### Yahoo Finance (Fallback Only)
- **Available**: Variable (unreliable on weekends)
- **Issues**: Rate limiting, weekend failures, API instability
- **Use**: Only as emergency fallback, not primary source

---

## Solving the Original Problem

### The Issue
Yahoo Finance API is unreliable on weekends and after hours, causing your batch backtests to fail with errors like:
```
JSONDecodeError('Expecting value: line 1 column 1 (char 0)')
YFTzMissingError('$%ticker%: possibly delisted; No timezone found')
```

### The Solution
**Don't use Yahoo Finance for regime data updates.** Use flat files:

```bash
# Monday evening - update SPY + sectors from reliable source
python populate_cache_bulk.py --start 2025-11-24 --end 2025-11-24 \
  --ticker-files ticker_lists/indices.txt ticker_lists/sector_etfs.txt

# Now your backtest won't hit Yahoo API for regime data
python batch_backtest.py --ticker-files ticker_lists/stocks.txt
```

Cache is fresh → No Yahoo API calls → No weekend errors → Analysis runs clean.

---

## Recommended Workflow

### Daily Routine (Automated)

**5:00 PM PT** - Cron job runs:
```bash
populate_cache_bulk.py --start $(date +%Y-%m-%d) --end $(date +%Y-%m-%d)
```

**6:00 PM PT** - Run your analysis:
```bash
python batch_backtest.py --ticker-files ticker_lists/stocks.txt
python vol_analysis.py SPY  # Check regime status
```

**Evening** - Review results, plan next day's trades

**Next Morning** - Execute trades at open based on EOD analysis

### Weekly Maintenance

**Sunday evening** - Catch up on any missed data:
```bash
# Get last week of data
python populate_cache_bulk.py --start 2025-11-18 --end 2025-11-24 \
  --ticker-files ticker_lists/indices.txt ticker_lists/sector_etfs.txt ticker_lists/stocks.txt
```

### Monthly Maintenance

**First Sunday of month** - Full refresh:
```bash
# Extend cache with last month's data
python populate_cache_bulk.py --months 1 \
  --ticker-files ticker_lists/indices.txt ticker_lists/sector_etfs.txt ticker_lists/stocks.txt
```

---

## File Inventory

### Production Scripts
- ✅ **`populate_cache_bulk.py`** - Use this for EOD data updates
- ✅ **`batch_backtest.py`** - Your backtest framework
- ✅ **`vol_analysis.py`** - Single ticker analysis

### Not Recommended for Production
- ❌ **`refresh_cache_rest.py`** - Requires higher subscription tier
  - Status: Available but non-functional with Starter plan
  - Keep for reference or future upgrade
  - Do not use in daily workflow

### Configuration Files
- `ticker_lists/indices.txt` - SPY and market indices
- `ticker_lists/sector_etfs.txt` - 11 sector ETFs for regime filtering
- `ticker_lists/stocks.txt` - Your trading universe
- `massive_api_key.txt` - REST API key (not used in EOD workflow)
- `~/.aws/credentials` - S3 credentials for flat files (active)

---

## Troubleshooting

### "No file found" on same day
**Symptom**: `populate_cache_bulk.py` reports "File not found" for today's date  
**Cause**: Flat files not yet published (typically available by 6 PM ET)  
**Solution**: Wait 30 minutes and retry, or run tomorrow for today's data

### Yahoo Finance errors in backtests
**Symptom**: `JSONDecodeError` or `YFTzMissingError` during batch backtest  
**Cause**: Regime data (SPY/sectors) not in cache, falling back to Yahoo  
**Solution**: Update cache with flat files before running backtest

### Stale regime data
**Symptom**: Batch backtest shows "Cache is 3 days behind"  
**Cause**: Haven't run daily cache update  
**Solution**: Run `populate_cache_bulk.py` for recent dates

---

## Summary

**For End-of-Day Trading:**
- ✅ Use `populate_cache_bulk.py` (flat files)
- ✅ Run daily after market close
- ✅ Automate with cron job
- ❌ Don't use REST API (subscription limitation)
- ❌ Don't rely on Yahoo Finance (unreliable)

**Your workflow is optimized for EOD data → next-day trading, and flat files are the perfect solution.**
