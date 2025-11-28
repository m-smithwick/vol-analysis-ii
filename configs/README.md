# Configuration System Documentation

## Overview

The Configuration System enables systematic backtesting across multiple parameter configurations without code changes. Instead of manually editing code to test different strategies, you create YAML configuration files that define all parameters.

## Quick Start

### 1. Test a Single Configuration

```bash
# Run backtest with a specific configuration
python batch_backtest.py \
  -f ticker_lists/ibd.txt \
  --risk-managed \
  --account-value 100000
```

### 2. Compare Multiple Configurations

```bash
# Test all 5 configurations and compare results
python batch_config_test.py \
  -c configs/base_config.yaml \
     configs/time_decay_config.yaml \
     configs/vol_regime_config.yaml \
     configs/conservative_config.yaml \
     configs/aggressive_config.yaml \
  -f ticker_lists/ibd.txt \
  -o backtest_results/config_comparison
```

This generates (all files in the output directory):
- **CSV file**: Sortable comparison table
- **Excel file**: Professionally formatted with conditional coloring
- **Text report**: Detailed analysis with rankings and insights

**Note**: Configuration subdirectories are not created since individual per-ticker reports are disabled by default (saves disk space). All comparison files go directly into the output directory.

## Available Configurations

### base_config.yaml - Production Baseline
- **Stop Strategy**: Static (traditional fixed stops)
- **Risk**: 0.75% per trade
- **Time Stops**: 12 bars
- **Use Case**: Current production settings, fully validated

### time_decay_config.yaml - Validated Winner ⭐
- **Stop Strategy**: Time Decay (gradually tightens: 2.5 → 2.0 → 1.5 ATR)
- **Risk**: 0.75% per trade
- **Time Stops**: 12 bars
- **Performance**: +22% improvement (1.52R avg vs 1.25R baseline)
- **Use Case**: Let trades develop early, tighten stops over time

### vol_regime_config.yaml - Volatility Adaptive
- **Stop Strategy**: Volatility Regime (adjusts based on ATR_Z)
- **Risk**: 0.75% per trade
- **Time Stops**: 12 bars
- **Performance**: +30% improvement (1.62R avg)
- **Use Case**: Wider stops in volatile markets, tighter in calm markets

### conservative_config.yaml - Capital Preservation
- **Stop Strategy**: Static
- **Risk**: 0.5% per trade (lower)
- **Time Stops**: Disabled (0 bars)
- **Entry Threshold**: 6.5 (vs 6.0 baseline - more selective)
- **Use Case**: Lower risk, longer holding periods, focus on capital preservation

### aggressive_config.yaml - Maximum Opportunities
- **Stop Strategy**: Static
- **Risk**: 1.0% per trade (maximum recommended)
- **Time Stops**: 8 bars (tighter than baseline)
- **Entry Threshold**: 5.5 (vs 6.0 baseline - more signals)
- **Regime Filters**: SPY only (less strict)
- **Use Case**: Higher risk, more frequent trading, capture more opportunities

## Configuration File Structure

```yaml
# Metadata
config_name: "your_config_name"
config_version: "1.0"
description: "Brief description of this configuration"

# Risk Management
risk_management:
  account_value: 100000
  risk_pct_per_trade: 0.75  # 0.5-1.0% recommended
  stop_strategy: "static"    # static, vol_regime, atr_dynamic, pct_trail, time_decay
  time_stop_bars: 12         # 0 or negative to disable
  
  stop_params:
    static:
      enabled: true
    vol_regime:
      low_vol_mult: 1.5      # Tight stop when calm
      normal_vol_mult: 2.0   # Standard
      high_vol_mult: 2.5     # Wide stop when volatile
      low_threshold: -0.5
      high_threshold: 0.5
    # ... other strategies

# Signal Thresholds
signal_thresholds:
  entry:
    moderate_buy_pullback: 6.0  # Primary validated signal
    stealth_accumulation: 4.0
    strong_buy: 6.0
    volume_breakout: 6.0
  exit:
    momentum_exhaustion: 5.0
    profit_taking: 5.0
    distribution_warning: 5.0
  enabled_entry_signals:
    - "moderate_buy_pullback"
  enabled_exit_signals:
    - "momentum_exhaustion"
    - "profit_taking"
    - "distribution_warning"

# Regime Filters
regime_filters:
  enable_spy_regime: true      # Require SPY above 200-day MA
  enable_sector_regime: true   # Require sector ETF above 50-day MA
  require_both_regimes: true   # Both must be bullish
  sector_mapping_file: "ticker_lists/sector_mappings.csv"

# Profit Management
profit_management:
  enable_profit_scaling: true
  profit_target_r: 2.0         # Take 50% at +2R
  profit_exit_pct: 0.5         # 50% partial exit
  enable_trailing_stop: true
  trail_lookback_bars: 10      # Trail by 10-day low

# Backtest Settings
backtest:
  start_date: null             # YYYY-MM-DD or null for full history
  end_date: null
  lookback_months: 36
  generate_charts: true
  chart_save_dir: "backtest_results"
  generate_trade_log: true
```

