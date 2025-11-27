"""
Test Regime Chart from Excel Data

Load SPY data from Excel file and generate chart to verify
if the issue is data corruption between Excel save and chart creation.
"""

import pandas as pd
import sys
import os

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from chart_builder_plotly import generate_analysis_chart


def main():
    print("="*80)
    print("REGIME CHART TEST FROM EXCEL DATA")
    print("="*80)
    
    # Load SPY Excel data
    excel_path = '../results_volume/SPY_6mo_20221208_20251125_data.xlsx'
    
    print(f"\n📂 Loading data from: {excel_path}")
    df = pd.read_excel(excel_path, sheet_name='Analysis_Data')
    
    # Set Date as index
    df['Date'] = pd.to_datetime(df['Date'])
    df.set_index('Date', inplace=True)
    
    print(f"✅ Loaded {len(df)} days of data")
    print(f"   Date range: {df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')}")
    
    # Check regime data
    print(f"\n📊 LAST 10 DAYS REGIME STATUS FROM EXCEL:")
    print("="*80)
    for idx in df.tail(10).index:
        overall = df.loc[idx, 'Overall_Regime_OK']
        status = "✅ TRUE (GREEN)" if overall else "❌ FALSE (RED)"
        print(f"   {idx.strftime('%Y-%m-%d')}: {status}")
    
    last_day_regime = df['Overall_Regime_OK'].iloc[-1]
    print(f"\n🎯 Last day (Nov 25) regime in Excel: {'✅ TRUE (GREEN)' if last_day_regime else '❌ FALSE (RED)'}")
    
    # Generate chart from this exact data
    print(f"\n📈 Generating chart from Excel data...")
    output_path = '../results_volume/TEST_SPY_from_excel.html'
    
    try:
        generate_analysis_chart(
            df=df,
            ticker="SPY_from_Excel",
            period="6mo",
            save_path=output_path,
            show=False
        )
        
        print(f"✅ Chart saved to: {output_path}")
        print(f"\n{'='*80}")
        print("🔍 CRITICAL VERIFICATION:")
        print("="*80)
        print(f"1. Excel data shows Nov 25 as: {'GREEN' if last_day_regime else 'RED'}")
        print(f"2. Open TEST_SPY_from_excel.html and check if Nov 25 is: {'GREEN' if last_day_regime else 'RED'}")
        print(f"\n   If chart matches Excel → Chart rendering is CORRECT")
        print(f"   If chart differs from Excel → Data is being corrupted DURING chart creation")
        
    except Exception as e:
        print(f"❌ Error generating chart: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
