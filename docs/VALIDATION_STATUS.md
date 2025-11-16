# ✅ Validation & Signal Status

Current production readiness of every published entry signal along with links to the deeper validation artifacts.

---

## 🔴 Critical Alerts

### ❌ Stealth Accumulation (DEPRECATED)
- **Status**: Failed 6‑month out-of-sample validation (22.7% win rate vs 53.2% expected, ‑7.65% median return).
- **Action**: Do **not** use until the signal is redesigned and revalidated.
- **Reference**: `OUT_OF_SAMPLE_VALIDATION_REPORT.md`

### ⚠️ Moderate Buy
- **Status**: Still valid but with reduced expectancy (+2‑3% median per trade instead of +5%).
- **Action**: Continue using with revised expectations and tighter risk controls.
- **Reference**: `OUT_OF_SAMPLE_VALIDATION_REPORT.md`

---

## 🟢 Currently Supported Entry Signals

| Signal | Status | Notes |
|--------|--------|-------|
| Moderate Buy | ✅ Live | Only entry signal currently cleared for production use |
| Strong Buy | 🚧 Revalidation required | Use only in experimental context |
| Stealth Accumulation | ❌ Disabled | Overfit on training data |
| Multi-Signal Confluence | 🚧 Depends on upstream signal health | Validate per use case |
| Volume Breakout | 🚧 Pending review | Awaiting new benchmarks |

---

## 📂 Validation References

- `STRATEGY_VALIDATION_COMPLETE.md` – canonical record of validation phases and evidence
- `BACKTEST_VALIDATION_METHODOLOGY.md` – how validation is performed
- `BACKTEST_VALIDATION_REPORT.md` – historical backtest results
- `OUT_OF_SAMPLE_VALIDATION_REPORT.md` – real-world 6‑month performance study

---

## 🔄 Review Cadence

- **Monthly**: Refresh results for active signals with most recent month of data
- **Quarterly**: Re-run full out-of-sample suite for any signal promoted to production
- **Before Release**: Link updated validation output in this file and trim stale warnings from the README

