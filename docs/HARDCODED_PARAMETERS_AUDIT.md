# Hardcoded Parameters Audit

**Purpose**: Identify all hardcoded values that should be externalized to configuration files for maximum flexibility.

**Date**: 2025-11-27

---

## ✅ Already Configurable (Phase 1 & 2 Complete)

### Risk Management
- `account_value`: Starting account equity
- `risk_pct_per_trade`: Risk percentage per trade (0.5-1.0%)
- `stop_strategy`: Stop loss strategy (static, vol_regime, atr_dynamic, pct_trail, time_decay)
- `time_stop_bars`: Time stop threshold (12 bars default)
- Stop strategy parameters (all 5 strategies)

### Signal Thresholds
- `strong_buy`: Accumulation score threshold (6.5 default)
- `moderate_buy_pullback`: Pullback entry threshold (6.5 validated - was 6.0, Dec 2025 optimization)
- `stealth_accumulation`: Early entry threshold (4.0 default)
- `volume_breakout`: Breakout threshold (6.5 default)

### Regime Filters
- `enable_spy_regime`: SPY 200-day MA filter (true/false)
- `enable_sector_regime`: Sector ETF 50-day MA filter (true/false)
- `require_both_regimes`: Require both filters (true/false)
- `sector_mapping_file`: Path to sector mappings CSV

### Profit Management
- `enable_profit_scaling`: 50% exit at +2R (true/false)
- `profit_target_r`: R-multiple for profit taking (2.0 default)
- `profit_exit_pct`: Partial exit percentage (0.5 = 50%)
- `enable_trailing_stop`: Trailing stop after profit (true/false)
- `trail_lookback_bars`: 10-day low trailing stop

---

## 🔴 Currently Hardcoded - Should Be Configurable

### 1. Pre-Trade Quality Filters (indicators.py, analysis_service.py)

**Location**: `indicators.apply_prefilters()`, `analysis_service.py` line ~126

```python
min_dollar_volume=5_000_000,  # $5M minimum liquidity
min_price=3.00,                # $3.00 minimum price
earnings_window_days=3,        # 3 days before/after earnings
```

**Impact**: 
- Controls which stocks are tradeable
- Affects backtesting sample size
- Different users have different capital → different liquidity needs

**Recommended Config Section**:
```yaml
pre_trade_filters:
  min_dollar_volume: 5000000  # Minimum avg daily dollar volume
  min_price: 3.00             # Minimum stock price
  earnings_window_days: 3      # Days to avoid around earnings
  enable_liquidity_filter: true
  enable_price_filter: true
  enable_earnings_filter: false  # Currently disabled by default
```

---

### 2. Event Day Detection (volume_features.py, indicators.py)

**Location**: `volume_features.detect_event_days()`, multiple calls

```python
atr_multiplier=2.5,      # Range spike threshold
volume_threshold=2.0     # Volume spike threshold
```

**Impact**:
- Determines which days are "event days" (earnings, news spikes)
- Entry signals filtered on event days
- Conservative users may want lower threshold (1.5x)
- Aggressive users may want higher threshold (3.0x)

**Recommended Config Section**:
```yaml
event_detection:
  enable_event_filter: true
  atr_multiplier: 2.5      # Range spike = TR > 2.5 * ATR20
  volume_threshold: 2.0    # Volume spike = Vol > 2.0x average
```

---

### 3. Volume Detection Thresholds (signal_generator.py)

**Locations**: Throughout signal generation functions

**Strong Buy**:
```python
(df['Relative_Volume'] >= 1.2) &  # Minimum volume
(df['Relative_Volume'] <= 3.0) &  # Maximum volume (avoid events)
```

**Moderate Buy**:
```python
(df['Relative_Volume'] < 1.5) &   # Volume normalizing
```

**Stealth Accumulation** (deprecated but still in code):
```python
(df['Relative_Volume'] < 1.3) &   # Low volume stealth
```

**Volume Breakout**:
```python
(df['Relative_Volume'] > 2.5) &   # High volume breakout
```

**Profit Taking**:
```python
(df['Relative_Volume'] > 1.8) &   # High volume exit
```

**Distribution Warning**:
```python
(df['Relative_Volume'] > 1.3) &   # Above average distribution
```

**Sell Signal**:
```python
(df['Relative_Volume'] > 1.5) &   # High volume sell
```

**Momentum Exhaustion**:
```python
(df['Relative_Volume'] < 0.8) &   # Declining volume
```