## Creating Custom Configurations

### 1. Copy Base Configuration

```bash
cp configs/base_config.yaml configs/my_config.yaml
```

### 2. Edit Parameters

Open `configs/my_config.yaml` and modify:

```yaml
config_name: "my_custom_config"
description: "Testing higher risk with tight time stops"

risk_management:
  risk_pct_per_trade: 1.0    # Increase to 1.0%
  time_stop_bars: 8           # Tighten to 8 bars
```

### 3. Validate Configuration

```bash
python config_loader.py configs/my_config.yaml
```

This checks:
- ✅ All required fields present
- ✅ Valid data types
- ✅ Values within acceptable ranges
- ✅ Stop strategy parameters complete

### 4. Test Configuration

```bash
python batch_config_test.py \
  -c configs/my_config.yaml \
  -f ticker_lists/short.txt \
  -o backtest_results/test_run
```

## Common Configuration Patterns

### Pattern 1: Test Different Stop Strategies

Create variants testing each stop strategy:

```yaml
# config_static.yaml
stop_strategy: "static"

# config_time_decay.yaml
stop_strategy: "time_decay"

# config_vol_regime.yaml
stop_strategy: "vol_regime"
```

Run comparison:
```bash
python batch_config_test.py \
  -c configs/config_*.yaml \
  -f ticker_lists/ibd.txt
```

### Pattern 2: Risk Level Comparison

```yaml
# conservative.yaml
risk_pct_per_trade: 0.5
time_stop_bars: 0  # Let winners run

# moderate.yaml
risk_pct_per_trade: 0.75
time_stop_bars: 12

# aggressive.yaml
risk_pct_per_trade: 1.0
time_stop_bars: 8  # Cut losers quickly
```

### Pattern 3: Entry Threshold Sweep

```yaml
# selective.yaml
signal_thresholds:
  entry:
    moderate_buy_pullback: 7.0  # More selective

# balanced.yaml
signal_thresholds:
  entry:
    moderate_buy_pullback: 6.0  # Baseline

# opportunistic.yaml
signal_thresholds:
  entry:
    moderate_buy_pullback: 5.0  # More signals
```

## Interpreting Comparison Reports

### Key Metrics Explained

**Return %**: Total portfolio return over test period
- Higher is better
- Consider alongside risk metrics

**Win Rate %**: Percentage of profitable trades
- 60-70% is excellent for swing trading
- 50-60% is good
- <50% needs improvement

**Avg R-Multiple**: Average profit relative to risk
- >1.5R is excellent
- 1.0-1.5R is good
- <1.0R is losing money

**Median R-Multiple**: Typical trade profit (more reliable than average)
- Use this for realistic expectations
- Less affected by outliers

**Profit Factor**: Total profits / Total losses
- >2.0 is excellent
- 1.5-2.0 is good
- <1.5 needs improvement

**Max Drawdown %**: Largest peak-to-trough equity decline
- Lower is better (less painful)
- -10% to -20% is typical for aggressive strategies
- <-10% is excellent

### Exit Type Distribution

Understanding where trades exit helps refine strategy:

