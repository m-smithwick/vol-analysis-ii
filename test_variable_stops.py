"""
Variable Stop Loss Testing Framework

This script tests different variable stop loss strategies against the baseline
static stop approach. Creates a standalone testing environment that extends
RiskManager without modifying production code.

Test Strategies:
1. Baseline: Current static stop (min(swing_low - 0.5*ATR, VWAP - 1.0*ATR))
2. ATR Dynamic: Stop adjusts based on current ATR
3. Percentage Trail: Fixed % trail below peak price
4. Volatility Regime: ATR_Z-based adaptive stops
5. Time Decay: Gradually tightening stops over time

Usage:
    python test_variable_stops.py --tickers FIX MSFT VRT --period 24mo
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import argparse
import os

from risk_manager import RiskManager
from backtest import pair_entry_exit_signals, analyze_strategy_performance
from data_manager import get_smart_data, read_ticker_file
from indicators import calculate_zscore
import vol_analysis
import volume_features
import signal_generator
import swing_structure
import indicators




def run_strategy_backtest(
    ticker: str,
    df: pd.DataFrame,
    strategy: str,
    account_value: float = 100000,
    risk_pct: float = 0.75
) -> Tuple[List[Dict], RiskManager]:
    """
    Run backtest with specific variable stop strategy.
    
    Args:
        ticker: Stock symbol
        df: DataFrame with signals and indicators
        strategy: Stop loss strategy name
        account_value: Starting account value
        risk_pct: Risk per trade percentage
        
    Returns:
        Tuple of (trades list, risk manager instance)
    """
    # Initialize production risk manager (now supports all variable stops)
    risk_mgr = RiskManager(
        account_value=account_value,
        risk_pct_per_trade=risk_pct,
        stop_strategy=strategy
    )
    
    # Entry and exit signals
    entry_signals = ['Strong_Buy', 'Moderate_Buy', 'Stealth_Accumulation', 
                     'Confluence_Signal', 'Volume_Breakout']
    exit_signals = ['Profit_Taking', 'Distribution_Warning', 'Sell_Signal',
                    'Momentum_Exhaustion', 'Stop_Loss']
    
    # Run backtest
    all_trades = []
    
    for idx in range(len(df)):
        current_date = df.index[idx]
        current_price = df.iloc[idx]['Close']
        
        # Update active positions
        if ticker in risk_mgr.active_positions:
            exit_check = risk_mgr.update_position(
                ticker=ticker,
                current_date=current_date,
                current_price=current_price,
                df=df,
                current_idx=idx
            )
            
            # Check for exit signals
            has_exit_signal = any(df.iloc[idx][sig] for sig in exit_signals)
            triggered_exits = [sig for sig in exit_signals if df.iloc[idx][sig]]
            
            should_exit = exit_check['should_exit'] or has_exit_signal
            
            if should_exit:
                # Determine exit type
                if exit_check['should_exit']:
                    exit_type = exit_check['exit_type']
                    exit_reason = exit_check['reason']
                else:
                    exit_type = 'SIGNAL_EXIT'
                    exit_reason = f"Exit signal: {', '.join(triggered_exits)}"
                
                # Close position
                exit_price = current_price if has_exit_signal else exit_check['exit_price']
                
                trade = risk_mgr.close_position(
                    ticker=ticker,
                    exit_price=exit_price,
                    exit_type=exit_type,
                    exit_date=current_date,
                    partial_exit_pct=exit_check.get('exit_pct', 1.0)
                )
                
                if trade:
                    trade['strategy'] = strategy
                    all_trades.append(trade)
        
        # Check for entry signals
        if ticker not in risk_mgr.active_positions:
            has_entry_signal = any(df.iloc[idx][sig] for sig in entry_signals)
            
            if has_entry_signal and idx + 1 < len(df):
                entry_price = df.iloc[idx + 1]['Open']
                entry_date = df.index[idx + 1]
                
                try:
                    stop_price = risk_mgr.calculate_initial_stop(df, idx)
                    
                    position = risk_mgr.open_position(
                        ticker=ticker,
                        entry_date=entry_date,
                        entry_price=entry_price,
                        stop_price=stop_price,
                        entry_idx=idx + 1,
                        df=df
                    )
                    
                except (KeyError, ValueError):
                    continue
    
    # Close any remaining positions
    if ticker in risk_mgr.active_positions:
        last_price = df.iloc[-1]['Close']
        last_date = df.index[-1]
        
        trade = risk_mgr.close_position(
            ticker=ticker,
            exit_price=last_price,
            exit_type='END_OF_DATA',
            exit_date=last_date
        )
        
        if trade:
            trade['strategy'] = strategy
            all_trades.append(trade)
    
    return all_trades, risk_mgr


def calculate_all_indicators(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """
    Calculate indicators directly on provided DataFrame WITHOUT re-downloading data.
    
    CRITICAL: This function now calculates indicators in-place to avoid cache corruption.
    Previous version called analyze_ticker() which re-downloaded data and corrupted caches.
    
    Bug Fixed: November 16, 2025
    - Removed analyze_ticker() call (was hardcoded to period='1y', data_source='yfinance')
    - Now calculates indicators directly on provided df
    - Preserves cache integrity
    """
    # Calculate CMF (Chaikin Money Flow)
    df['CMF_20'] = volume_features.calculate_cmf(df, period=20)
    df['CMF_Z'] = volume_features.calculate_cmf_zscore(df, cmf_period=20, zscore_window=20)
    
    # Price-Volume Correlation
    df['PriceVolumeCorr'] = indicators.calculate_price_volume_correlation(df, window=20)
    
    # Price trend analysis
    df['Price_MA'] = df['Close'].rolling(window=10).mean()
    df['Price_Trend'] = df['Close'] > df['Price_MA']
    df['Price_Rising'] = df['Close'] > df['Close'].shift(5)
    
    # CMF-based signals
    df['CMF_Positive'] = df['CMF_Z'] > 0
    df['CMF_Strong'] = df['CMF_Z'] > 1.0
    
    # OBV and A/D Line (for signal compatibility)
    price_delta = df['Close'].diff().fillna(0)
    obv_direction = np.sign(price_delta).fillna(0)
    df['OBV'] = (obv_direction * df['Volume']).fillna(0).cumsum()
    df['OBV_MA'] = df['OBV'].rolling(window=10).mean()
    df['OBV_Trend'] = (df['OBV'] > df['OBV_MA']).fillna(False)
    
    high_low_range = (df['High'] - df['Low']).replace(0, np.nan)
    money_flow_multiplier = ((df['Close'] - df['Low']) - (df['High'] - df['Close'])) / high_low_range
    money_flow_multiplier = money_flow_multiplier.replace([np.inf, -np.inf], 0).fillna(0)
    money_flow_volume = money_flow_multiplier * df['Volume']
    df['AD_Line'] = money_flow_volume.cumsum()
    df['AD_MA'] = df['AD_Line'].rolling(window=10).mean()
    df['AD_Rising'] = df['AD_Line'].diff().fillna(0) > 0
    
    # Volume analysis
    df['Volume_MA'] = df['Volume'].rolling(window=20).mean()
    df['Volume_Spike'] = df['Volume'] > (df['Volume_MA'] * 1.5)
    df['Relative_Volume'] = volume_features.calculate_volume_surprise(df, window=20)
    
    # VWAP
    df['VWAP'] = indicators.calculate_anchored_vwap(df)
    df['Above_VWAP'] = df['Close'] > df['VWAP']
    
    # Swing structure
    df['Recent_Swing_Low'], df['Recent_Swing_High'] = swing_structure.calculate_swing_levels(df, lookback=3)
    df['Near_Support'], df['Lost_Support'], df['Near_Resistance'] = swing_structure.calculate_swing_proximity_signals(
        df, df['Recent_Swing_Low'], df['Recent_Swing_High'], atr_series=None, use_volatility_aware=False
    )
    df['Support_Level'] = df['Recent_Swing_Low']
    
    # ATR and event detection
    df['TR'], df['ATR20'] = indicators.calculate_atr(df, period=20)
    df['Event_Day'] = volume_features.detect_event_days(df, atr_multiplier=2.5, volume_threshold=2.0)
    
    # Z-score standardization
    df = indicators.standardize_features(df, window=20)
    
    # Phase detection
    df['Phase'] = pd.Series('Neutral', index=df.index)
    
    # Accumulation scores
    df['Accumulation_Score'] = signal_generator.calculate_accumulation_score(df)
    df['Exit_Score'] = signal_generator.calculate_exit_score(df)
    
    # Entry signals
    df['Strong_Buy'] = signal_generator.generate_strong_buy_signals(df)
    df['Moderate_Buy'] = signal_generator.generate_moderate_buy_signals(df)
    df['Stealth_Accumulation'] = signal_generator.generate_stealth_accumulation_signals(df)
    df['Confluence_Signal'] = signal_generator.generate_confluence_signals(df)
    df['Volume_Breakout'] = signal_generator.generate_volume_breakout_signals(df)
    
    # Exit signals
    df['Profit_Taking'] = signal_generator.generate_profit_taking_signals(df)
    df['Distribution_Warning'] = signal_generator.generate_distribution_warning_signals(df)
    df['Sell_Signal'] = signal_generator.generate_sell_signals(df)
    df['Momentum_Exhaustion'] = signal_generator.generate_momentum_exhaustion_signals(df)
    df['Stop_Loss'] = signal_generator.generate_stop_loss_signals(df)
    
    return df


def compare_stop_strategies(
    tickers: List[str],
    period: str = '1y',
    strategies: List[str] = None
) -> pd.DataFrame:
    """
    Compare all stop loss strategies across multiple tickers.
    
    Args:
        tickers: List of ticker symbols to test
        period: Data period ('1y', '2y', etc.)
        strategies: List of strategies to test (None = all)
        
    Returns:
        DataFrame with comparison results
    """
    if strategies is None:
        strategies = ['static', 'atr_dynamic', 'pct_trail', 'vol_regime', 'time_decay']
    
    all_results = []
    
    for ticker in tickers:
        print(f"\n{'='*70}")
        print(f"Testing {ticker}")
        print(f"{'='*70}")
        
        # Load and prepare data
        try:
            df = get_smart_data(ticker, period=period, interval='1d', force_refresh=False)
            
            if df is None or len(df) < 50:
                print(f"⚠️  Insufficient data for {ticker}")
                continue
            
            # Calculate indicators (simplified version from vol_analysis.py)
            df = calculate_all_indicators(df, ticker)
            
            # Ensure ATR_Z exists
            if 'ATR_Z' not in df.columns and 'ATR20' in df.columns:
                df['ATR_Z'] = calculate_zscore(df['ATR20'], window=20)
            
            print(f"   Data loaded: {len(df)} bars")
            
        except Exception as e:
            print(f"❌ Error loading {ticker}: {e}")
            continue
        
        # Test each strategy
        for strategy in strategies:
            print(f"\n   Testing {strategy}...")
            
            try:
                trades, risk_mgr = run_strategy_backtest(
                    ticker=ticker,
                    df=df,
                    strategy=strategy
                )
                
                if not trades:
                    print(f"      No trades generated")
                    continue
                
                # Calculate metrics
                closed_trades = [t for t in trades if not t.get('is_open', False)]
                
                if not closed_trades:
                    print(f"      No closed trades")
                    continue
                
                returns = [t['r_multiple'] for t in closed_trades]
                wins = [r for r in returns if r > 0]
                losses = [r for r in returns if r <= 0]
                
                result = {
                    'Ticker': ticker,
                    'Strategy': strategy,
                    'Trades': len(closed_trades),
                    'Win_Rate': (len(wins) / len(returns)) * 100 if returns else 0,
                    'Avg_R': np.mean(returns) if returns else 0,
                    'Avg_Win_R': np.mean(wins) if wins else 0,
                    'Avg_Loss_R': np.mean(losses) if losses else 0,
                    'Best_R': max(returns) if returns else 0,
                    'Worst_R': min(returns) if returns else 0,
                    'Profit_Factor': abs(sum(wins) / sum(losses)) if losses and sum(losses) != 0 else float('inf'),
                    'Avg_Bars': np.mean([t['bars_held'] for t in closed_trades])
                }
                
                all_results.append(result)
                
                print(f"      Trades: {result['Trades']}, Win Rate: {result['Win_Rate']:.1f}%, Avg R: {result['Avg_R']:.2f}")
                
            except Exception as e:
                print(f"      ❌ Error: {e}")
                continue
    
    # Create results DataFrame
    results_df = pd.DataFrame(all_results)
    
    return results_df


def generate_comparison_report(results_df: pd.DataFrame, output_file: str = None) -> str:
    """
    Generate formatted comparison report.
    
    Args:
        results_df: DataFrame with strategy comparison results
        output_file: Optional file path to save report
        
    Returns:
        Formatted report string
    """
    report_lines = []
    
    report_lines.append("=" * 80)
    report_lines.append("VARIABLE STOP LOSS STRATEGY COMPARISON")
    report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("=" * 80)
    report_lines.append("")
    
    if results_df.empty:
        report_lines.append("⚠️  No results to display")
        return "\n".join(report_lines)
    
    # Overall summary by strategy
    report_lines.append("📊 STRATEGY PERFORMANCE SUMMARY")
    report_lines.append("-" * 80)
    report_lines.append("")
    
    strategy_summary = results_df.groupby('Strategy').agg({
        'Trades': 'sum',
        'Win_Rate': 'mean',
        'Avg_R': 'mean',
        'Profit_Factor': 'mean',
        'Avg_Bars': 'mean'
    }).round(2)
    
    strategy_summary = strategy_summary.sort_values('Avg_R', ascending=False)
    
    for strategy, row in strategy_summary.iterrows():
        report_lines.append(f"Strategy: {strategy.upper()}")
        report_lines.append(f"  Total Trades: {int(row['Trades'])}")
        report_lines.append(f"  Avg Win Rate: {row['Win_Rate']:.1f}%")
        report_lines.append(f"  Avg R-Multiple: {row['Avg_R']:.2f}R")
        report_lines.append(f"  Avg Profit Factor: {row['Profit_Factor']:.2f}")
        report_lines.append(f"  Avg Holding Period: {row['Avg_Bars']:.1f} bars")
        report_lines.append("")
    
    # Detailed results by ticker
    report_lines.append("📈 DETAILED RESULTS BY TICKER")
    report_lines.append("-" * 80)
    report_lines.append("")
    
    for ticker in results_df['Ticker'].unique():
        ticker_data = results_df[results_df['Ticker'] == ticker]
        
        report_lines.append(f"Ticker: {ticker}")
        report_lines.append("-" * 40)
        
        for _, row in ticker_data.iterrows():
            report_lines.append(f"  {row['Strategy']:15s} | "
                              f"Trades: {int(row['Trades']):3d} | "
                              f"Win: {row['Win_Rate']:5.1f}% | "
                              f"Avg R: {row['Avg_R']:+6.2f} | "
                              f"PF: {row['Profit_Factor']:5.2f}")
        
        report_lines.append("")
    
    # Best strategy recommendation
    report_lines.append("💡 RECOMMENDATIONS")
    report_lines.append("-" * 80)
    report_lines.append("")
    
    best_by_r = strategy_summary.idxmax()['Avg_R']
    best_by_wr = strategy_summary.idxmax()['Win_Rate']
    best_by_pf = strategy_summary.idxmax()['Profit_Factor']
    
    report_lines.append(f"🏆 Best Average R-Multiple: {best_by_r.upper()}")
    report_lines.append(f"   ({strategy_summary.loc[best_by_r, 'Avg_R']:.2f}R average)")
    report_lines.append("")
    
    report_lines.append(f"🎯 Best Win Rate: {best_by_wr.upper()}")
    report_lines.append(f"   ({strategy_summary.loc[best_by_wr, 'Win_Rate']:.1f}% win rate)")
    report_lines.append("")
    
    report_lines.append(f"💰 Best Profit Factor: {best_by_pf.upper()}")
    report_lines.append(f"   ({strategy_summary.loc[best_by_pf, 'Profit_Factor']:.2f} profit factor)")
    report_lines.append("")
    
    # Statistical significance note
    total_trades = results_df['Trades'].sum()
    report_lines.append(f"📝 NOTES")
    report_lines.append(f"  • Total Trades Analyzed: {int(total_trades)}")
    
    if total_trades < 100:
        report_lines.append(f"  ⚠️  Sample size limited - results may not be statistically significant")
        report_lines.append(f"     Consider testing with more tickers or longer period")
    
    report_lines.append("")
    report_lines.append("=" * 80)
    
    report = "\n".join(report_lines)
    
    # Save to file if requested
    if output_file:
        os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else '.', exist_ok=True)
        with open(output_file, 'w') as f:
            f.write(report)
        print(f"\n💾 Report saved: {output_file}")
    
    return report


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description='Test variable stop loss strategies')
    parser.add_argument('--tickers', nargs='+', default=['AAPL', 'MSFT', 'NVDA', 'TSLA', 'AMD'],
                       help='Ticker symbols to test')
    parser.add_argument('--file', '-f', 
                       help='Path to file containing ticker symbols (one per line). Overrides --tickers if provided.')
    parser.add_argument('-p', '--period', default='12mo',
                       help='Data period (e.g., 6mo, 12mo, 24mo). Legacy 1y/2y values are converted to months.')
    parser.add_argument('--strategies', nargs='+', 
                       default=['static', 'atr_dynamic', 'pct_trail', 'vol_regime', 'time_decay'],
                       help='Strategies to test')
    parser.add_argument('--output', default='backtest_results/variable_stop_comparison.txt',
                       help='Output file path')
    
    args = parser.parse_args()
    
    # Determine tickers to use
    if args.file:
        try:
            tickers = read_ticker_file(args.file)
            print(f"📁 Read {len(tickers)} tickers from {args.file}")
        except Exception as e:
            print(f"❌ Error reading ticker file {args.file}: {e}")
            return
    else:
        tickers = args.tickers
    
    period = args.period.lower()
    legacy_map = {'1y': '12mo', '2y': '24mo', '3y': '36mo'}
    period = legacy_map.get(period, period)
    
    if not period.endswith('mo') and period not in {'1d','5d','ytd','max'}:
        try:
            if period.endswith('y'):
                years = int(period[:-1])
                period = f"{years * 12}mo"
        except ValueError:
            pass
    
    print("=" * 80)
    print("VARIABLE STOP LOSS TESTING FRAMEWORK")
    print("=" * 80)
    print(f"\nTickers: {', '.join(tickers)}")
    print(f"Period: {period}")
    print(f"Strategies: {', '.join(args.strategies)}")
    print("")
    
    results_df = compare_stop_strategies(
        tickers=tickers,
        period=period,
        strategies=args.strategies
    )
    
    # Generate report
    if not results_df.empty:
        report = generate_comparison_report(results_df, args.output)
        print("\n" + report)
        
        # Save CSV data
        csv_file = args.output.replace('.txt', '_data.csv')
        results_df.to_csv(csv_file, index=False)
        print(f"💾 Data saved: {csv_file}")
    else:
        print("\n⚠️  No results generated")


if __name__ == "__main__":
    main()
