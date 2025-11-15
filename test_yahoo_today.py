#!/usr/bin/env python3
"""
Test script to check if Yahoo Finance has today's data available for tickers.

Usage:
    python test_yahoo_today.py
"""

import yfinance as yf
import pandas as pd
from datetime import datetime

def read_tickers(filename='cmb.txt'):
    """Read tickers from file."""
    tickers = []
    with open(filename, 'r') as f:
        for line in f:
            ticker = line.strip().upper()
            if ticker and not ticker.startswith('#'):
                tickers.append(ticker)
    return tickers

def test_yahoo_today():
    """Test if Yahoo has today's data for all tickers."""
    print("="*70)
    print("YAHOO FINANCE - TODAY'S DATA AVAILABILITY TEST")
    print("="*70)
    
    today = datetime.now()
    print(f"\nTest Date: {today.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Market Day: {today.strftime('%A, %B %d, %Y')}\n")
    
    # Read tickers
    tickers = read_tickers('cmb.txt')
    print(f"Testing {len(tickers)} tickers from cmb.txt\n")
    print("-"*70)
    
    # Test each ticker
    results = []
    
    for i, ticker in enumerate(tickers, 1):
        try:
            # Download today's data
            df = yf.download(ticker, period='1d', progress=False)
            
            if not df.empty:
                # Get the last date in the data
                last_date = df.index[-1]
                last_date_str = last_date.strftime('%Y-%m-%d')
                today_str = today.strftime('%Y-%m-%d')
                
                # Check if we got today's data
                has_today = last_date_str == today_str
                
                results.append({
                    'ticker': ticker,
                    'has_data': True,
                    'last_date': last_date_str,
                    'has_today': has_today,
                    'close': df['Close'].iloc[-1],
                    'volume': df['Volume'].iloc[-1]
                })
                
                status = "✅ TODAY" if has_today else f"⚠️ OLD ({last_date_str})"
                close_price = float(df['Close'].iloc[-1])
                volume = int(df['Volume'].iloc[-1])
                print(f"[{i:2d}/{len(tickers)}] {ticker:6s}: {status} - Close: ${close_price:.2f}, Vol: {volume:,}")
            else:
                results.append({
                    'ticker': ticker,
                    'has_data': False,
                    'last_date': None,
                    'has_today': False,
                    'close': None,
                    'volume': None
                })
                print(f"[{i:2d}/{len(tickers)}] {ticker:6s}: ❌ NO DATA")
                
        except Exception as e:
            results.append({
                'ticker': ticker,
                'has_data': False,
                'last_date': None,
                'has_today': False,
                'close': None,
                'volume': None
            })
            print(f"[{i:2d}/{len(tickers)}] {ticker:6s}: ❌ ERROR - {str(e)}")
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    total = len(results)
    has_data = sum(1 for r in results if r['has_data'])
    has_today = sum(1 for r in results if r['has_today'])
    no_data = total - has_data
    
    print(f"\nTotal Tickers: {total}")
    print(f"✅ Has Today's Data ({today.strftime('%Y-%m-%d')}): {has_today}")
    print(f"⚠️ Has Old Data: {has_data - has_today}")
    print(f"❌ No Data Available: {no_data}")
    
    if has_today > 0:
        print(f"\n🎯 SUCCESS: Yahoo Finance has today's data for {has_today}/{total} tickers")
    else:
        print(f"\n⚠️ WARNING: No tickers have today's data yet")
        print("   This may be normal if:")
        print("   - Market hasn't closed yet")
        print("   - Yahoo data not updated yet (typically available by 6-8pm ET)")
    
    # Show tickers without today's data
    old_data = [r for r in results if r['has_data'] and not r['has_today']]
    if old_data:
        print(f"\n📊 Tickers with old data:")
        for r in old_data:
            print(f"   • {r['ticker']}: Last data from {r['last_date']}")
    
    no_data_tickers = [r for r in results if not r['has_data']]
    if no_data_tickers:
        print(f"\n❌ Tickers with no data:")
        for r in no_data_tickers:
            print(f"   • {r['ticker']}")

if __name__ == '__main__':
    test_yahoo_today()
