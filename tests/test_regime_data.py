"""
Test Regime Data Verification

This script verifies that the Overall_Regime_OK flag is being set correctly
in the actual analysis pipeline before the chart is created.
"""

import pandas as pd
import sys
import os
sys.path.insert(0, os.path.abspath('..'))

from vol_analysis import analyze_ticker


def test_regime_data(ticker='SPY', period='1mo'):
    """
    Run analysis and examine the regime data before charting.
    """
    print("="*80)
    print(f"REGIME DATA VERIFICATION TEST: {ticker} ({period})")
    print("="*80)
    
    # Run analysis and capture the DataFrame
    print(f"\n🚀 Running analysis for {ticker}...")
    result = analyze_ticker(
        ticker=ticker,
        period=period,
        save_to_file=False,
        output_dir='../results_volume',
        save_chart=False,
        show_chart=False,
        show_summary=False,
        debug=False,
        chart_backend='plotly'
    )
    
    if isinstance(result, tuple):
        df, _ = result
    else:
        df = result
    
    print(f"\n✅ Analysis complete. DataFrame has {len(df)} rows")
    print(f"   Date range: {df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')}")
    
    # Check if Overall_Regime_OK column exists
    if 'Overall_Regime_OK' not in df.columns:
        print("\n❌ ERROR: Overall_Regime_OK column not found in DataFrame!")
        print(f"   Available columns with 'Regime' in name:")
        regime_cols = [col for col in df.columns if 'Regime' in col or 'regime' in col]
        for col in regime_cols:
            print(f"   - {col}")
        return
    
    # Examine the last 10 days of regime data
    print(f"\n📊 LAST 10 DAYS OF REGIME DATA:")
    print("="*80)
    print(f"{'Date':<12} {'Overall_Regime_OK':<20} {'Market_Regime_OK':<20} {'Sector_Regime_OK':<20}")
    print("-"*80)
    
    for idx in df.tail(10).index:
        overall = df.loc[idx, 'Overall_Regime_OK']
        market = df.loc[idx, 'Market_Regime_OK'] if 'Market_Regime_OK' in df.columns else 'N/A'
        sector = df.loc[idx, 'Sector_Regime_OK'] if 'Sector_Regime_OK' in df.columns else 'N/A'
        
        overall_str = "✅ TRUE (GREEN)" if overall else "❌ FALSE (RED)"
        market_str = "✅ TRUE" if market == True else "❌ FALSE" if market == False else str(market)
        sector_str = "✅ TRUE" if sector == True else "❌ FALSE" if sector == False else str(sector)
        
        print(f"{idx.strftime('%Y-%m-%d'):<12} {overall_str:<20} {market_str:<20} {sector_str:<20}")
    
    # Count regime changes
    regime_changes = df['Overall_Regime_OK'].ne(df['Overall_Regime_OK'].shift()).fillna(True)
    change_count = regime_changes.sum()
    
    print(f"\n📈 REGIME STATISTICS:")
    print(f"   Total regime changes: {change_count}")
    print(f"   TRUE (GREEN) days: {df['Overall_Regime_OK'].sum()}")
    print(f"   FALSE (RED) days: {(~df['Overall_Regime_OK']).sum()}")
    print(f"   Last day regime: {'✅ TRUE (GREEN)' if df['Overall_Regime_OK'].iloc[-1] else '❌ FALSE (RED)'}")
    
    # Show actual positions where changes occur
    print(f"\n🔄 REGIME CHANGE POSITIONS (for chart rendering):")
    change_positions = df[regime_changes].index.tolist()
    for i, change_date in enumerate(change_positions[-5:]):  # Last 5 changes
        pos = df.index.get_loc(change_date)
        regime_value = df.loc[change_date, 'Overall_Regime_OK']
        print(f"   Position {pos}: {change_date.strftime('%Y-%m-%d')} → {'GREEN' if regime_value else 'RED'}")
    
    print("\n" + "="*80)
    print("✅ DIAGNOSIS COMPLETE")
    print("="*80)
    print("\n💡 Compare this data with what you see in the HTML chart.")
    print("   If the chart doesn't match this data, the issue is in chart rendering.")
    print("   If the chart matches but it's wrong, the issue is in regime calculation.")


if __name__ == "__main__":
    test_regime_data('SPY', '1mo')
