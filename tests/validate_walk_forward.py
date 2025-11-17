#!/usr/bin/env python3
"""
Validation #4: Walk-Forward Testing
===================================

Tests if performance is consistent across different time periods.

This is critical to detect:
1. Overfitting to specific market conditions
2. Performance concentration in one period
3. Strategy robustness across different regimes
"""

import pandas as pd
import numpy as np
from datetime import datetime
from vol_analysis import analyze_ticker


def run_walk_forward_test(ticker: str, total_period: str = '24mo'):
    """
    Split period into segments and test performance consistency.
    
    For 24mo period, we'll test:
    - First 12mo
    - Second 12mo
    - First 6mo vs Last 6mo
    """
    print(f"\n{'='*70}")
    print(f"🔍 WALK-FORWARD VALIDATION: {ticker}")
    print(f"{'='*70}\n")
    
    print("Testing strategy across different time periods...")
    print("If results vary wildly, strategy may be overfit\n")
    
    # Get full period data
    df_full = analyze_ticker(ticker, period=total_period, save_to_file=False,
                            show_chart=False, show_summary=False)
    
    total_days = len(df_full)
    
    print(f"📊 Full Period: {total_days} days")
    print(f"   From: {df_full.index[0].strftime('%Y-%m-%d')}")
    print(f"   To: {df_full.index[-1].strftime('%Y-%m-%d')}\n")
    
    # Split into periods
    mid_point = total_days // 2
    quarter_point = total_days // 4
    three_quarter = 3 * total_days // 4
    
    periods = {
        'First Half (12mo)': df_full.iloc[:mid_point],
        'Second Half (12mo)': df_full.iloc[mid_point:],
        'Q1-Q2 (6mo)': df_full.iloc[:mid_point//2],
        'Q3-Q4 (6mo)': df_full.iloc[three_quarter:],
    }
    
    print("="*70)
    print("📈 PERFORMANCE BY TIME PERIOD")
    print("="*70)
    
    results = {}
    
    for period_name, df_period in periods.items():
        if len(df_period) < 60:  # Skip if too short
            continue
        
        # Calculate key metrics
        total_return = ((df_period['Close'].iloc[-1] - df_period['Close'].iloc[0]) / 
                       df_period['Close'].iloc[0] * 100)
        
        # Count signals
        moderate_buy = df_period['Moderate_Buy'].sum() if 'Moderate_Buy' in df_period.columns else 0
        stealth = df_period['Stealth_Accumulation'].sum() if 'Stealth_Accumulation' in df_period.columns else 0
        momentum_exit = df_period['Momentum_Exhaustion'].sum() if 'Momentum_Exhaustion' in df_period.columns else 0
        profit_exit = df_period['Profit_Taking'].sum() if 'Profit_Taking' in df_period.columns else 0
        
        # Average scores
        avg_acc_score = df_period['Accumulation_Score'].mean() if 'Accumulation_Score' in df_period.columns else 0
        avg_exit_score = df_period['Exit_Score'].mean() if 'Exit_Score' in df_period.columns else 0
        
        results[period_name] = {
            'days': len(df_period),
            'total_return': total_return,
            'moderate_buy': moderate_buy,
            'stealth': stealth,
            'momentum_exit': momentum_exit,
            'profit_exit': profit_exit,
            'avg_acc_score': avg_acc_score,
            'avg_exit_score': avg_exit_score
        }
        
        print(f"\n{period_name}: {len(df_period)} days")
        print(f"  Period Return: {total_return:+.2f}%")
        print(f"  Avg Accumulation Score: {avg_acc_score:.2f}/10")
        print(f"  Avg Exit Score: {avg_exit_score:.2f}/10")
        print(f"  Entry Signals: Moderate={moderate_buy}, Stealth={stealth}")
        print(f"  Exit Signals: Momentum={momentum_exit}, Profit={profit_exit}")
    
    # Consistency analysis
    print(f"\n\n{'='*70}")
    print("🎯 CONSISTENCY ANALYSIS")
    print(f"{'='*70}\n")
    
    # Compare first vs second half
    if 'First Half (12mo)' in results and 'Second Half (12mo)' in results:
        first = results['First Half (12mo)']
        second = results['Second Half (12mo)']
        
        return_diff = abs(first['total_return'] - second['total_return'])
        signal_consistency = abs(first['moderate_buy'] - second['moderate_buy'])
        
        print("First Half vs Second Half:")
        print(f"  Return Difference: {return_diff:.2f}%")
        
        if return_diff < 20:
            print(f"    ✅ Consistent performance across periods")
        elif return_diff < 50:
            print(f"    ⚠️ Moderate variation - performance depends on period")
        else:
            print(f"    🚨 Large variation - strategy may not be robust")
        
        print(f"\n  Signal Generation:")
        print(f"    First half: {first['moderate_buy']} Moderate Buy, {first['stealth']} Stealth")
        print(f"    Second half: {second['moderate_buy']} Moderate Buy, {second['stealth']} Stealth")
        
        if signal_consistency > first['moderate_buy'] * 0.5:
            print(f"    ⚠️ Signal generation varies significantly between periods")
        else:
            print(f"    ✅ Signal generation relatively consistent")
    
    print(f"\n\n{'='*70}")
    print("💡 INTERPRETATION")
    print(f"{'='*70}\n")
    
    print("Walk-forward validation tests if strategy works consistently")
    print("across different market conditions and time periods.\n")
    
    print("✅ GOOD SIGN: Similar performance in all periods")
    print("⚠️ WARNING: Performance concentrated in one period")
    print("🚨 BAD SIGN: Strategy only works in specific conditions\n")


def test_multiple_tickers(tickers: list = None):
    """Quick walk-forward test on multiple tickers."""
    if tickers is None:
        tickers = ['NVDA', 'MSFT', 'PLTR']
    
    print(f"\n{'='*70}")
    print(f"🔍 MULTI-TICKER WALK-FORWARD VALIDATION")
    print(f"{'='*70}\n")
    
    for ticker in tickers:
        print(f"\n--- {ticker} ---")
        try:
            run_walk_forward_test(ticker, '24mo')
        except Exception as e:
            print(f"❌ Error analyzing {ticker}: {e}")
        
        print()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        ticker = sys.argv[1].upper()
        run_walk_forward_test(ticker, '24mo')
    else:
        # Test a few key tickers
        print("\n🔍 VALIDATION #4: WALK-FORWARD TESTING")
        print(f"{'='*70}")
        print("\nTesting performance consistency across time periods...")
        test_multiple_tickers(['NVDA', 'MSFT', 'AMD'])
    
    print(f"\n\n{'='*70}")
    print("✅ VALIDATION #4 COMPLETE")
    print(f"{'='*70}\n")
    print("Next: Review all 4 validations and provide final assessment")
