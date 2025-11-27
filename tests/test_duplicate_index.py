"""
Test for Duplicate Index Values

Check if there are duplicate index values after setting Date as index.
"""

import pandas as pd
import sys
import os

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)


def check_index_duplicates():
    # Load SPY Excel data
    excel_path = os.path.join(parent_dir, 'results_volume/SPY_6mo_20221208_20251125_data.xlsx')
    
    print("="*80)
    print("DUPLICATE INDEX CHECK (AFTER SETTING DATE AS INDEX)")
    print("="*80)
    
    df = pd.read_excel(excel_path, sheet_name='Analysis_Data')
    df['Date'] = pd.to_datetime(df['Date'])
    
    print(f"\n📊 BEFORE setting index:")
    print(f"   Total rows: {len(df)}")
    print(f"   Unique dates: {df['Date'].nunique()}")
    
    # Set Date as index (this is what the chart code does)
    df.set_index('Date', inplace=True)
    
    print(f"\n📊 AFTER setting Date as index:")
    print(f"   Total rows: {len(df)}")
    print(f"   Unique index values: {df.index.nunique()}")
    print(f"   Has duplicate index: {df.index.has_duplicates}")
    
    if df.index.has_duplicates:
        print(f"\n❌ FOUND DUPLICATE INDEX VALUES!")
        
        # Find which dates are duplicated
        dup_mask = df.index.duplicated(keep=False)
        dup_dates = df[dup_mask].index.unique()
        
        print(f"\n   Dates with duplicates: {len(dup_dates)}")
        print(f"\n📅 Duplicate index entries (first 10):")
        for date in dup_dates[:10]:
            count = (df.index == date).sum()
            print(f"   {date.strftime('%Y-%m-%d')}: {count} entries")
            
            # Show regime values for this date
            rows = df.loc[date]
            if isinstance(rows, pd.Series):
                regime = rows['Overall_Regime_OK'] if 'Overall_Regime_OK' in df.columns else 'N/A'
                print(f"     Overall_Regime_OK: {regime}")
            else:
                print(f"     Multiple rows found:")
                for i, (idx, row) in enumerate(rows.iterrows() if hasattr(rows, 'iterrows') else [(None, rows)]):
                    regime = row['Overall_Regime_OK'] if 'Overall_Regime_OK' in df.columns else 'N/A'
                    print(f"       Row {i+1}: Overall_Regime_OK = {regime}")
        
        # Check specifically for Nov dates
        print(f"\n🔍 November 2025 dates:")
        nov_df = df[df.index >= '2025-11-01']
        for date in nov_df.index.unique():
            count = (df.index == date).sum()
            if count > 1:
                print(f"   {date.strftime('%Y-%m-%d')}: {count} entries ❌")
            else:
                regime = df.loc[date, 'Overall_Regime_OK']
                print(f"   {date.strftime('%Y-%m-%d')}: 1 entry, regime={regime}")
        
        print(f"\n⚠️  DIAGNOSIS: Duplicate index values break regime")
        print(f"   segment calculations in Plotly charts!")
        print(f"\n💡 SOLUTION: Remove duplicate rows before creating charts")
    else:
        print(f"\n✅ No duplicate index values")
        print(f"   Issue must be in the chart rendering logic")


if __name__ == "__main__":
    check_index_duplicates()
