#!/usr/bin/env python3
"""
Debug script for regime filter issues.

Tests calculate_historical_regime_series() directly to identify failure points.
"""

import pandas as pd
import numpy as np
import sys
import traceback
from regime_filter import calculate_historical_regime_series
from analysis_service import prepare_analysis_dataframe

def test_regime_filter_debug(ticker='AAPL'):
    """Test regime filter with detailed debugging."""
    
    print(f"\n{'='*70}")
    print(f"REGIME FILTER DEBUG TEST - {ticker}")
    print(f"{'='*70}")
    
    try:
        # Step 1: Get sample data using the same pipeline as batch_backtest
        print(f"Step 1: Loading data for {ticker}...")
        df = prepare_analysis_dataframe(
            ticker=ticker,
            period='12mo',
            data_source='yfinance',
            force_refresh=False,
            verbose=True
        )
        
        print(f"✅ Data loaded: {len(df)} rows from {df.index.min().date()} to {df.index.max().date()}")
        
        # Check if regime columns exist and their values
        regime_cols = ['Market_Regime_OK', 'Sector_Regime_OK', 'Overall_Regime_OK']
        
        print(f"\n📊 Regime Column Analysis:")
        for col in regime_cols:
            if col in df.columns:
                true_count = df[col].sum()
                total_count = len(df)
                false_count = total_count - true_count
                
                print(f"  {col}:")
                print(f"    True: {true_count}/{total_count} ({true_count/total_count*100:.1f}%)")
                print(f"    False: {false_count}/{total_count} ({false_count/total_count*100:.1f}%)")
                
                if true_count == total_count:
                    print(f"    ⚠️  ALL VALUES ARE TRUE - This suggests regime filter failed!")
                elif false_count == total_count:
                    print(f"    ⚠️  ALL VALUES ARE FALSE - Conservative fallback active")
                else:
                    print(f"    ✅ Mixed values - regime filter working correctly")
            else:
                print(f"  ❌ {col}: Column missing!")
        
        # Step 2: Test the regime calculation function directly
        print(f"\n📊 Direct Regime Function Test:")
        print(f"Testing calculate_historical_regime_series({ticker}, df)...")
        
        # Create a smaller test DataFrame to isolate the function
        test_df = df.iloc[-60:].copy()  # Last 60 days
        print(f"Test DataFrame: {len(test_df)} rows from {test_df.index.min().date()} to {test_df.index.max().date()}")
        
        market_regime, sector_regime, overall_regime = calculate_historical_regime_series(ticker, test_df)
        
        print(f"\n✅ Regime calculation succeeded!")
        print(f"Market regime: {market_regime.sum()}/{len(market_regime)} True ({market_regime.sum()/len(market_regime)*100:.1f}%)")
        print(f"Sector regime: {sector_regime.sum()}/{len(sector_regime)} True ({sector_regime.sum()/len(sector_regime)*100:.1f}%)")
        print(f"Overall regime: {overall_regime.sum()}/{len(overall_regime)} True ({overall_regime.sum()/len(overall_regime)*100:.1f}%)")
        
        # Check if all values are True (the problem we're looking for)
        if market_regime.sum() == len(market_regime) and sector_regime.sum() == len(sector_regime):
            print(f"\n⚠️  ALL REGIME VALUES ARE TRUE - This is suspicious!")
            print(f"    This suggests either:")
            print(f"    1. SPY has been above 200MA for all 60 days")
            print(f"    2. Sector ETF has been above 50MA for all 60 days")
            print(f"    3. There's a bug in the calculation")
            
            # Let's check the raw data
            from regime_filter import load_benchmark_data, get_sector_etf
            
            print(f"\n🔍 Raw Benchmark Data Check:")
            
            # Check SPY data
            spy_data = load_benchmark_data('SPY', period='12mo')
            if spy_data is not None and len(spy_data) >= 200:
                spy_data['MA200'] = spy_data['Close'].rolling(200, min_periods=200).mean()
                latest_spy = spy_data.dropna(subset=['MA200']).iloc[-1]
                spy_above = latest_spy['Close'] > latest_spy['MA200']
                
                print(f"  SPY: ${latest_spy['Close']:.2f} vs 200MA ${latest_spy['MA200']:.2f} ({'ABOVE' if spy_above else 'BELOW'})")
            else:
                print(f"  ❌ SPY data insufficient or missing")
                
            # Check sector ETF data
            sector_etf = get_sector_etf(ticker)
            sector_data = load_benchmark_data(sector_etf, period='6mo')
            if sector_data is not None and len(sector_data) >= 50:
                sector_data['MA50'] = sector_data['Close'].rolling(50, min_periods=50).mean()
                latest_sector = sector_data.dropna(subset=['MA50']).iloc[-1]
                sector_above = latest_sector['Close'] > latest_sector['MA50']
                
                print(f"  {sector_etf}: ${latest_sector['Close']:.2f} vs 50MA ${latest_sector['MA50']:.2f} ({'ABOVE' if sector_above else 'BELOW'})")
            else:
                print(f"  ❌ {sector_etf} data insufficient or missing")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR in regime filter test:")
        print(f"   {type(e).__name__}: {str(e)}")
        print(f"\n📋 Full traceback:")
        traceback.print_exc()
        return False


def test_cache_status():
    """Check cache status for key benchmarks."""
    
    print(f"\n{'='*70}")
    print(f"CACHE STATUS CHECK")
    print(f"{'='*70}")
    
    from data_manager import get_smart_data
    
    benchmarks = ['SPY', 'XLK', 'XLF', 'XLV', 'XLE']  # Common sector ETFs
    
    for symbol in benchmarks:
        try:
            data = get_smart_data(symbol, period='12mo', force_refresh=False)
            if data is not None and not data.empty:
                print(f"✅ {symbol}: {len(data)} rows from {data.index.min().date()} to {data.index.max().date()}")
            else:
                print(f"❌ {symbol}: No data available")
        except Exception as e:
            print(f"❌ {symbol}: Error loading - {e}")


if __name__ == '__main__':
    # Test cache first
    test_cache_status()
    
    # Test regime filter
    ticker = sys.argv[1] if len(sys.argv) > 1 else 'AAPL'
    success = test_regime_filter_debug(ticker)
    
    if success:
        print(f"\n✅ Debug test completed successfully")
    else:
        print(f"\n❌ Debug test failed - see errors above")
