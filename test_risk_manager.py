"""
Test suite for RiskManager class

Validates all risk management functionality:
- Position sizing
- Stop placement
- Exit conditions (time, momentum, profit, trailing)
- Trade tracking and analysis
"""

import pandas as pd
import numpy as np
from risk_manager import RiskManager, analyze_risk_managed_trades


def create_sample_data():
    """Create sample price data with indicators for testing."""
    dates = pd.date_range('2024-01-01', periods=50, freq='D')
    
    # Create realistic price data
    np.random.seed(42)
    close = 100 + np.cumsum(np.random.randn(50) * 2)
    high = close + np.random.rand(50) * 2
    low = close - np.random.rand(50) * 2
    volume = np.random.randint(1_000_000, 10_000_000, 50)
    
    df = pd.DataFrame({
        'Close': close,
        'Open': close * 0.99,  # Simulate slight gap
        'High': high,
        'Low': low,
        'Volume': volume
    }, index=dates)
    
    # Add required indicators
    df['ATR20'] = 2.0  # Simplified ATR
    df['Recent_Swing_Low'] = df['Low'].rolling(10).min()
    df['Anchored_VWAP'] = df['Close'].expanding().mean()
    df['CMF_Z'] = np.random.randn(50)  # Random z-scores
    
    return df


def test_position_sizing():
    """Test risk-based position sizing calculation."""
    print("\n=== Testing Position Sizing ===")
    
    rm = RiskManager(account_value=100_000, risk_pct_per_trade=1.0)
    
    entry_price = 100.0
    stop_price = 95.0  # $5 risk per share
    
    position_size = rm.calculate_position_size(entry_price, stop_price)
    
    # With 1% risk on $100k account = $1000 risk
    # Risk per share = $5
    # Expected position = $1000 / $5 = 200 shares
    
    print(f"Account Value: ${rm.account_value:,.0f}")
    print(f"Risk Per Trade: {rm.risk_pct}%")
    print(f"Entry Price: ${entry_price:.2f}")
    print(f"Stop Price: ${stop_price:.2f}")
    print(f"Risk Per Share: ${entry_price - stop_price:.2f}")
    print(f"Position Size: {position_size} shares")
    print(f"Total Risk: ${position_size * (entry_price - stop_price):,.2f}")
    
    assert position_size == 200, f"Expected 200 shares, got {position_size}"
    print("✓ Position sizing test passed")


def test_stop_calculation():
    """Test initial stop placement logic."""
    print("\n=== Testing Stop Calculation ===")
    
    df = create_sample_data()
    rm = RiskManager(account_value=100_000)
    
    entry_idx = df.index[20]  # Use DatetimeIndex
    stop_price = rm.calculate_initial_stop(df, entry_idx)
    
    swing_stop = df.loc[entry_idx, 'Recent_Swing_Low'] - (0.5 * df.loc[entry_idx, 'ATR20'])
    vwap_stop = df.loc[entry_idx, 'Anchored_VWAP'] - (1.0 * df.loc[entry_idx, 'ATR20'])
    
    print(f"Entry Index: {entry_idx.date()}")
    print(f"Swing Low: ${df.loc[entry_idx, 'Recent_Swing_Low']:.2f}")
    print(f"ATR20: ${df.loc[entry_idx, 'ATR20']:.2f}")
    print(f"Anchored VWAP: ${df.loc[entry_idx, 'Anchored_VWAP']:.2f}")
    print(f"\nSwing-based stop: ${swing_stop:.2f}")
    print(f"VWAP-based stop: ${vwap_stop:.2f}")
    print(f"Final stop (min): ${stop_price:.2f}")
    
    assert stop_price == min(swing_stop, vwap_stop), "Stop should be minimum of swing/VWAP stops"
    print("✓ Stop calculation test passed")


def test_time_stop():
    """Test time-based exit after 12 bars if <+1R."""
    print("\n=== Testing Time Stop ===")
    
    df = create_sample_data()
    rm = RiskManager(account_value=100_000)
    
    # Open position
    entry_iloc = 10
    entry_idx = df.index[entry_iloc]
    entry_date = entry_idx
    entry_price = df.loc[entry_idx, 'Close']
    stop_price = entry_price * 0.95  # 5% stop
    
    position = rm.open_position(
        ticker='TEST',
        entry_date=entry_date,
        entry_price=entry_price,
        stop_price=stop_price,
        entry_idx=entry_iloc,  # Use integer position for bars_in_trade calculation
        df=df
    )
    
    print(f"Opened position at ${entry_price:.2f}, stop at ${stop_price:.2f}")
    
    # Simulate price going sideways (small gain <1R)
    test_iloc = entry_iloc + 13  # 13 bars later
    test_idx = df.index[test_iloc]
    test_price = entry_price + (entry_price - stop_price) * 0.5  # +0.5R
    
    exit_check = rm.update_position(
        ticker='TEST',
        current_date=test_idx,
        current_price=test_price,
        df=df,
        current_idx=test_iloc  # Use integer position
    )
    
    print(f"\nAfter {exit_check['r_multiple']:.2f}R gain and 13 bars:")
    print(f"Should Exit: {exit_check['should_exit']}")
    print(f"Exit Type: {exit_check['exit_type']}")
    print(f"Reason: {exit_check['reason']}")
    
    assert exit_check['should_exit'] == True, "Should trigger time stop"
    assert exit_check['exit_type'] == 'TIME_STOP', "Should be TIME_STOP"
    print("✓ Time stop test passed")


