# Project Status

**Last Updated**: 2025-12-08  
**Current Status**: ✅ Ready for next objective

---

## 🎯 Current Context

[To be updated with next session's focus]

---

## 🏗️ Architectural Impact

[To be assessed for next work unit]

---

## 📋 Active Plan

[No active work in progress]

---

## 🧹 Janitor Queue

### Medium Priority

**1. Position Sizing Gap: Backtest vs Live Signal Generation** (Architectural)
   - **Issue**: Disconnect between compounding backtest and stateless live analysis
   - **Workarounds Available**: Manual --account-value updates, extract from LOG_FILE
   - **Future Enhancement**: Build portfolio_state.py tracker tool
   - **Priority**: Medium (workarounds sufficient)
   - **Date Identified**: 2025-12-01

**2. Indicator Warmup Buffer Too Small** (Data Pipeline)
   - **Issue**: batch_backtest.py uses 30-day buffer, but 200-day MA needs ~400 days
   - **Impact**: Date range backtests start signal generation much later than expected
   - **Workaround**: Manually use longer period (-p 60mo) when using date ranges
   - **Fix Needed**: Increase buffer from 30 → 400 days in batch_backtest.py
   - **Priority**: Medium (workaround available)
   - **Date Identified**: 2025-12-07

**3. DuckDB Mode User Confusion** (Documentation/UX)
   - **Issue**: Users expect --use-duckdb to download missing data, but it only queries existing cache
   - **Impact**: Confusion when date ranges not in massive_cache/ return no results
   - **Workaround**: Use legacy mode first to download, then DuckDB for queries
   - **Fix Needed**: Better error messages explaining DuckDB is query optimization, not data source
   - **Priority**: Low (documentation clarified)
   - **Date Identified**: 2025-12-07

### Low Priority

**4. Cached Earnings Dates** (Future Enhancement)
   - Currently bypassing earnings window filter (safe)
   - Default parameter: `earnings_dates=[]`
   - Impact: Low (current bypass works fine)

**5. Residual Duplicate Dates in Regime Display**
   - Display-only issue (cosmetic fix for future cleanup)

---
