# Validation Rigor Standard

## The Problem
Validation gets declared "complete" before adequate testing → contradictory findings → bad trading decisions.

## The Rule: Label Every Validation

**🔬 PRELIMINARY** - Single metric, not cross-validated, DO NOT implement  
**✅ VALIDATED** - Multiple metrics confirm, apples-to-apples comparison, safe for production

## Requirements for ✅ VALIDATED Status

**Must Have:**
1. **Same portfolio, same period** - All strategies tested on identical data
2. **Multiple metrics** - P&L, stop rate, per-trade avg (if winner differs by metric → NOT validated)
3. **100+ trades minimum** - Statistical significance
4. **Reproducible** - Document exact test commands/parameters

**Red Flags:**
- Winner depends on 1-2 outlier trades
- Winner changes with small date range adjustments
- Can't explain WHY winner wins
- Only tested one metric

## When Publishing Validation

**Include at top:**
```markdown
**Status:** [🔬 PRELIMINARY | ✅ VALIDATED]
**Issues:** [What's missing if PRELIMINARY]
**Next Steps:** [What testing needed for ✅]
```

## Enforcement

- DO NOT say "production ready" for 🔬 PRELIMINARY findings
- DO NOT implement until ✅ VALIDATED
- DO push back if user wants to implement PRELIMINARY results

**Better to say "needs more testing" than flip-flop every 6 days.**
