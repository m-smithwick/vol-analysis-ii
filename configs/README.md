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

## ⚠️⚠️⚠️ IMPORTANT: MA_CROSSDOWN EXIT STRATEGY DEPRECATED ⚠️⚠️⚠️

**Status**: DISABLED in all configurations as of December 2025

**Evidence**: Comprehensive full-cycle backtesting (Mar 2022 - Dec 2025, S&P 100 stocks) proved MA_Crossdown exit strategy is **harmful**, not helpful:

### Empirical Results (3.69 years, full market cycle including 2022 bear market):

| Metric | Standard Exits | With MA_Crossdown | Impact |
|--------|---------------|-------------------|---------|
| **Max Drawdown** | **-36.97%** ✅ | -52.77% | 43% WORSE! |
| **Total Return** | **307.72%** ✅ | 264.19% | 14% WORSE |
| **Sharpe Ratio** | **1.62** ✅ | 1.34 | 17% WORSE |
| **Win Rate** | **53.7%** ✅ | 44.1% | Lost 403 trades! |
| **Annual Return** | **46.39%** ✅ | 41.94% | 10% WORSE |
| **Total Trades** | 2,121 | 1,670 | 451 fewer |

### Why MA_Crossdown Failed:
1. **50-day MA too sensitive**: Triggers on normal volatility, not real trend breaks
2. **Cuts winners prematurely**: Exits during healthy pullbacks
3. **Creates whipsaws**: Exit → re-enter → exit again = "buy high, sell low"
4. **Prevents recovery**: Forces exits that don't allow positions to bounce back
5. **Worse in bear markets**: Created MORE damage during 2022 decline, not less

### Full Analysis:
See `backtest_comparison_all_three_configs.txt` for complete evidence.

### Current Configuration Status:
- ✅ **conservative_config.yaml**: MA_Crossdown DISABLED with warnings
- ✅ **aggressive_config.yaml**: MA_Crossdown DISABLED with warnings  
- ✅ **balanced_config.yaml**: No MA_Crossdown (never had it)
- ✅ **base_config.yaml**: No MA_Crossdown (never had it)

**DO NOT RE-ENABLE** unless you have new evidence contradicting these results.

---

## ⚠️ Experimental Configurations (.yamlx files)

**Files with `.yamlx` extension are EXPERIMENTAL and NOT RECOMMENDED for production trading.**

### time_decay_config.yamlx
- **Status**: ❌ NOT RECOMMENDED
- **Validation Results** (Nov 2025, 982 trades, 36 months):
  - time_decay: $53,359 P&L, 23% stop rate, $319/trade
  - static: $161,278 P&L, 15% stop rate, $417/trade ⭐
- **Performance**: 3x WORSE than static stops
- **Problem**: Tightens too aggressively, cutting winners short before they reach profit targets
- **Preserved for**: Research purposes only

### vol_regime_config.yamlx
- **Status**: ❌ NOT RECOMMENDED
- **Validation Results** (Nov 2025, 982 trades, 36 months):
  - vol_regime: $146,572 P&L, 32% stop rate (HIGHEST), $342/trade
  - static: $161,278 P&L, 15% stop rate (LOWEST), $417/trade ⭐
- **Performance**: 10% worse P&L, 2x worse stop rate than static
- **Problem**: Adaptive logic creates excessive stops despite sophistication
- **Preserved for**: Research purposes only

**For Production Trading**: Use `.yaml` files only (conservative, balanced, base, aggressive)

**See**: `STOP_STRATEGY_VALIDATION.md` for complete empirical validation analysis

---

## Available Configurations

> **📊 For comprehensive strategy analysis and selection guidance**, see [Configuration Strategy Analysis](../docs/CONFIGURATION_STRATEGY_ANALYSIS.md)
>
> That document includes:
> - Empirical performance across 6 portfolio types
> - Detailed strategy comparison tables
> - Portfolio composition impact analysis
> - Risk/reward trade-off analysis
> - Decision framework for strategy selection

### Quick Reference

| Configuration | Best For | Return | Max DD | Status |
|--------------|----------|--------|--------|--------|
| **conservative_config.yaml** ⭐ | Capital preservation, diversified portfolios | 71-142% | -10% to -16% | ✅ Production |
| **balanced_config.yaml** ⭐ | Most consistent across portfolio types | 67-139% | -10% to -15% | ✅ Production |
| **base_config.yaml** | Historical baseline, testing reference | 57-127% | -9% to -14% | ✅ Production |
| **aggressive_config.yaml** | Maximum returns (use with caution) | 49-114% | -9% to -14% | ⚠️ High risk |
| time_decay_config.yamlx | Research only | 50-86% | -9% to -27% | ❌ Not recommended |
| vol_regime_config.yamlx | Research only | 42-113% | -8% to -15% | ❌ Not recommended |

**Performance data**: Based on Nov 2025 empirical validation (6 portfolio types, 20-254 tickers each)

### Production Configurations (.yaml files)

#### conservative_config.yaml ⭐ RECOMMENDED FOR MOST USERS
- **Entry Threshold**: 6.5 (high selectivity)
- **Time Stops**: Disabled (let winners run)
- **Risk**: 1.0% per trade
- **Best Performance**: Diversified portfolios, stable/mixed stocks
- **Win Rate**: 67-71% (highest consistency)
- **Winner**: 3 of 6 validation tests

#### balanced_config.yaml ⭐ MOST CONSISTENT
- **Entry Threshold**: 6.5 (high selectivity)
- **Time Stops**: 20 bars (moderate)
- **Risk**: 1.0% per trade
- **Best Performance**: Universal - works on all portfolio types
- **Consistency**: Ranked 2nd in 5 of 6 tests (never worse than 4th)
- **Recommended**: Default choice when portfolio composition unknown

#### base_config.yaml - BASELINE REFERENCE
- **Entry Threshold**: 6.0 (original validated)
- **Time Stops**: 12 bars
- **Risk**: 1.0% per trade
- **Purpose**: Historical baseline for comparison testing
- **Performance**: Consistent middle performer (3rd place in 4 of 6 tests)

#### aggressive_config.yaml ⚠️ HIGH RISK
- **Entry Threshold**: 5.5 (lower selectivity)
- **Time Stops**: 8 bars (tight)
- **Risk**: 1.0% per trade
- **Regime Filters**: SPY only (less strict)
- **Performance**: Bottom half in ALL 6 validation tests
- **⛔ Warning**: Never ranked in top 3, proven inferior across all portfolio types

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
    ma_crossdown: 5.0          # Moving average crossdown exit
  enabled_entry_signals:
    - "moderate_buy_pullback"
  enabled_exit_signals:
    - "momentum_exhaustion"
    - "profit_taking"
    - "distribution_warning"
    - "ma_crossdown"           # Optional trend-following exit

# Exit Signal Parameters (Optional)
exit_signal_params:
  ma_crossdown:
    enabled: true              # Enable/disable without removing from enabled_exit_signals
    ma_period: 48              # MA period (48=slightly earlier than crowd at 50)
    confirmation_days: 1       # 1=immediate, 2=two-day confirmation
    buffer_pct: 0.0            # Buffer % below MA (0.5 adds 0.5% cushion)

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