def test_profit_scaling():
    """Test 50% exit at +2R and trailing stop."""
    print("\n=== Testing Profit Scaling ===")
    
    df = create_sample_data()
    rm = RiskManager(account_value=100_000)
    
    # Ensure CMF_Z is positive for this test (avoid momentum failure)
    df['CMF_Z'] = np.abs(df['CMF_Z'])
    
    # Open position
    entry_iloc = 10
    entry_idx = df.index[entry_iloc]
    entry_date = entry_idx
    entry_price = 100.0
    stop_price = 95.0  # $5 risk
    
    # Ensure Anchored_VWAP is below entry price (avoid momentum failure)
    df.loc[df.index[entry_iloc:], 'Anchored_VWAP'] = entry_price * 0.98
    
    position = rm.open_position(
        ticker='WINNER',
        entry_date=entry_date,
        entry_price=entry_price,
        stop_price=stop_price,
        entry_idx=entry_iloc,  # Use integer position
        df=df
    )
    
    print(f"Opened position at ${entry_price:.2f}, stop at ${stop_price:.2f}")
    print(f"Position size: {position['position_size']} shares")
    
    # Simulate +2R gain
    test_iloc = entry_iloc + 5
    test_idx = df.index[test_iloc]
    test_price = entry_price + (entry_price - stop_price) * 2.0  # +2R = $110
    
    exit_check = rm.update_position(
        ticker='WINNER',
        current_date=test_idx,
        current_price=test_price,
        df=df,
        current_idx=test_iloc  # Use integer position
    )
    
    print(f"\nAt +{exit_check['r_multiple']:.2f}R (${test_price:.2f}):")
    print(f"Should Exit: {exit_check['should_exit']}")
    print(f"Partial Exit: {exit_check['partial_exit']}")
    print(f"Exit %: {exit_check['exit_pct'] * 100:.0f}%")
    print(f"Exit Type: {exit_check['exit_type']}")
    
    assert exit_check['should_exit'] == True, "Should trigger profit target"
    assert exit_check['partial_exit'] == True, "Should be partial exit"
    assert exit_check['exit_pct'] == 0.5, "Should exit 50%"
    assert exit_check['exit_type'] == 'PROFIT_TARGET', "Should be PROFIT_TARGET"
    
    # Execute the partial exit
    partial_trade = rm.close_position(
        ticker='WINNER',
        exit_price=test_price,
        exit_type=exit_check['exit_type'],
        exit_date=test_idx,
        partial_exit_pct=0.5
    )
    
    print(f"\nPartial exit completed:")
    print(f"Exited {partial_trade['position_size']} shares at +{partial_trade['r_multiple']:.2f}R")
    print(f"Remaining position: {rm.active_positions['WINNER']['position_size']} shares")
    print(f"Trailing stop active: {rm.active_positions['WINNER']['trail_stop_active']}")
    print(f"Trail stop price: ${rm.active_positions['WINNER']['trail_stop_price']:.2f}")
    
    assert partial_trade['partial_exit'] == True, "Should be marked as partial"
    assert rm.active_positions['WINNER']['trail_stop_active'] == True, "Trailing stop should be active"
    print("✓ Profit scaling test passed")


