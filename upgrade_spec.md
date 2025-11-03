# Swing Trading Volume Model – Upgrade Spec

This document describes targeted improvements to the existing end-of-day volume-based trading model. Each section is a workstream. Each workstream includes: goal, design changes, and acceptance criteria.

The intent is to move from "decent scanner with heuristics" to "swing process that respects structure, market regime, execution reality, and P&L context."

---

## 1. Anchored VWAP From Meaningful Pivots (Not From Chart Start)

### Goal
The current VWAP calculation is cumulative from the first bar in the loaded DataFrame:

```python
df['VWAP'] = (Close * Volume).cumsum() / Volume.cumsum()
```

That means:
- VWAP is different depending on whether we pulled 1 month vs 12 months of data.
- "Above VWAP" may reflect nothing more than where we started our chart, not where real buyers stepped in.

We want an **anchored VWAP** that starts at an *actual turning point where strong hands likely entered*, e.g. a swing low after capitulation. This is how institutions track cost basis.

### Design
1. **Detect swing pivots.**
   - A pivot low at index `i` is where `Low[i]` is lower than the previous N lows and the next N lows (N ≈ 3–5).
   - A pivot high is the inverse.

2. **Pick most recent “significant” pivot** in the direction you're trading:
   - For bullish logic: last confirmed swing low.
   - (Later we can switch anchor when a new decisive swing low forms with big volume.)

3. **Compute anchored VWAP forward from that pivot index.**
   ```python
   df.loc[pivot_idx:, 'Anchored_VWAP'] = (
       (df.loc[pivot_idx:, 'Close'] * df.loc[pivot_idx:, 'Volume']).cumsum()
       / df.loc[pivot_idx:, 'Volume'].cumsum()
   )
   ```

   Rows before `pivot_idx` can be NaN or forward-filled from the first defined value.

4. **Replace usage.**
   Anywhere we currently test `Above_VWAP`, `Below_VWAP`, or include VWAP in `Accumulation_Score`, `Exit_Score`, `Strong_Buy`, `Stop_Loss`, etc., we should reference `Anchored_VWAP`, not the naive period-start VWAP.

### Acceptance Criteria
- Anchored_VWAP aligns with visible turns (the "defended" low), not arbitrary dataset start dates.
- Entry logic ("price above VWAP") and exit logic ("price lost VWAP") become more meaningful, because VWAP now represents cost basis of real buyers after a turn.

---

## 2. Support/Resistance From Swing Structure, Not Rolling Min/Max

### Goal
Current code defines support using something like a rolling 20-day low and checks if price is within ~5% of that. Problems:
- In a crash, today's low *is* the rolling low → we think it's "support," but it's just falling knife.
- In an uptrend pullback, true "support" is usually the last higher low, not the absolute 20-day low.

We want **swing-based support/resistance** using actual pivot lows/highs.

### Design
1. Reuse pivot detection from Section 1.
   - Mark bars that are confirmed swing lows and swing highs.

2. Build forward-filled series:
   ```python
   df['Recent_Swing_Low'] = np.nan
   df['Recent_Swing_High'] = np.nan

   for i in range(len(df)):
       if is_pivot_low(i):
           df.loc[i:, 'Recent_Swing_Low'] = df.loc[i, 'Low']
       if is_pivot_high(i):
           df.loc[i:, 'Recent_Swing_High'] = df.loc[i, 'High']

   df['Recent_Swing_Low'] = df['Recent_Swing_Low'].ffill()
   df['Recent_Swing_High'] = df['Recent_Swing_High'].ffill()
   ```

3. Redefine proximity to support:
   ```python
   df['Near_Support'] = df['Close'] <= df['Recent_Swing_Low'] * 1.05
   ```

4. Redefine breakdown:
   ```python
   df['Lost_Support'] = df['Close'] < df['Recent_Swing_Low']
   ```

5. Anywhere the current code uses `Support_Level`, `Near_Support`, `Broke_Support`, etc.:
   - Replace with `Recent_Swing_Low`, `Near_Support`, and `Lost_Support`.

### Acceptance Criteria
- "Strong_Buy" triggers near a previously defended low, not just “lowest low in 20 days.”
- "Stop_Loss" only fires on a true violation of a known defended level.
- Visually, plotted swing lows/highs line up with obvious reaction zones on the chart.

---

## 3. News / Event Spike Filter (ATR Spike Days)

