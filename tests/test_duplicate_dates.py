"""
Test for Duplicate Dates Issue

Check if SPY Excel file has duplicate dates causing regime shading issues.
"""

import pandas as pd
import sys
import os

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)


def check_duplicates():
    # Load SPY Excel data
    excel_path = os.path.join(parent_dir, 'results_volume/SPY_6mo_20221208_20251125_data.xlsx')
    
    print("="*80)
    print("DUPLICATE DATES CHECK")
    print("="*80)
    
    df = pd.read_excel(excel_path, sheet_name='Analysis_Data')
    df['Date'] = pd.to_datetime(df['Date'])
    
    print(f"\n📊 Total rows in Excel: {len(df)}")
    print(f"   Unique dates: {df['Date'].nunique()}")
    print(f"   Duplicate dates: {len(df) - df['Date'].nunique()}")
    
    # Find duplicates
    duplicates = df[df.duplicated('Date', keep=False)].sort_values('Date')
    
    if len(duplicates) > 0:
        print(f"\n❌ FOUND {len(duplicates)} DUPLICATE DATE ENTRIES!")
        print("\n📅 Duplicate dates (showing first 20):")
        dup_dates = duplicates['Date'].unique()[:20]
        for date in dup_dates:
            count = (duplicates['Date'] == date).sum()
            print(f"   {date.strftime('%Y-%m-%d')}: {count} copies")
        
        # Check regime values for duplicates
        print(f"\n🔍 Checking regime values for duplicates:")
        for date in dup_dates[:5]:
            dup_rows = df[df['Date'] == date]
            print(f"\n   {date.strftime('%Y-%m-%d')} ({len(dup_rows)} copies):")
            for idx, row in dup_rows.iterrows():
                regime = row['Overall_Regime_OK'] if 'Overall_Regime_OK' in df.columns else 'N/A'
                print(f"     Row {idx}: Overall_Regime_OK = {regime}")
        
        print(f"\n⚠️  DIAGNOSIS: Duplicate dates will cause")
        print(f"   incorrect regime segment calculations!")
        print(f"\n💡 SOLUTION: Remove duplicates before charting")
        
    else:
        print(f"\n✅ No duplicate dates found")
        print(f"   Issue must be elsewhere")


if __name__ == "__main__":
    check_duplicates()
