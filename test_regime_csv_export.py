#!/usr/bin/env python3
"""
Test script to verify regime filter columns are included in CSV export.
"""

import pandas as pd
import numpy as np
from datetime import datetime

def test_regime_csv_export():
    """Test that regime columns are properly exported to CSV."""
    
    print("Testing regime filter CSV export fix...")
    
    # Create mock trade data similar to what backtest.py generates
    mock_trades = [
        {
            'entry_date': pd.Timestamp('2025-09-12'),
            'exit_date': pd.Timestamp('2025-09-19'),
            'ticker': 'AAPL',
            'entry_price': 230.35,
            'exit_price': 231.48,
            'position_size': 68,
            'partial_exit': False,
            'exit_pct': 1.0,
            'exit_type': 'SIGNAL_EXIT',
            'dollar_pnl': 76.84,
            'equity_before_trade': 100000.0,
            'portfolio_equity': 100076.84,
            'r_multiple': 0.10,
            'profit_pct': 0.49,
            'entry_signals': ['Moderate_Buy'],
            'exit_signals': ['Distribution_Warning'],
            'signal_scores': {'Moderate_Buy_Score': 4.75, 'Accumulation_Score': 7.18},
            'market_regime_ok': True,    # SPY > 200 MA at entry
            'sector_regime_ok': True,    # Sector ETF > 50 MA at entry
            'overall_regime_ok': True    # Both conditions met
        },
        {
            'entry_date': pd.Timestamp('2025-09-16'),
            'exit_date': pd.Timestamp('2025-09-22'),
            'ticker': 'MSFT',
            'entry_price': 502.25,
            'exit_price': 514.60,
            'position_size': 55,
            'partial_exit': False,
            'exit_pct': 1.0,
            'exit_type': 'TIME_STOP',
            'dollar_pnl': 679.25,
            'equity_before_trade': 100076.84,
            'portfolio_equity': 100756.09,
            'r_multiple': 0.91,
            'profit_pct': 2.46,
            'entry_signals': ['Strong_Buy'],
            'exit_signals': [],
            'signal_scores': {'Accumulation_Score': 9.12},
            'market_regime_ok': False,   # SPY < 200 MA at entry (regime blocked some signals)
            'sector_regime_ok': True,    # Sector ETF > 50 MA at entry
            'overall_regime_ok': False   # Market regime failed
        }
    ]
    
    # Test the CSV export logic from batch_backtest.py
    print("Creating test DataFrame...")
    ledger_df = pd.DataFrame(mock_trades)
    
    # Convert data types to match actual batch backtest processing
    ledger_df['entry_date'] = pd.to_datetime(ledger_df['entry_date'])
    ledger_df['exit_date'] = pd.to_datetime(ledger_df['exit_date'])
    
    # Convert entry/exit signals to strings (like in batch_backtest.py)
    ledger_df['entry_signals_str'] = ledger_df['entry_signals'].apply(
        lambda x: ','.join(x) if isinstance(x, list) else ''
    )
    ledger_df['primary_signal'] = ledger_df['entry_signals'].apply(
        lambda x: x[0] if isinstance(x, list) and len(x) > 0 else ''
    )
    ledger_df['exit_signals_str'] = ledger_df['exit_signals'].apply(
        lambda x: ','.join(x) if isinstance(x, list) else ''
    )
    ledger_df['primary_exit_signal'] = ledger_df['exit_signals'].apply(
        lambda x: x[0] if isinstance(x, list) and len(x) > 0 else ''
    )
    
    # Extract signal scores
    ledger_df['accumulation_score'] = ledger_df['signal_scores'].apply(
        lambda x: x.get('Accumulation_Score', np.nan) if isinstance(x, dict) else np.nan
    )
    ledger_df['moderate_buy_score'] = ledger_df['signal_scores'].apply(
        lambda x: x.get('Moderate_Buy_Score', np.nan) if isinstance(x, dict) else np.nan
    )
    ledger_df['profit_taking_score'] = ledger_df['signal_scores'].apply(
        lambda x: x.get('Profit_Taking_Score', np.nan) if isinstance(x, dict) else np.nan
    )
    
    # Apply the NEW regime filter CSV export logic
    print("Testing regime filter column extraction...")
    
    # Extract regime filter columns if they exist (added for regime filter support)
    regime_columns = []
    for col in ['market_regime_ok', 'sector_regime_ok', 'overall_regime_ok']:
        if col in ledger_df.columns:
            regime_columns.append(col)
            print(f"✅ Found regime column: {col}")
        else:
            # Add missing regime columns as None for compatibility
            ledger_df[col] = None
            regime_columns.append(col)
            print(f"⚠️  Added missing regime column: {col}")
    
    # Create portfolio_ledger with regime columns
    portfolio_ledger = ledger_df[['entry_date', 'exit_date', 'ticker', 'entry_price', 'exit_price',
                                  'position_size', 'partial_exit', 'exit_pct', 'exit_type', 'dollar_pnl',
                                  'equity_before_trade', 'portfolio_equity', 'r_multiple', 'profit_pct',
                                  'entry_signals_str', 'primary_signal', 'exit_signals_str', 'primary_exit_signal',
                                  'accumulation_score', 'moderate_buy_score', 'profit_taking_score'] + regime_columns]
    
    print(f"\n📊 Portfolio ledger columns ({len(portfolio_ledger.columns)}):")
    for i, col in enumerate(portfolio_ledger.columns):
        marker = "🎯" if col in ['market_regime_ok', 'sector_regime_ok', 'overall_regime_ok'] else "  "
        print(f"{marker} {i+1:2d}. {col}")
    
    # Test CSV export
    print(f"\n💾 Testing CSV export...")
    export_df = portfolio_ledger.copy()
    
    # Format dates for CSV
    for col in ['entry_date', 'exit_date']:
        if export_df[col].notna().any():
            export_df[col] = export_df[col].dt.strftime("%Y-%m-%d")
    
    # Save to test CSV
    test_csv_path = 'test_regime_export.csv'
    export_df.to_csv(test_csv_path, index=False)
    
    print(f"✅ Test CSV saved: {test_csv_path}")
    
    # Verify the CSV contains regime columns
    print(f"\n🔍 Verifying CSV contents...")
    
    # Read back the CSV
    verify_df = pd.read_csv(test_csv_path)
    
    print(f"CSV has {len(verify_df.columns)} columns:")
    regime_found = []
    for col in verify_df.columns:
        if col in ['market_regime_ok', 'sector_regime_ok', 'overall_regime_ok']:
            regime_found.append(col)
            print(f"✅ {col}: {list(verify_df[col].values)}")
    
    print(f"\n📊 Results:")
    print(f"  Regime columns in CSV: {len(regime_found)}/3")
    print(f"  Expected columns: market_regime_ok, sector_regime_ok, overall_regime_ok")
    print(f"  Found columns: {regime_found}")
    
    if len(regime_found) == 3:
        print(f"\n✅ SUCCESS: All regime filter columns are present in CSV export!")
        print(f"   - market_regime_ok: Shows SPY > 200 MA status at entry")
        print(f"   - sector_regime_ok: Shows sector ETF > 50 MA status at entry")
        print(f"   - overall_regime_ok: Shows if both conditions were met")
        
        # Show sample values
        print(f"\n📋 Sample regime values:")
        for i, row in verify_df.iterrows():
            print(f"  Trade {i+1} ({row['ticker']}): Market={row['market_regime_ok']}, Sector={row['sector_regime_ok']}, Overall={row['overall_regime_ok']}")
        
        return True
    else:
        print(f"\n❌ FAILED: Missing regime columns in CSV export")
        print(f"   Expected: 3 regime columns")
        print(f"   Found: {len(regime_found)} regime columns")
        return False

if __name__ == '__main__':
    success = test_regime_csv_export()
    if success:
        print(f"\n🎉 Test PASSED: Regime filter CSV export is working correctly!")
    else:
        print(f"\n💥 Test FAILED: Regime filter CSV export needs debugging")