### Goal
Right now, any giant candle with huge volume can trigger bullish accumulation or bearish distribution signals. Earnings gaps and macro shock candles create noise. We want to avoid auto-signaling on “absurd” days.

### Design
1. Add True Range and ATR:
   ```python
   df['Close_prev'] = df['Close'].shift(1)

   def true_range(row):
       return max(
           row['High'] - row['Low'],
           abs(row['High'] - row['Close_prev']),
           abs(row['Low'] - row['Close_prev'])
       )

   df['TR'] = df.apply(true_range, axis=1)
   df['ATR20'] = df['TR'].rolling(20).mean()
   ```

2. Define spike candles:
   ```python
   df['Range_Spike'] = df['TR'] > 2.5 * df['ATR20']
   ```

3. Define "Event_Day" as "range spike + big volume":
   ```python
   df['Event_Day'] = df['Range_Spike'] & (df['Relative_Volume'] > 2.0)
   ```

4. When generating bullish entry signals (`Strong_Buy`, `Confluence_Signal`, `Volume_Breakout`):
   - Require `Event_Day == False`.

5. When generating exit/stop-loss style warnings, you may:
   - Still allow them, OR
   - Tag them separately (e.g. `NewsDriven_Stop`) for manual judgment.

### Acceptance Criteria
- Strong_Buy won't fire just because one earnings candle had crazy reversal volume.
- Dashboard/HTML can show `Event_Day` so you know "this is news-driven, handle manually."

---

## 4. Next-Day Execution / No Lookahead

