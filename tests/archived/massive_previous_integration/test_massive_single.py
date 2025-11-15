#!/usr/bin/env python3
"""
Simple test for Massive.com integration with single ticker T.
Respects API rate limits by only fetching one ticker.
"""

from data_manager import get_smart_data, clear_cache
from error_handler import setup_logging

# Configure logging
setup_logging()

def test_ticker_t():
    """Test Massive.com data fetch for ticker T (AT&T)"""
    
    print("\n" + "="*70)
    print("MASSIVE.COM SINGLE TICKER TEST: T (AT&T)")
    print("="*70)
    
    ticker = "T"
    
    # Clear any cached data
    print(f"\n1. Clearing cache for {ticker}...")
    clear_cache(ticker, '1d')
    print("   ✅ Cache cleared")
    
    # Fetch from Massive.com
    print(f"\n2. Fetching {ticker} data via Massive.com (5 days)...")
    try:
        df = get_smart_data(ticker, '5d', data_source='massive')
        
        if df.empty:
            print("   ❌ No data retrieved")
            return False
        
        print(f"   ✅ Success! Retrieved {len(df)} days of data")
        print(f"   Date range: {df.index[0].date()} to {df.index[-1].date()}")
        print(f"   Columns: {list(df.columns)}")
        
        # Show sample data
        print("\n3. Sample data (first 3 rows):")
        print(df.head(3))
        
        # Verify data was cached
        print("\n4. Verifying data was cached...")
        df_cached = get_smart_data(ticker, '5d')
        if not df_cached.empty:
            print(f"   ✅ Cache verified: {len(df_cached)} days cached")
        else:
            print("   ⚠️ Cache verification issue")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_ticker_t()
    
    print("\n" + "="*70)
    if success:
        print("✅ TEST PASSED: Massive.com integration works for ticker T")
    else:
        print("❌ TEST FAILED: See errors above")
    print("="*70 + "\n")