def test_full_trade_workflow():
    """Test complete trade lifecycle with realistic scenario."""
    print("\n=== Testing Full Trade Workflow ===")
    
    df = create_sample_data()
    rm = RiskManager(account_value=100_000, risk_pct_per_trade=0.75)
    
    # Entry signal at bar 10
    entry_iloc = 10
    entry_idx = df.index[entry_iloc]
    entry_date = entry_idx
    entry_price = df.loc[entry_idx, 'Close']
    stop_price = rm.calculate_initial_stop(df, entry_idx)
    
    print(f"Entry: {entry_date.date()}, Price: ${entry_price:.2f}, Stop: ${stop_price:.2f}")
    
    position = rm.open_position(
        ticker='FULLTEST',
        entry_date=entry_date,
        entry_price=entry_price,
        stop_price=stop_price,
        entry_idx=entry_iloc,  # Use integer position
        df=df
    )
    
    print(f"Position size: {position['position_size']} shares")
    
    # Simulate price movement through remaining bars
    for idx in range(entry_iloc + 1, len(df)):
        current_idx = df.index[idx]
        current_price = df.loc[current_idx, 'Close']
        
        exit_check = rm.update_position(
            ticker='FULLTEST',
            current_date=current_idx,
            current_price=current_price,
            df=df,
            current_idx=idx  # Use integer position
        )
        
        if exit_check['should_exit']:
            print(f"\nExit triggered on {current_idx.date()}")
            print(f"Price: ${current_price:.2f}")
            print(f"R-Multiple: {exit_check['r_multiple']:.2f}R")
            print(f"Exit Type: {exit_check['exit_type']}")
            print(f"Reason: {exit_check['reason']}")
            
            trade = rm.close_position(
                ticker='FULLTEST',
                exit_price=current_price,
                exit_type=exit_check['exit_type'],
                exit_date=current_idx,
                partial_exit_pct=exit_check.get('exit_pct', 1.0)
            )
            
            if not exit_check.get('partial_exit', False):
                break
    
    # Analyze all trades
    all_trades = rm.get_all_trades()
    print(f"\nTotal trades executed: {len(all_trades)}")
    
    for i, trade in enumerate(all_trades):
        print(f"\nTrade {i+1}:")
        print(f"  Entry: {trade['entry_date'].date()} @ ${trade['entry_price']:.2f}")
        print(f"  Exit: {trade['exit_date'].date()} @ ${trade['exit_price']:.2f}")
        print(f"  R-Multiple: {trade['r_multiple']:.2f}R")
        print(f"  Profit: {trade['profit_pct']:.2f}%")
        print(f"  Exit Type: {trade['exit_type']}")
        print(f"  Bars Held: {trade['bars_held']}")
    
    print("✓ Full trade workflow test passed")


def test_analysis_function():
    """Test trade analysis functionality."""
    print("\n=== Testing Trade Analysis ===")
    
    # Create mock trades
    trades = [
        {'r_multiple': 2.5, 'profit_pct': 12.5, 'bars_held': 8, 'exit_type': 'PROFIT_TARGET', 
         'profit_taken_50pct': True, 'peak_r_multiple': 2.8},
        {'r_multiple': 1.5, 'profit_pct': 7.5, 'bars_held': 5, 'exit_type': 'TRAIL_STOP', 
         'profit_taken_50pct': True, 'peak_r_multiple': 2.1},
        {'r_multiple': -1.0, 'profit_pct': -5.0, 'bars_held': 3, 'exit_type': 'HARD_STOP', 
         'profit_taken_50pct': False, 'peak_r_multiple': 0.2},
        {'r_multiple': 0.3, 'profit_pct': 1.5, 'bars_held': 13, 'exit_type': 'TIME_STOP', 
         'profit_taken_50pct': False, 'peak_r_multiple': 0.8},
    ]
    
    analysis = analyze_risk_managed_trades(trades)
    
    print("\nTrade Analysis Results:")
    print(f"Total Trades: {analysis['Total Trades']}")
    print(f"Win Rate: {analysis['Win Rate']}")
    print(f"Average R-Multiple: {analysis['Average R-Multiple']}")
    print(f"Average Profit %: {analysis['Average Profit %']}")
    print(f"Average Bars Held: {analysis['Average Bars Held']}")
    print(f"Profit Scaling Used: {analysis['Profit Scaling Used']} times")
    
    print("\nExit Type Breakdown:")
    for exit_type, count in analysis['Exit Type Breakdown'].items():
        print(f"  {exit_type}: {count}")
    
    print("\nR-Multiple Distribution:")
    for range_name, count in analysis['R-Multiple Distribution'].items():
        print(f"  {range_name}: {count}")
    
    print(f"\nBest Trade: {analysis['Best Trade']}")
    print(f"Worst Trade: {analysis['Worst Trade']}")
    print(f"Peak R-Multiple Avg: {analysis['Peak R-Multiple Avg']}")
    
    assert analysis['Total Trades'] == 4, "Should have 4 trades"
    assert analysis['Profit Scaling Used'] == 2, "Should have 2 trades with profit scaling"
    print("✓ Analysis function test passed")


if __name__ == '__main__':
    print("=" * 60)
    print("RISK MANAGER TEST SUITE")
    print("=" * 60)
    
    try:
        test_position_sizing()
        test_stop_calculation()
        test_time_stop()
        test_profit_scaling()
        test_full_trade_workflow()
        test_analysis_function()
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