**Stop Loss**:
```python
(df['Relative_Volume'] > 1.8) &   # High volume breakdown
```

**Impact**:
- Core signal detection logic
- Different volume profiles for different trading styles
- Aggressive traders may accept lower volume
- Conservative traders may require higher volume confirmation

**Recommended Config Section**:
```yaml
volume_thresholds:
  # Entry Signals
  strong_buy_min: 1.2
  strong_buy_max: 3.0
  moderate_buy_max: 1.5
  stealth_max: 1.3
  volume_breakout_min: 2.5
  
  # Exit Signals
  profit_taking_min: 1.8
  distribution_warning_min: 1.3
  sell_signal_min: 1.5
  momentum_exhaustion_max: 0.8
  stop_loss_min: 1.8
```

---

### 4. CMF (Chaikin Money Flow) Thresholds (signal_generator.py)

**Locations**: Multiple signal functions

```python
cmf_positive = df['CMF_Z'] > 0       # Positive buying pressure
strong_cmf = df['CMF_Z'] > 1.0       # Strong buying pressure (>1σ)
```

**Impact**:
- Determines buying/selling pressure strength
- Conservative: require stronger CMF (>1.0)
- Aggressive: allow weaker CMF (>0.5)

**Recommended Config Section**:
```yaml
cmf_thresholds:
  positive_threshold: 0.0    # CMF_Z > 0 = buying pressure
  strong_threshold: 1.0      # CMF_Z > 1.0 = strong buying
  weak_threshold: 0.5        # For less strict signals
```

---

### 5. Moving Average Periods (signal_generator.py, analysis_service.py)

**Locations**: Throughout analysis pipeline

**Pullback Detection**:
```python
ma_5 = df['Close'].rolling(5).mean()   # Short-term MA
ma_20 = df['Close'].rolling(20).mean() # Long-term MA
```

**Other MAs**:
```python
df['Price_MA'] = df['Close'].rolling(window=10).mean()
df['SMA_50'] = df['Close'].rolling(window=50).mean()
df['SMA_200'] = df['Close'].rolling(window=200).mean()
```

**Impact**:
- Defines pullback zones
- Trend determination
- Different timeframes for different holding periods

**Recommended Config Section**:
```yaml
moving_averages:
  short_term: 5      # For pullback detection
  medium_term: 20    # For trend confirmation
  long_term: 50      # For chart display
  very_long_term: 200  # For regime filtering
```

---

### 6. Accumulation Score Thresholds (signal_generator.py)

**Locations**: Various signal scoring functions

```python
(df['Accumulation_Score'] < 2)   # Very low accumulation (exit)
(df['Accumulation_Score'] < 3)   # Low accumulation (momentum exhaustion)
(df['Accumulation_Score'] < 4)   # Waning accumulation (profit taking)
(df['Accumulation_Score'] >= 5)  # Moderate accumulation (moderate buy base)
(df['Accumulation_Score'] >= 6)  # High accumulation (confluence, stealth)
(df['Accumulation_Score'] >= 7)  # Very high accumulation (strong buy)
```

**Impact**:
- Signal thresholds in configs control MINIMUM score to generate signal
- Exit logic uses hardcoded accumulation level boundaries
- Note: Moderate Buy uses score ≥5 internally but filtered to ≥6.5 via config threshold

**Recommended Config Addition**:
```yaml
accumulation_levels:
  very_low: 2    # For exit urgency
  low: 3         # For momentum exhaustion
  waning: 4      # For profit taking detection
  moderate: 5    # For moderate buy base signal (then filtered by config threshold)
  high: 6        # For confluence/stealth
  very_high: 7   # For strong buy (per conservative_config.yaml default)
```

**Note**: As of Dec 2025, individual signal thresholds from config files are the sole authority. No global filters applied.

---

### 7. Price Movement Lookback Periods (signal_generator.py)

**Locations**: Various functions

```python
df['Close'].shift(1)         # 1-day comparison
df['Close'].shift(3)         # 3-day trend
df['Close'].shift(5)         # 5-day momentum
df['Close'].rolling(20).max() # 20-day new highs
```

**Impact**:
- Determines momentum and trend windows
- Shorter periods = more sensitive
- Longer periods = more stable

**Recommended Config Section**:
```yaml
lookback_periods:
  single_day: 1       # Day-over-day comparison
  short_trend: 3      # Short-term trend (3 days)
  momentum: 5         # Momentum lookback (5 days)
  swing_high: 20      # New high detection (20 days)
```

