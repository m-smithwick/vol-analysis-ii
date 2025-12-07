#!/usr/bin/env python3
"""
Debug script to verify MA_Crossdown signal is being generated properly.
"""

import pandas as pd
from analysis_service import prepare_analysis_dataframe
from config_loader import load_config

def test_ma_crossdown_signal(ticker='AAPL', period='6mo'):
    """Test if MA_Crossdown signal is generated and has True values."""
    
    print(f"\n{'='*70}")
    print(f"🔍 MA_CROSSDOWN SIGNAL DEBUG TEST")
    print(f"Ticker: {ticker} | Period: {period}")
    print(f"{'='*70}\n")
    
    # Load conservative config
    config_loader = load_config('configs/conservative_config.yaml')
    config = config_loader.config  # Get the actual config dict
    
    # Check config settings
    print("📋 Configuration Check:")
    exit_params = config.get('exit_signal_params', {})
    ma_config = exit_params.get('ma_crossdown', {})
    print(f"  exit_signal_params exists: {bool(exit_params)}")
    print(f"  ma_crossdown section exists: {bool(ma_config)}")
    print(f"  enabled: {ma_config.get('enabled', False)}")
    print(f"  ma_period: {ma_config.get('ma_period', 'N/A')}")
    print(f"  confirmation_days: {ma_config.get('confirmation_days', 'N/A')}")
    print(f"  buffer_pct: {ma_config.get('buffer_pct', 'N/A')}")
    print()
    
    # Get DataFrame with signals
    print("📊 Generating analysis DataFrame...")
    df = prepare_analysis_dataframe(
        ticker=ticker,
        period=period,
        config=config,
        cache_only=True,
        verbose=True
    )
    
    # Check if MA_Crossdown column exists
    print(f"\n🔍 Signal Column Check:")
    print(f"  MA_Crossdown column exists: {'MA_Crossdown' in df.columns}")
    
    if 'MA_Crossdown' in df.columns:
        # Count True values
        ma_crossdown_count = df['MA_Crossdown'].sum()
        print(f"  MA_Crossdown signals found: {ma_crossdown_count}")
        
        # Show dates where signal is True
        if ma_crossdown_count > 0:
            print(f"\n📅 MA_Crossdown Signal Dates:")
            signal_dates = df[df['MA_Crossdown']].index
            for date in signal_dates:
                close = df.loc[date, 'Close']
                ma_50 = df['Close'].rolling(48).mean().loc[date]
                print(f"    {date.strftime('%Y-%m-%d')}: Close=${close:.2f}, MA(48)=${ma_50:.2f}")
        else:
            print(f"\n  ⚠️ No MA_Crossdown signals found!")
            
            # Check if 48-day MA exists
            df['MA_48'] = df['Close'].rolling(48).mean()
            df['Below_MA'] = df['Close'] < df['MA_48']
            
            below_ma_count = df['Below_MA'].sum()
            print(f"\n  Days where Close < MA(48): {below_ma_count}")
            
            if below_ma_count > 0:
                print(f"  Sample dates below MA(48):")
                sample = df[df['Below_MA']].tail(5)
                for date, row in sample.iterrows():
                    print(f"    {date.strftime('%Y-%m-%d')}: Close=${row['Close']:.2f}, MA(48)=${row['MA_48']:.2f}")
    else:
        print(f"  ❌ MA_Crossdown column NOT FOUND in DataFrame!")
        print(f"\n  Available exit signal columns:")
        exit_cols = [col for col in df.columns if any(x in col for x in 
                     ['Profit', 'Distribution', 'Sell', 'Momentum', 'Stop', 'MA'])]
        for col in sorted(exit_cols):
            print(f"    - {col}")
    
    # Check other exit signals for comparison
    print(f"\n📊 Other Exit Signals (for comparison):")
    exit_signals = ['Profit_Taking', 'Distribution_Warning', 'Sell_Signal',
                    'Momentum_Exhaustion', 'Stop_Loss']
    
    for sig in exit_signals:
        if sig in df.columns:
            count = df[sig].sum()
            print(f"  {sig}: {count} signals")
        else:
            print(f"  {sig}: MISSING")
    
    print(f"\n{'='*70}\n")
    
    return df


if __name__ == '__main__':
    # Test with AAPL 6mo (known to have 4 crossdowns)
    df = test_ma_crossdown_signal('AAPL', '6mo')
    
    # Also test with a ticker from the batch backtest
    print("\n" + "="*70)
    print("Testing with NASDAQ-100 ticker...")
    print("="*70 + "\n")
    df2 = test_ma_crossdown_signal('MSFT', '3y')
