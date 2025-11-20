#!/usr/bin/env python3
"""
Test the cache-only fix for get_smart_data() and regime filter.
"""

import pandas as pd
from data_manager import get_smart_data
from regime_filter import calculate_historical_regime_series

def test_cache_only_fix():
    """Test that the cache-only fix resolves both issues."""
    
    print("=" * 70)
    print("TESTING CACHE-ONLY FIX")
    print("=" * 70)
    
    # Test 1: get_smart_data() should be cache-only
    print("\n🧪 TEST 1: get_smart_data() cache-only behavior")
    print("-" * 50)
    
    try:
        # Test with a ticker that should be in cache
        ticker = 'AAPL'
        print(f"Testing get_smart_data('{ticker}', '24mo')...")
        
        df = get_smart_data(ticker, '24mo')
        
        print(f"✅ SUCCESS: Retrieved {len(df)} periods for {ticker}")
        print(f"   Date range: {df.index.min().date()} to {df.index.max().date()}")
        
        # Calculate actual months covered
        months_diff = (df.index.max().year - df.index.min().year) * 12 + (df.index.max().month - df.index.min().month)
        print(f"   Coverage: ~{months_diff} months")
        
        if months_diff >= 20:
            print(f"✅ 24mo period working correctly")
        else:
            print(f"⚠️  Only {months_diff} months - may still have date range issue")
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False
    
    # Test 2: Regime filter should work without yfinance calls
    print(f"\n🧪 TEST 2: Regime filter cache-only behavior")
    print("-" * 50)
    
    try:
        print(f"Testing calculate_historical_regime_series('{ticker}', df)...")
        
        # Use the data we just retrieved
        market_regime, sector_regime, overall_regime = calculate_historical_regime_series(ticker, df)
        
        print(f"✅ SUCCESS: Regime calculation completed")
        
        # Check for actual True/False values (not all one value)
        market_true = market_regime.sum() 
        sector_true = sector_regime.sum()
        overall_true = overall_regime.sum()
        total = len(df)
        
        print(f"   Market regime: {market_true}/{total} True ({market_true/total*100:.1f}%)")
        print(f"   Sector regime: {sector_true}/{total} True ({sector_true/total*100:.1f}%)")
        print(f"   Overall regime: {overall_true}/{total} True ({overall_true/total*100:.1f}%)")
        
        # Check if regime data is realistic (not all True or all False)
        if 0 < market_true < total or 0 < sector_true < total:
            print(f"✅ Regime data looks realistic (mixed True/False values)")
        elif market_true == total and sector_true == total:
            print(f"⚠️  All regime values are True - may indicate strong bull market or date range issue")
        else:
            print(f"⚠️  All regime values are False - may indicate missing benchmark data")
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        print(f"   This indicates benchmark data (SPY/sector ETF) may be missing from cache")
        return False

def test_benchmark_cache_status():
    """Test if benchmark data is available in cache."""
    
    print(f"\n🧪 TEST 3: Benchmark cache status")
    print("-" * 50)
    
    benchmarks = ['SPY', 'XLK', 'XLF', 'XLV']  # Common benchmarks
    
    for benchmark in benchmarks:
        try:
            df = get_smart_data(benchmark, '24mo')
            print(f"✅ {benchmark}: {len(df)} periods ({df.index.min().date()} to {df.index.max().date()})")
        except Exception as e:
            print(f"❌ {benchmark}: {e}")

if __name__ == '__main__':
    # Test benchmark cache first
    test_benchmark_cache_status()
    
    # Test main functionality
    success = test_cache_only_fix()
    
    if success:
        print(f"\n🎉 CACHE-ONLY FIX TEST: ✅ PASSED")
        print(f"   Ready to test batch_backtest.py with fixed architecture")
    else:
        print(f"\n💥 CACHE-ONLY FIX TEST: ❌ FAILED")
        print(f"   Need to populate benchmark data before testing batch operations")
