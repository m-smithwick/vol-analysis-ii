"""
Threshold Disconnect Verification Script

This script demonstrates the disconnect between:
1. Batch summary signals (using empirical thresholds)
2. Risk-managed backtest signals (using fixed boolean logic)

Run this to verify which signals your system is actually trading.
"""

import pandas as pd
import sys
from signal_threshold_validator import (
    apply_empirical_thresholds,
    compare_signal_counts,
    generate_threshold_comparison_report
)


def verify_threshold_disconnect(ticker: str, period: str = '24mo'):
    """
    Verify threshold disconnect for a specific ticker.
    
    Args:
        ticker: Stock symbol to analyze
        period: Analysis period
    """
    print(f"\n🔍 VERIFYING THRESHOLD DISCONNECT FOR {ticker}")
    print("=" * 70)
    
    # Import analyze_ticker to get the DataFrame
    try:
        from vol_analysis import analyze_ticker
    except ImportError:
        print("❌ Error: vol_analysis.py not found")
        return
    
    # Run analysis to get DataFrame
    print(f"\n📊 Analyzing {ticker} ({period})...")
    result = analyze_ticker(
        ticker=ticker,
        period=period,
        save_to_file=False,
        save_chart=False,
        show_chart=False,
        show_summary=False
    )
    
    if not isinstance(result, tuple):
        print(f"❌ Error analyzing {ticker}")
        return
    
    df, _ = result
    
    # Apply empirical thresholds
    print(f"\n🎯 Applying empirical thresholds...")
    df = apply_empirical_thresholds(df)
    
    # Compare signal counts
    comparison = compare_signal_counts(df)
    
    # Generate report
    report = generate_threshold_comparison_report(
        ticker=ticker,
        df=df,
        comparison=comparison,
        save_to_file=True,
        output_dir='backtest_results'
    )
    
    print("\n" + report)
    
    # Show specific examples
    print("\n📋 SIGNAL COMPARISON EXAMPLES:")
    print("=" * 70)
    
    if 'moderate_buy' in comparison:
        mb = comparison['moderate_buy']
        print(f"\n🟡 MODERATE BUY DISCONNECT:")
        print(f"   Batch Summary Says: Use signals with score ≥{mb['threshold']}")
        print(f"   Expected Win Rate: {mb['expected_win_rate']:.1f}%")
        print(f"   Expected Expectancy: {mb['expected_expectancy']:+.2f}%")
        print()
        print(f"   Risk-Managed Backtest Actually Trades: ALL signals with score ≥5.0")
        print(f"   Raw Signals: {mb['raw_signals']}")
        print(f"   Filtered Signals (≥{mb['threshold']}): {mb['filtered_signals']}")
        print(f"   Signals You'd Trade by Mistake: {mb['signals_removed']}")
        print()
        print(f"   ⚠️  You would be trading {mb['reduction_pct']:.0f}% MORE signals than validated!")
    
    # Show which signals are currently active
    print(f"\n📍 CURRENT SIGNALS (as of last bar):")
    print("-" * 70)
    
    last_idx = len(df) - 1
    
    # Check Moderate Buy
    if 'Moderate_Buy' in df.columns:
        raw_signal = df.iloc[last_idx]['Moderate_Buy']
        filtered_signal = df.iloc[last_idx]['Moderate_Buy_filtered']
        score = df.iloc[last_idx]['Moderate_Buy_Score']
        
        print(f"\n🟡 Moderate Buy:")
        print(f"   Raw Signal: {'✅ ACTIVE' if raw_signal else '❌ No Signal'}")
        print(f"   Filtered Signal: {'✅ ACTIVE' if filtered_signal else '❌ No Signal'}")
        print(f"   Current Score: {score:.2f}")
        print(f"   Threshold: ≥{comparison['moderate_buy']['threshold']}")
        
        if raw_signal and not filtered_signal:
            print(f"   ⚠️  WARNING: Raw signal active but score below empirical threshold!")
            print(f"   You would trade this in risk-managed backtest but shouldn't!")
    
    # Check Stealth
    if 'Stealth_Accumulation' in df.columns:
        raw_signal = df.iloc[last_idx]['Stealth_Accumulation']
        filtered_signal = df.iloc[last_idx]['Stealth_Accumulation_filtered']
        score = df.iloc[last_idx]['Stealth_Accumulation_Score']
        
        print(f"\n💎 Stealth Accumulation:")
        print(f"   Raw Signal: {'✅ ACTIVE' if raw_signal else '❌ No Signal'}")
        print(f"   Filtered Signal: {'✅ ACTIVE' if filtered_signal else '❌ No Signal'}")
        print(f"   Current Score: {score:.2f}")
        print(f"   Threshold: ≥{comparison['stealth_accumulation']['threshold']}")
        
        if raw_signal and not filtered_signal:
            print(f"   ⚠️  WARNING: Raw signal active but score below empirical threshold!")
    
    print("\n" + "=" * 70)
    print("\n💡 NEXT STEPS:")
    print("1. Review the threshold validation report saved to backtest_results/")
    print("2. Update batch_backtest.py to use apply_empirical_thresholds()")
    print("3. Use *_filtered signals in risk-managed backtest")
    print("4. Re-run backtests to get accurate performance metrics")
    print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python verify_threshold_disconnect.py TICKER [PERIOD]")
        print("Example: python verify_threshold_disconnect.py KGC 24mo")
        sys.exit(1)
    
    ticker = sys.argv[1]
    period = sys.argv[2] if len(sys.argv) > 2 else '24mo'
    
    verify_threshold_disconnect(ticker, period)
