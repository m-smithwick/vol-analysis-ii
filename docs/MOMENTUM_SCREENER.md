# Momentum Screener Documentation

## Overview

The Momentum Screener identifies "Momentum Ignition" candidates using a combination of:
1. **Relative Strength Velocity** - Acceleration in relative performance vs SPY
2. **Volatility Contraction Pattern (VCP)** - Tight trading ranges suggesting consolidation
3. **Trend Confirmation** - Price above 200-day SMA
4. **Liquidity Requirements** - Minimum 500k average daily volume

## Quick Start

```bash
# Test with 4 tickers (quick validation)
python momentum_screener.py --file ticker_lists/short.txt

# Screen 20 IBD stocks
python momentum_screener.py --file ticker_lists/ibd20.txt

# Screen S&P 100 with custom output
python momentum_screener.py --file ticker_lists/sp100.txt --output sp100_momentum.csv

# Quick check on specific tickers
python momentum_screener.py --tickers AAPL MSFT GOOGL
```

## Requirements

### Cache Prerequisites

All tickers must be in local cache before screening:

```bash
# Populate benchmark (required)
python populate_cache.py SPY --period 24mo

# Populate ticker universe
python populate_cache.py --file ticker_lists/sp100.txt --period 24mo
```

**Minimum Data**: 250 trading days (for 200-day SMA calculation)

### Python Dependencies

Already included in `requirements.txt`:
- pandas
- numpy
- scipy (for linear regression)

## Screening Methodology

The screener uses a **two-stage filtering approach** to efficiently process large ticker universes:

### Stage 1: Velvet Rope Filter (Institutional Quality)

Applied **first** to eliminate low-quality stocks before expensive calculations:

1. **Price Floor**: Close >= $15 (eliminates penny stocks)
2. **Dollar Volume**: 20-day avg >= $20M (institutional liquidity requirement)
3. **Trend Alignment**: Price > 200 SMA **AND** 200 SMA rising (not just above, but in rising trend)
4. **Volatility Cap**: ADR_20 <= 6% (rejects overly choppy stocks)

**Performance Impact**:
- Filters out ~85% of stocks instantly
- Eliminates penny stocks (typically ~45% of raw universe)
- Removes low-liquidity names (typically ~40% of remaining)
- Only high-quality survivors proceed to Stage 2

**Example Results** (Batch 01, 1000 tickers):
```
Loaded: 787 tickers (213 had insufficient data)
Velvet Rope Survivors: 116/787 (14.7%)
Filtered Out: 671 (85.3%)

Rejection Breakdown:
  - Price floor (<$15): 309 (46.1%)
  - Dollar volume (<$20M): 259 (38.6%)
  - Trend alignment: 90 (13.4%)
  - Volatility cap (>6% ADR): 13 (1.9%)
```

### Stage 2: Momentum Calculations (Survivors Only)

Expensive calculations performed only on institutional-quality survivors:

### 2.1. Relative Strength (RS) Velocity

**Purpose**: Identify stocks with accelerating momentum relative to the market.

**Calculation**:
```python
RS_Ratio = Stock_Close / SPY_Close
Slope_10d = Linear_regression_slope(RS_Ratio, last_10_days)
Slope_50d = Linear_regression_slope(RS_Ratio, last_50_days)
Velocity_Increasing = Slope_10d > Slope_50d
```

**Interpretation**:
- Positive slope: Outperforming SPY
- Slope_10d > Slope_50d: Momentum accelerating (key signal)
- Negative slopes with 10d > 50d: Underperforming less (still shows acceleration)

### 2. Volatility Contraction Pattern (VCP)

**Purpose**: Identify consolidation phases that often precede breakouts.

**Calculation**:
```python
Norm_Range = (High - Low) / Close
Avg_Range_20 = 20-day_SMA(Norm_Range)
VCP_Active = Current_Norm_Range < (0.5 * Avg_Range_20)
```

**Interpretation**:
- VCP_Active = True: Current volatility < 50% of recent average
- Suggests tight consolidation (potential coiling for breakout)
- Lower contraction_ratio = tighter consolidation

### 3. Trend Confirmation

**Calculation**:
```python
SMA_200 = 200-day_simple_moving_average(Close)
Above_200SMA = Current_Price > SMA_200
```

**Interpretation**:
- Ensures stock is in established uptrend
- Filters out downtrending stocks despite momentum

### 4. Liquidity Filter

**Calculation**:
```python
Avg_Volume_20 = 20-day_average(Volume)
Liquidity_OK = Avg_Volume_20 > 500,000
```

**Interpretation**:
- Ensures sufficient trading volume
- Minimizes slippage on entry/exit

## Command Line Options

### Input Selection

```bash
# From file (one ticker per line)
--file ticker_lists/my_universe.txt

# From command line
--tickers AAPL MSFT GOOGL AMZN
```

### Screening Parameters

```bash
# Lookback period (default: 12mo)
--period 18mo

# Benchmark for RS calculation (default: SPY)
--benchmark QQQ

# Output file (default: auto-timestamped)
--output my_results.csv

# Number of results to display (default: 20)
--top 10
```

## Output Format

### Console Display

```
================================================================================
TOP MOMENTUM CANDIDATES
================================================================================
ticker    RS_10d    RS_50d Vel↑ VCP P/SMA% Vol_20d Pass
  PLTR  -0.000434 -0.000695    ✓   ✓ +15.5%  57.30M   ✅
   NET  -0.000647 -0.000846    ✓   ✓  +9.8%   3.92M   ✅
   MDB  0.014307  0.000944     ✓   ✗ +59.4%   2.94M
================================================================================
```

