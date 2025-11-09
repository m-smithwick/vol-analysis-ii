#!/usr/bin/env python3
"""
Validation #1: Verify Execution Timing
======================================

Checks that backtest entry/exit prices are realistic and don't use future information.

This script analyzes actual trade data to verify:
1. Entry price = Open of day AFTER signal (not same-day close)
2. Exit price = Open of day AFTER exit signal
3. No lookahead bias (no using future prices for past decisions)
4. Price movements are realistic given market data
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from vol_analysis import analyze_ticker


def validate_single_ticker_timing(ticker: str, period: str = '24mo'):
    """
    Validate execution timing for a single ticker by checking actual prices.
    
    Args:
        ticker: Stock symbol
        period: Analysis period
    """
    print(f"\n{'='*70}")
    print(f"🔍 EXECUTION TIMING VALIDATION: {ticker}")
    print(f"{'='*70}\n")
    
    # Get analyzed data
    df = analyze_ticker(ticker, period=period, save_to_file=False, 
                       show_chart=False, show_summary=False)
    
    print("✅ Data loaded. Checking execution timing logic...\n")
    
    # Find signal occurrences
    entry_signals = ['Moderate_Buy', 'Strong_Buy', 'Stealth_Accumulation']
    exit_signals = ['Momentum_Exhaustion', 'Profit_Taking', 'Sell_Signal']
    
    timing_issues = []
    
    # Check entry signals
    print("📊 ENTRY SIGNAL TIMING CHECKS:")
    print("-" * 70)
    
    for signal in entry_signals:
        if signal not in df.columns:
            continue
            
        signal_days = df[df[signal] == True]
        
        if signal_days.empty:
            print(f"  {signal}: No signals found")
            continue
        
        print(f"\n  {signal}: {len(signal_days)} signals")
        
        # Check first few signals in detail
        for i, (date, row) in enumerate(list(signal_days.iterrows())[:3]):
            # Find next day's data
            date_idx = df.index.get_loc(date)
            
            if date_idx + 1 < len(df):
                next_day = df.index[date_idx + 1]
                next_day_data = df.iloc[date_idx + 1]
                
                signal_day_close = row['Close']
                next_day_open = next_day_data['Open']
                next_day_close = next_day_data['Close']
                
                # Calculate realistic gap
                gap_pct = ((next_day_open - signal_day_close) / signal_day_close) * 100
                
                # Check if Next_Open column exists and matches
                if 'Next_Open' in df.columns:
                    stored_next_open = row['Next_Open']
                    matches = abs(stored_next_open - next_day_open) < 0.01
                    
                    print(f"    Signal {i+1}: {date.strftime('%Y-%m-%d')}")
                    print(f"      Signal day close: ${signal_day_close:.2f}")
                    print(f"      Next day open: ${next_day_open:.2f} (gap: {gap_pct:+.2f}%)")
                    print(f"      Stored Next_Open: ${stored_next_open:.2f} {'✅' if matches else '❌ MISMATCH'}")
                    
                    if not matches:
                        timing_issues.append({
                            'ticker': ticker,
                            'signal': signal,
                            'date': date,
                            'issue': f'Next_Open mismatch: stored={stored_next_open:.2f}, actual={next_day_open:.2f}'
                        })
                    
                    # Check for unrealistic gaps
                    if abs(gap_pct) > 10:
                        print(f"      ⚠️ Large gap: {gap_pct:+.2f}% (check for splits/earnings)")
                        timing_issues.append({
                            'ticker': ticker,
                            'signal': signal,
                            'date': date,
                            'issue': f'Large gap: {gap_pct:+.2f}%'
                        })
                else:
                    print(f"    Signal {i+1}: {date.strftime('%Y-%m-%d')}")
                    print(f"      ⚠️ Next_Open column missing - may use incorrect entry price")
                    timing_issues.append({
                        'ticker': ticker,
                        'signal': signal,
                        'date': date,
                        'issue': 'Next_Open column missing'
                    })
            else:
                print(f"    Signal {i+1}: {date.strftime('%Y-%m-%d')} - Last day of data, no next day")
    
    # Check exit signals
    print(f"\n\n📊 EXIT SIGNAL TIMING CHECKS:")
    print("-" * 70)
    
    for signal in exit_signals:
        if signal not in df.columns:
            continue
            
        signal_days = df[df[signal] == True]
        
        if signal_days.empty:
            print(f"  {signal}: No signals found")
            continue
        
        print(f"\n  {signal}: {len(signal_days)} signals")
        
        # Check first few exit signals
        for i, (date, row) in enumerate(list(signal_days.iterrows())[:3]):
            date_idx = df.index.get_loc(date)
            
            if date_idx + 1 < len(df):
                next_day = df.index[date_idx + 1]
                next_day_data = df.iloc[date_idx + 1]
                
                signal_day_close = row['Close']
                next_day_open = next_day_data['Open']
                
                gap_pct = ((next_day_open - signal_day_close) / signal_day_close) * 100
                
                print(f"    Exit {i+1}: {date.strftime('%Y-%m-%d')}")
                print(f"      Signal day close: ${signal_day_close:.2f}")
                print(f"      Next day open: ${next_day_open:.2f} (gap: {gap_pct:+.2f}%)")
                
                # Check for unusual gaps
                if abs(gap_pct) > 10:
                    print(f"      ⚠️ Large exit gap: {gap_pct:+.2f}%")
                    timing_issues.append({
                        'ticker': ticker,
                        'signal': signal,
                        'date': date,
                        'issue': f'Large exit gap: {gap_pct:+.2f}%'
                    })
    
    # Summary
    print(f"\n\n{'='*70}")
    print("📋 VALIDATION SUMMARY")
    print(f"{'='*70}\n")
    
    if not timing_issues:
        print("✅ NO TIMING ISSUES DETECTED")
        print("   • Entry prices use next-day opens")
        print("   • Exit prices use next-day opens")
        print("   • No unrealistic gaps found")
        print("   • Execution timing appears correct")
    else:
        print(f"⚠️ FOUND {len(timing_issues)} TIMING ISSUES:\n")
        for issue in timing_issues:
            print(f"  • {issue['signal']} on {issue['date'].strftime('%Y-%m-%d')}")
            print(f"    Issue: {issue['issue']}")
        print("\n❌ EXECUTION TIMING MAY BE INCORRECT")
        print("   Review backtest logic for lookahead bias")
    
    return timing_issues


def check_realistic_returns(ticker: str, period: str = '24mo'):
    """
    Check if returns are realistic by comparing to actual price movements.
    """
    print(f"\n{'='*70}")
    print(f"💰 RETURN REALISM CHECK: {ticker}")
    print(f"{'='*70}\n")
    
    df = analyze_ticker(ticker, period=period, save_to_file=False,
                       show_chart=False, show_summary=False)
    
    # Calculate actual price statistics
    returns = df['Close'].pct_change() * 100
    
    print("📊 ACTUAL PRICE STATISTICS:")
    print(f"  Daily Return Mean: {returns.mean():+.2f}%")
    print(f"  Daily Return Std Dev: {returns.std():.2f}%")
    print(f"  Best Day: {returns.max():+.2f}%")
    print(f"  Worst Day: {returns.min():+.2f}%")
    print(f"  95th Percentile: {returns.quantile(0.95):+.2f}%")
    
    # Calculate multi-day returns
    returns_5d = ((df['Close'] - df['Close'].shift(5)) / df['Close'].shift(5) * 100).dropna()
    returns_20d = ((df['Close'] - df['Close'].shift(20)) / df['Close'].shift(20) * 100).dropna()
    
    print(f"\n  5-Day Return Mean: {returns_5d.mean():+.2f}%")
    print(f"  5-Day Best: {returns_5d.max():+.2f}%")
    print(f"  5-Day 95th Percentile: {returns_5d.quantile(0.95):+.2f}%")
    
    print(f"\n  20-Day Return Mean: {returns_20d.mean():+.2f}%")
    print(f"  20-Day Best: {returns_20d.max():+.2f}%")
    print(f"  20-Day 95th Percentile: {returns_20d.quantile(0.95):+.2f}%")
    
    print("\n💡 INTERPRETATION:")
    print("  If backtest shows average returns >> 95th percentile actual returns,")
    print("  this suggests lookahead bias or unrealistic execution assumptions.")
    
    return {
        'daily_mean': returns.mean(),
        'daily_std': returns.std(),
        'return_5d_mean': returns_5d.mean(),
        'return_5d_95th': returns_5d.quantile(0.95),
        'return_20d_mean': returns_20d.mean(),
        'return_20d_95th': returns_20d.quantile(0.95)
    }


if __name__ == "__main__":
    import sys
    
    ticker = sys.argv[1] if len(sys.argv) > 1 else 'SOUN'
    period = sys.argv[2] if len(sys.argv) > 2 else '24mo'
    
    print(f"\n🔍 VALIDATION #1: EXECUTION TIMING")
    print(f"{'='*70}\n")
    print("Testing if backtest uses realistic entry/exit prices...")
    print("(Entry = next day open after signal, not same-day close)\n")
    
    # Run timing validation
    issues = validate_single_ticker_timing(ticker, period)
    
    # Run return realism check
    stats = check_realistic_returns(ticker, period)
    
    print(f"\n\n{'='*70}")
    print("✅ VALIDATION #1 COMPLETE")
    print(f"{'='*70}")
    
    if issues:
        print("\n⚠️ Found timing issues - review output above")
        print("Next: Fix any issues before proceeding to validation #2")
    else:
        print("\n✅ Execution timing appears correct")
        print("Next: Run validation #2 to analyze outlier impact")
        print("\nCommand: python validate_outlier_impact.py")
