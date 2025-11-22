"""
Risk Management Constants

These constants define default values for risk management parameters across the trading system.
Values are determined through empirical testing and optimization.

See TIME_STOP_OPTIMIZATION_RESULTS.md for detailed analysis and validation.
"""

# Time Stop Threshold
# Exit after N bars if position has not reached +1R profit
#
# EMPIRICALLY OPTIMIZED VALUE: 20 bars
#
# Optimization Results (24-month test, 41 tickers):
# - TIME_STOP rate: Reduced from 44% to 23% (21 percentage point improvement)
# - Overall expectancy: Improved from +8.73% to +13.71% (+57% improvement)
# - Win rate: Maintained at 63.9%
# - Median return: Improved from +2.45% to +3.25% (+33% improvement)
#
# Why 20 bars works:
# - Gives accumulation patterns time to develop into price movement
# - Filters out false signals that fail quickly (by bar 15)
# - Not too quick (12 bars cut winners short)
# - Not too slow (>20 bars holds dead positions too long)
#
# Usage:
#   Set to 0 or negative to disable time stops entirely
#   Override via CLI: --time-stop-bars <value>
#
# Last validated: November 2025
DEFAULT_TIME_STOP_BARS = 20