**Legend**:
- **RS_10d/50d**: Linear regression slopes of RS ratio
- **Vel↑**: Velocity increasing (✓ = yes, ✗ = no)
- **VCP**: Volatility contraction active (✓ = yes, ✗ = no)
- **P/SMA%**: Percent above/below 200-day SMA
- **Vol_20d**: 20-day average volume (in millions)
- **Pass**: ✅ = Passes all filters

### CSV Export

Full results exported to timestamped CSV:

```csv
ticker,passes_all_filters,rs_slope_10d,rs_slope_50d,velocity_increasing,
current_rs_ratio,vcp_active,current_norm_range,avg_range_20d,
contraction_ratio,current_price,sma_200,above_200sma,price_vs_sma_pct,
avg_volume_20d,liquidity_ok
```

## Interpretation Guide

### Perfect Candidate Profile

**Passes All Filters** = ✅ in "Pass" column

```
PLTR: -0.000434/-0.000695, ✓ Vel↑, ✓ VCP, +15.5%, 57.30M
```

**Why This is Strong**:
1. **RS Velocity Increasing**: Even though both slopes negative (underperforming market), 10-day slope is LESS negative than 50-day (momentum improving)
2. **VCP Active**: Contraction ratio 0.44 (trading in 44% of normal range - very tight)
3. **Above 200 SMA**: +15.5% (established uptrend)
4. **High Liquidity**: 57M shares/day (easy entry/exit)

### Common Patterns

#### Strong RS, No VCP
```
MDB: 0.014307/0.000944, ✓ Vel↑, ✗ VCP, +59.4%, 2.94M
```
- Accelerating relative strength
- BUT still volatile (not consolidating)
- May need to wait for VCP formation

#### VCP Present, Weak RS
```
Stock: -0.001/-0.0009, ✗ Vel↑, ✓ VCP, +10%, 5M
```
- Tight consolidation
- BUT momentum decelerating
- May be topping rather than coiling

## Performance Considerations

### Speed Benchmarks

**4 tickers (short.txt)**: ~1 second
**20 tickers (ibd20.txt)**: ~2 seconds  
**100 tickers (sp100.txt)**: ~8-10 seconds
**1000+ tickers**: Expected ~60-90 seconds

### Memory Usage

- Minimal for <100 tickers
- ~500MB for 1000 tickers
- Linear scaling with ticker count

### Optimization Tips

1. **Pre-populate cache**: Avoid on-the-fly downloads
2. **Use appropriate period**: 12-18mo sufficient for most strategies
3. **Batch processing**: Screen multiple universes in sequence

## Integration with Existing System

The screener is standalone but follows project conventions:

### Data Layer
- Uses `data_manager.get_smart_data()` (cache-only mode)
- Respects existing cache structure
- No external API calls

### Error Handling
- Uses `error_handler` framework
- Graceful degradation (skips problem tickers)
- Comprehensive logging

### Logging
- Standard `vol_analysis` logger
- Progress reporting every 10 tickers
- Cache freshness warnings

## Troubleshooting

### "No cached data available"

```
❌ Failed to load benchmark SPY: No cached data available
```

**Solution**:
```bash
python populate_cache.py SPY --period 24mo
```

### "Insufficient data (XXX periods, need 200+)"

**Problem**: Ticker has <200 trading days cached

**Solution**:
```bash
python populate_cache.py TICKER --period 12mo
```

### "Cache is X days behind"

**Not an Error**: Screener uses cached data as-is

**To Update**:
```bash
python populate_cache.py TICKER --period Xd
```

### No tickers pass filters

**This is normal** - the filters are intentionally strict:
- Most tickers fail on VCP (too volatile)
- Many fail on RS velocity (momentum not accelerating)
- Typical hit rate: 0-10% in most universes

## Example Workflows

### Daily Pre-Market Scan

```bash
# Update cache for watchlist
python populate_cache.py --file ticker_lists/watchlist.txt --period 5d

# Run screen
python momentum_screener.py --file ticker_lists/watchlist.txt

# Review CSV results
open momentum_results_*.csv
```

### Weekly Full Universe Screen

```bash
# Screen large universe
python momentum_screener.py --file ticker_lists/sp100.txt --output weekly_screen.csv

# Filter to perfect candidates
grep "True" weekly_screen.csv > perfect_candidates.csv
```

### Compare Multiple Benchmarks

```bash
# Screen vs SPY (market relative)
python momentum_screener.py --file tickers.txt --benchmark SPY --output spy_relative.csv

# Screen vs QQQ (tech relative)
python momentum_screener.py --file tickers.txt --benchmark QQQ --output qqq_relative.csv

# Screen vs IWM (small-cap relative)
python momentum_screener.py --file tickers.txt --benchmark IWM --output iwm_relative.csv
```

## Future Enhancements (Potential)

- [ ] Parallel processing for 1000+ ticker universes
- [ ] Historical backtest of screen results
- [ ] Configurable VCP threshold (currently 0.5)
- [ ] Multiple RS timeframe analysis (10/20/50/100 day slopes)
- [ ] Alert system for new candidates
- [ ] Integration with existing vol_analysis signals

## References

**Related Documentation**:
- `CODE_MAP.txt` - Project architecture
- `docs/CACHE_SCHEMA.md` - Cache structure
- `README.md` - Main project documentation

**Methodology Sources**:
- Relative Strength: IBD methodology
- VCP Pattern: Mark Minervini's Volatility Contraction Pattern
- Linear Regression: Standard statistical technique

---

**Last Updated**: 2025-12-11  
**Module**: `momentum_screener.py`  
**Status**: Production Ready