### Goal
Some levels are computed with same-day data (like today's low) and then immediately used to justify a same-day entry at the close. That’s lookahead if you plan to "enter tomorrow."

We want the model to produce **signals you act on the next session**, using only info you'd have at today's close, with no cheating.

### Design
1. Create lagged structural levels for use in signals:
   ```python
   df['Swing_Low_lag'] = df['Recent_Swing_Low'].shift(1)
   df['Anchored_VWAP_lag'] = df['Anchored_VWAP'].shift(1)
   ```

2. Rewrite entry conditions to reference *lagged* structure, not today's freshly-updated structure.
   Example Strong_Buy logic, conceptually:
   ```python
   df['Strong_Buy_raw'] = (
       (df['Accumulation_Score'] >= THRESH) &
       (df['Close'] > df['Anchored_VWAP_lag']) &
       (df['Close'] <= df['Swing_Low_lag'] * 1.05) &
       (df['Relative_Volume'].between(1.2, 3.0)) &
       (~df['Event_Day'])
   )
   ```

   `Strong_Buy_raw` now means: "Given everything up to (and including) today's close, tomorrow is a candidate long."

3. Plot markers one bar *after* `Strong_Buy_raw` so visually you're marking the day you would actually take the trade.

4. Do similar lagging for breakdown / stop-loss logic.

### Acceptance Criteria
- Backtests mimic: "Signal forms on Day T → you enter/exit Day T+1."
- No signal ever uses values from the *same* bar it is plotted on unless that value is truly known at the close (like today's volume or today's close is fine; but today's derived pivot 'support' is not).

---

## 5. P&L-Aware Exit Logic

### Goal
Current `Exit_Score` is global. It doesn't distinguish:
- "You're up +12%, this is profit-taking time"
vs
- "You're down -4%, structure failed, cut it."

We want exits that react both to technical failure *and* to unrealized P&L relative to your own cost.

### Design
1. Track entry information.
   - Define `Entry_Flag` = (`Strong_Buy_raw` OR `Confluence_Signal_raw`).
   - When `Entry_Flag` first becomes True for a ticker, record:
     - `Entry_Price` = that day's close.
     - `Entry_Date` = that day.
   - Forward-fill `Entry_Price` until an exit event triggers and you "close" the position.
   - This likely requires a lightweight portfolio simulation layer rather than pure vector math, but you can approximate with forward-fill.

2. Compute unrealized P&L:
   ```python
   df['PnL_Pct'] = (df['Close'] / df['Entry_Price']) - 1.0
   ```

3. Build separate sub-scores:
   - `Protect_Profit_Score` (kick in when `PnL_Pct >= PROFIT_THRESH`, e.g. 0.08 for +8%):
     - High Relative_Volume on an up close
     - Big extension above Anchored_VWAP_lag
     - OBV flattening / divergence
   - `Cut_Loss_Score` (kick in when `PnL_Pct < 0`):
     - Close < Swing_Low_lag on elevated volume
     - Close < Anchored_VWAP_lag on elevated volume
     - A/D rolling over

4. Final `Exit_Score` logic:
   - If `PnL_Pct >= PROFIT_THRESH`: bias toward `Protect_Profit_Score`.
   - If `PnL_Pct < 0`: bias toward `Cut_Loss_Score`.
   - If flat-ish P&L: take the max of the two.

5. For plotting / dashboard:
   - Use different markers for "trim/take profit" vs "hard stop/exit loser."

### Acceptance Criteria
- Profit-taking signals mostly show up when you're already green and stretched.
- Hard-exit signals mostly show up when you're underwater or when structure is clearly broken.
- You stop getting generic "exit now!" spam in normal healthy pullbacks when you're still comfortably up.

---

## 6. Market / Sector Regime Filter

### Goal
Right now, each ticker is judged in isolation. In broad risk-off tape, lots of pretty-looking support bounces fail. We want to avoid new longs when the overall market or sector is in distribution.

### Design
1. For each symbol:
   - Also pull benchmark data (e.g. SPY and relevant sector ETF like XLK, XLF, XLE, etc.).

2. Run a lightweight version of the same logic on those benchmarks:
   - Is benchmark above its `Anchored_VWAP_lag`?
   - Is benchmark flashing a distribution warning (e.g. heavy down-volume vs up-volume, OBV rolling over hard)?
   - Is benchmark in freefall / `Event_Day` recently?

3. Define a boolean gate, e.g.:
   ```python
   Market_OK = (
       (SPY_Close > SPY_Anchored_VWAP_lag) &
       (~SPY_Distribution_Warning)
   )
   ```

4. Apply this gate to long-side entry signals:
   ```python
   df['Strong_Buy_final'] = df['Strong_Buy_raw'] & Market_OK
   df['Confluence_Signal_final'] = df['Confluence_Signal_raw'] & Market_OK
   ```

   Do **not** gate sell/exit logic; you still exit in bad tape.

5. In dashboards / HTML:
   - Show both raw signal and gated signal, so you can tell "the stock looks good, but the market is junk."

### Acceptance Criteria
- In risk-off weeks, the model surfaces fewer/no new longs.
- In healthy tape, valid longs still come through.
- You can quickly see when a name is fighting the macro instead of swimming with it.

---

## 7. Refactor / Integration Plan

### indicators.py
Add helpers:
- `find_pivots(df, lookback=3)` → returns indices of swing highs and lows.
- `compute_anchored_vwap(df, last_pivot_idx)` → adds `Anchored_VWAP`.
- `compute_swing_levels(df, pivots)` → adds `Recent_Swing_Low`, `Recent_Swing_High`, forward-filled.
- `compute_volatility_flags(df)` → adds `TR`, `ATR20`, `Range_Spike`, `Event_Day`.

All helpers should avoid lookahead (confirm pivots only after `lookback` bars have passed, etc.).

### vol_analysis.py
- Replace rolling-min/rolling-max “support” usage with swing-based `Recent_Swing_Low` / `Recent_Swing_High`.
- Replace cumulative VWAP with pivot-anchored `Anchored_VWAP`.
- Add lagged versions (`Swing_Low_lag`, `Anchored_VWAP_lag`) for tradeable signals.
- Add next-day action markers (`Strong_Buy_raw` becomes "tomorrow's actionable buy").
- Inject `Market_OK` gating logic before final buy signals.
- Separate exit markers into profit-taking vs stop-loss, using P&L-aware logic.

### Dashboard / Output
- Plot price with:
  - Anchored_VWAP,
  - Recent_Swing_Low / Recent_Swing_High horizontal levels,
  - Markers for:
    - Strong_Buy_final (green),
    - Confluence_Signal_final (blue),
    - Profit_Take (orange),
    - Hard_Stop (red).
- Table should show:
  - raw signal date,
  - gated status (Market_OK yes/no),
  - PnL_Pct if "in position",
  - Exit_Score type (trim vs stop).

---

## 8. End State

After implementing the above:

- Entries happen near defended swing levels, with proven accumulation volume, only when the broad tape isn't garbage.
- VWAP used in logic actually represents "where size stepped in" instead of "where the CSV started."
- Signals are timed realistically (you act next day; no lookahead).
- Exits respect whether you're green (protect profit) or red (cut loser), instead of treating them the same.
- Event-driven chaos days are flagged, not blindly traded.

That gets you from “indicator soup” to an actual swing system you can run off daily closes without babysitting intraday flow.
