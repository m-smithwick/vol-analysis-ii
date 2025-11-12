#!/usr/bin/env python3
"""
Test script for Massive.com flat file integration.

This script tests the Massive.com data provider and its integration
with the existing data_manager module.
"""

import sys
from datetime import datetime, timedelta

# Add error handling
try:
    from massive_data_provider import (
        MassiveDataProvider,
        get_massive_daily_data,
        test_massive_connection
    )
    from data_manager import get_smart_data, clear_cache
    from error_handler import setup_logging, logger
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure all required modules are available")
    sys.exit(1)

# Configure logging
setup_logging()

def test_connection():
    """Test 1: Verify S3 connection to Massive.com"""
    print("\n" + "="*70)
    print("TEST 1: Connection Test")
    print("="*70)
    
    result = test_massive_connection()
    if result:
        print("✅ Connection test PASSED")
        return True
    else:
        print("❌ Connection test FAILED")
        return False

def test_direct_fetch():
    """Test 2: Direct fetch using Massive provider"""
    print("\n" + "="*70)
    print("TEST 2: Direct Fetch Test (5 days of AAPL data)")
    print("="*70)
    
    try:
        df = get_massive_daily_data('AAPL', '5d')
        
        if df.empty:
            print("❌ No data retrieved")
            return False
        
        print(f"✅ Retrieved {len(df)} days of data")
        print(f"   Date range: {df.index[0].date()} to {df.index[-1].date()}")
        print(f"   Columns: {list(df.columns)}")
        print("\nFirst 3 rows:")
        print(df.head(3))
        return True
        
    except Exception as e:
        print(f"❌ Error during direct fetch: {e}")
        return False

def test_data_manager_integration():
    """Test 3: Integration with data_manager"""
    print("\n" + "="*70)
    print("TEST 3: Data Manager Integration")
    print("="*70)
    
    ticker = "MSFT"
    
    # Clear any existing cache
    print(f"Clearing cache for {ticker}...")
    clear_cache(ticker, "1d")
    
    try:
        # Fetch using Massive data source
        print(f"\nFetching {ticker} data via Massive.com...")
        df_massive = get_smart_data(ticker, "5d", data_source="massive")
        
        if df_massive.empty:
            print("❌ No data retrieved from Massive")
            return False
        
        print(f"✅ Retrieved {len(df_massive)} days via Massive.com")
        print(f"   Date range: {df_massive.index[0].date()} to {df_massive.index[-1].date()}")
        
        # Verify it was cached
        print(f"\nVerifying data was cached...")
        df_cached = get_smart_data(ticker, "5d")
        
        if df_cached.empty:
            print("❌ Cache verification failed")
            return False
        
        print(f"✅ Cache verified: {len(df_cached)} days")
        
        # Compare data
        if len(df_massive) == len(df_cached):
            print("✅ Data consistency check PASSED")
        else:
            print(f"⚠️ Data length mismatch: Massive={len(df_massive)}, Cache={len(df_cached)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during integration test: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_fallback_behavior():
    """Test 4: Fallback to yfinance on error"""
    print("\n" + "="*70)
    print("TEST 4: Fallback Behavior Test")
    print("="*70)
    
    ticker = "INVALID_TICKER_XYZ"
    
    try:
        print(f"Attempting to fetch invalid ticker {ticker} with Massive source...")
        df = get_smart_data(ticker, "5d", data_source="massive")
        
        if not df.empty:
            print("⚠️ Unexpectedly got data for invalid ticker")
            return False
        
        print("✅ Correctly handled invalid ticker (returned empty DataFrame)")
        return True
        
    except Exception as e:
        print(f"✅ Correctly raised exception for invalid ticker: {type(e).__name__}")
        return True

def test_data_format_compatibility():
    """Test 5: Verify data format matches yfinance"""
    print("\n" + "="*70)
    print("TEST 5: Data Format Compatibility")
    print("="*70)
    
    ticker = "GOOGL"
    
    try:
        # Clear cache
        clear_cache(ticker, "1d")
        
        # Fetch from Massive
        print(f"Fetching {ticker} from Massive.com...")
        df_massive = get_smart_data(ticker, "3d", data_source="massive")
        
        # Clear cache again
        clear_cache(ticker, "1d")
        
        # Fetch from yfinance
        print(f"Fetching {ticker} from yfinance...")
        df_yfinance = get_smart_data(ticker, "3d", data_source="yfinance")
        
        if df_massive.empty or df_yfinance.empty:
            print("❌ One or both data sources returned empty")
            return False
        
        # Check column compatibility
        massive_cols = set(df_massive.columns)
        yfinance_cols = set(df_yfinance.columns)
        
        if massive_cols == yfinance_cols:
            print(f"✅ Column names match: {list(massive_cols)}")
        else:
            print(f"❌ Column mismatch:")
            print(f"   Massive: {massive_cols}")
            print(f"   yfinance: {yfinance_cols}")
            return False
        
        # Check data types
        print("\nData type comparison:")
        for col in df_massive.columns:
            massive_dtype = df_massive[col].dtype
            yfinance_dtype = df_yfinance[col].dtype
            match = "✅" if massive_dtype == yfinance_dtype else "⚠️"
            print(f"   {col}: Massive={massive_dtype}, yfinance={yfinance_dtype} {match}")
        
        print("\n✅ Format compatibility test PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Error during format test: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("MASSIVE.COM INTEGRATION TEST SUITE")
    print("="*70)
    
    tests = [
        ("Connection Test", test_connection),
        ("Direct Fetch Test", test_direct_fetch),
        ("Data Manager Integration", test_data_manager_integration),
        ("Fallback Behavior", test_fallback_behavior),
        ("Format Compatibility", test_data_format_compatibility),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ Unexpected error in {test_name}: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests PASSED! Massive.com integration is working correctly.")
        return 0
    else:
        print(f"\n⚠️ {total - passed} test(s) FAILED. Review errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