---

### 8. Support/Resistance Parameters (swing_structure.py)

**Location**: `swing_structure.calculate_swing_levels()`

```python
lookback=3  # Pivot lookback period
```

**Impact**:
- Tighter lookback (2) = more support/resistance levels
- Wider lookback (5) = fewer, stronger levels

**Already in function call, needs config integration**

---

### 9. Technical Indicator Windows (analysis_service.py, indicators.py)

**Locations**: Multiple indicator calculations

```python
window=20  # Standard for most indicators
window=10  # OBV MA, Price MA
window=5   # Short-term correlations
```

**Impact**:
- Responsiveness vs stability trade-off
- Shorter windows = faster signals
- Longer windows = smoother signals

**Recommended Config Section**:
```yaml
indicator_periods:
  atr_period: 20
  cmf_period: 20
  volume_ma: 20
  obv_ma: 10
  ad_ma: 10
  price_ma: 10
  zscore_window: 20
  correlation_window: 20
  swing_lookback: 3
```

---

### 10. Support Breakout Tolerance (signal_generator.py)

**Location**: `generate_sell_signals()`

```python
(df['Close'] < df['Support_Level'] * 1.02)  # Within 2% of support
```

**Impact**:
- How close to support before triggering sell
- Tighter (1.01) = earlier exits
- Looser (1.05) = more room

**Recommended Config Section**:
```yaml
support_parameters:
  breakout_tolerance: 0.02  # 2% tolerance
  proximity_pct: 0.03       # 3% for "near support" (currently in swing_structure.py)
```

---

### 11. Price Extension Threshold (signal_generator.py)

**Location**: `generate_momentum_exhaustion_signals()`

```python
(df['Close'] > df['Close'].rolling(10).mean() * 1.03)  # Extended 3% above MA
```

**Impact**:
- Determines when price is "overextended"
- Lower (1.02) = more exhaustion signals
- Higher (1.05) = wait for more extension

**Recommended Config Section**:
```yaml
momentum_params:
  extension_threshold: 0.03  # 3% above MA = extended
  exhaustion_volume: 0.8     # Volume < 0.8x = exhausted
  price_decline_days: 3      # 3-day decline threshold
```

---

## 📊 Priority Ranking for Externalization

### High Priority (User-Facing Settings)
1. **Pre-Trade Filters** - Users with different capital have different needs
2. **Volume Thresholds** - Core signal detection, highly personal
3. **Event Detection** - Risk tolerance varies

### Medium Priority (Fine-Tuning)
4. **CMF Thresholds** - Advanced users may want to adjust
5. **Moving Average Periods** - Affects signal timing
6. **Accumulation Levels** - Exit logic customization

### Low Priority (Advanced/Rare)
7. **Lookback Periods** - Usually stable
8. **Support Parameters** - Rarely needs changing
9. **Indicator Windows** - Technical, rarely modified

---

## 🎯 Recommendation

### Phase 2.5: Add High-Priority Parameters (30 minutes)

1. **Pre-Trade Filters** - Add to config schema
2. **Volume Thresholds** - Create `volume_thresholds` section
3. **Event Detection** - Add `event_detection` section

### Phase 3: Complete Parameter Externalization (1-2 hours)

1. Add all remaining parameters to config schema
2. Modify functions to accept config parameters
3. Wire through analysis pipeline
4. Test with various configurations

### Quick Win Approach

Start with Pre-Trade Filters - these are:
- Easy to externalize (single function)
- High user impact (capital requirements vary)
- Already have clear defaults

---

## 📝 Implementation Notes

**Architecture Principle**: Keep signal LOGIC in code, extract TUNING PARAMETERS to config.

**Example**:
```python
# LOGIC stays in code:
pullback_zone = (df['Close'] < ma_5) & (df['Close'] > ma_20)

# PARAMETERS come from config:
ma_5 = df['Close'].rolling(config['ma_short']).mean()
ma_20 = df['Close'].rolling(config['ma_long']).mean()
```

**Backward Compatibility**: All parameters must have sensible defaults so existing code continues to work without config files.

---

## 🚀 Next Steps

1. Decide which parameters to externalize (all? high-priority only?)
2. Update config schema (base_config.yaml)
3. Modify functions to accept parameters
4. Wire parameters through pipeline
5. Test with different configurations
6. Document in configs/README.md

**Current Status**: Signal thresholds are 80% complete (entry thresholds done, volume thresholds pending).