**Time Stops**: Dead positions that didn't move
- Too many? Consider loosening entry criteria
- Too few? Might be letting losers run

**Hard/Static Stops**: Risk management working
- Should be <30% of exits
- More means entries are poorly timed

**Profit Targets**: Winning trades hitting +2R
- 20-40% is healthy
- Shows strategy captures momentum

**Trail Stops**: Letting winners run then exiting
- 30-50% ideal
- Shows you're riding trends

**Signal Exits**: Regular exit signals triggering
- Should be significant portion
- Validates signal-based exit logic

## Best Practices

### 1. Start with Base Configuration

Always run `base_config.yaml` first to establish baseline performance.

### 2. Change One Variable at a Time

When testing, modify only one parameter per configuration:
- ✅ Good: Test different stop strategies with same risk %
- ❌ Bad: Change stop strategy AND risk % AND time stops

### 3. Use Appropriate Sample Sizes

- **Small test** (ticker_lists/short.txt): Quick validation
- **Medium test** (ticker_lists/ibd.txt): Standard validation
- **Large test** (ticker_lists/cmb.txt): Robust validation

### 4. Consider Market Conditions

Test configurations in different market regimes:
```yaml
backtest:
  start_date: "2023-11-01"  # Choppy period
  end_date: "2025-04-04"
```

```yaml
backtest:
  start_date: "2025-04-04"  # Rally period
  end_date: "2025-11-07"
```

### 5. Validate Before Live Trading

Never trade with a configuration that hasn't been:
1. ✅ Validated with `config_loader.py`
2. ✅ Backtested on historical data
3. ✅ Tested out-of-sample
4. ✅ Compared to baseline performance

## Troubleshooting

### Configuration Validation Errors

**Error**: `risk_pct_per_trade must be between 0.1 and 5.0`
- **Fix**: Adjust risk percentage to acceptable range

**Error**: `Invalid stop_strategy 'custom'`
- **Fix**: Use one of: static, vol_regime, atr_dynamic, pct_trail, time_decay

**Error**: `Missing required sections: ['profit_management']`
- **Fix**: Add missing section from base_config.yaml template

### No Trades Generated

**Possible causes**:
1. **Entry thresholds too high**: Lower `moderate_buy_pullback` threshold
2. **Regime filters too strict**: Try `require_both_regimes: false`
3. **Date range too short**: Extend test period
4. **Ticker list has no data**: Check cache with `query_cache_range.py`

### Performance Issues

**Backtest taking too long?**
- Use smaller ticker list for testing
- Reduce `lookback_months` if not needed
- Set `save_individual_reports: false` in batch_backtest.py

## Advanced Usage

### Integrating with RiskManager Directly

```python
from config_loader import load_config
from risk_manager import RiskManager

# Load configuration
config = load_config('configs/my_config.yaml')

# Extract parameters
risk_params = config.get_risk_manager_params()
stop_params = config.get_stop_params()

# Initialize RiskManager with config
risk_manager = RiskManager(
    account_value=risk_params['account_value'],
    risk_pct_per_trade=risk_params['risk_pct_per_trade'],
    stop_strategy=risk_params['stop_strategy'],
    time_stop_bars=risk_params['time_stop_bars'],
    stop_params=stop_params
)
```

### Programmatic Configuration Generation

```python
import yaml

# Generate parameter sweep
for risk_pct in [0.5, 0.75, 1.0]:
    config = {
        'config_name': f'risk_{risk_pct}',
        'risk_management': {
            'risk_pct_per_trade': risk_pct,
            # ... other params
        }
    }
    
    with open(f'configs/risk_{risk_pct}.yaml', 'w') as f:
        yaml.dump(config, f)
```

## Support

For questions or issues:
1. Check configuration with: `python config_loader.py <config_file>`
2. Review base_config.yaml for template
3. See PROJECT-STATUS.md for current development status
4. See CODE_MAP.txt for module documentation

## Version History

- **v1.0** (Nov 2025): Initial release
  - 5 validated configurations
  - Batch testing framework
  - Excel comparison reports
  - Full parameter coverage
