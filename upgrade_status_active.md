# Volume Analysis System - Active Items

**Pending work and next steps**

---

## Pending Implementation ⏸️

### Item #7: Refactor/Integration Plan

**Status:** ⏸️ PARTIAL (Item #1 complete, full refactor pending)

**Goal:** Modular pipeline architecture with separate modules for each feature type

**Current State:**
- risk_manager.py ✅ (standalone module)
- regime_filter.py ✅ (standalone module)
- Other features still integrated in main files

**Remaining Work:**
- Break out modules: swing_structure.py, volume_features.py
- Create unified orchestration in vol_analysis.py
- Add unit tests for each module
- Update integration tests

---

### Item #9: Robust Threshold Validation & Overfitting Prevention

**Status:** ⏸️ PLANNED (depends on Item #8 ✅)

**Goal:** Walk-forward analysis and out-of-sample validation to prevent curve-fitting

**Dependency:** Item #8 (Threshold Optimization) completed with overfitting risk identified

**Implementation Plan:**
1. Walk-forward analysis framework
2. Out-of-sample test periods
3. Rolling threshold optimization
4. Performance degradation detection
5. Validation reporting

**Risk Mitigation:**
- Current thresholds (6.5, 8.0) validated on same data used for optimization
- Need separate validation dataset to confirm edge is real

---

## Implementation Priority

**Recommended Order:**
1. **Item #5** (P&L Exits) - High impact, RiskManager foundation ready
2. **Item #9** (Validation) - Critical for production readiness
3. **Item #7** (Refactor) - Optional cleanup, can be deferred

---

## Key Metrics (Current Implementation)

From completed threshold optimization:
- Moderate Buy (≥6.5): 64.3% win rate, +2.15% expectancy, 28 trades
- Stealth Accumulation: 61.7% win rate, +2.81% expectancy, 146 trades
- Combined Strategy: 100% win rate, +20.77% average return

**Note:** These metrics need validation with Item #9 to confirm robustness

---

**Last Updated:** 2025-11-05  
**For completed items, see:** `upgrade_status_completed.md`  
**For quick overview, see:** `upgrade_summary.md`
