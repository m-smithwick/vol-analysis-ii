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


class VariableStopRiskManager(RiskManager):
    """
    Extended RiskManager that implements variable stop loss strategies.
    
    This class inherits from RiskManager and adds variable stop calculation
    methods without modifying the base class. Each strategy can be tested
    independently.
    """
    
    def __init__(self, account_value: float, risk_pct_per_trade: float = 0.75, 
                 stop_strategy: str = 'static'):
        """
        Initialize with specific stop loss strategy.
        
        Args:
            account_value: Total account equity
            risk_pct_per_trade: Risk percentage per trade
            stop_strategy: 'static', 'atr_dynamic', 'pct_trail', 'vol_regime', 'time_decay'
        """
        super().__init__(account_value, risk_pct_per_trade)
        self.stop_strategy = stop_strategy
        
        # Strategy-specific parameters (fixed for testing)
        self.params = {
            'atr_dynamic': {
                'multiplier': 2.0,
                'min_multiplier': 1.5,
                'max_multiplier': 3.0
            },
            'pct_trail': {
                'trail_pct': 8.0,  # 8% trail
                'activation_r': 1.0  # Activate after +1R
            },
            'vol_regime': {
                'low_vol_threshold': -0.5,
                'high_vol_threshold': 0.5,
                'low_vol_mult': 1.5,
                'normal_vol_mult': 2.0,
                'high_vol_mult': 2.5
            },
            'time_decay': {
                'initial_mult': 2.5,
                'day_5_mult': 2.5,
                'day_10_mult': 2.0,
                'day_15_mult': 1.5
            }
        }
    
    def calculate_variable_stop(
        self, 
        ticker: str, 
        df: pd.DataFrame, 
        current_idx: int
    ) -> float:
        """
        Calculate variable stop based on selected strategy.
        
        Args:
            ticker: Stock symbol
            df: DataFrame with price and indicator data
            current_idx: Current bar index
            
        Returns:
            Updated stop price
        """
        if ticker not in self.active_positions:
            return None
        
        pos = self.active_positions[ticker]
        current_price = df.iloc[current_idx]['Close']
        
        # Get strategy
        if self.stop_strategy == 'static':
            # Use original static stop
            return pos['stop_price']
        
        elif self.stop_strategy == 'atr_dynamic':
            return self._calculate_atr_dynamic_stop(pos, df, current_idx, current_price)
        
        elif self.stop_strategy == 'pct_trail':
            return self._calculate_pct_trail_stop(pos, df, current_idx, current_price)
        
        elif self.stop_strategy == 'vol_regime':
            return self._calculate_vol_regime_stop(pos, df, current_idx, current_price)
        
        elif self.stop_strategy == 'time_decay':
            return self._calculate_time_decay_stop(pos, df, current_idx, current_price)
        
        else:
            # Unknown strategy, use static
            return pos['stop_price']
    
    def _calculate_atr_dynamic_stop(
        self, 
        pos: Dict, 
        df: pd.DataFrame, 
        current_idx: int,
        current_price: float
    ) -> float:
        """
        ATR-based dynamic stop: Adjusts based on current ATR.
        
        Stop = entry_price - (current_ATR * multiplier)
        Clamped between min/max multipliers
        """
        params = self.params['atr_dynamic']
        
        current_atr = df.iloc[current_idx]['ATR20']
        
        # Calculate stop using current ATR
        multiplier = params['multiplier']
        stop = pos['entry_price'] - (current_atr * multiplier)
        
        # Apply min/max constraints
        max_stop = pos['entry_price'] - (current_atr * params['min_multiplier'])
        min_stop = pos['entry_price'] - (current_atr * params['max_multiplier'])
        
        stop = max(min_stop, min(stop, max_stop))
        
        # Never lower the stop (only raise it)
        stop = max(stop, pos['stop_price'])
        
        return stop
    
    def _calculate_pct_trail_stop(
        self, 
        pos: Dict, 
        df: pd.DataFrame, 
        current_idx: int,
        current_price: float
    ) -> float:
        """
        Percentage-based trailing stop: Fixed % below peak price.
        
        Activates after reaching activation_r profit level.
        Stop = peak_price * (1 - trail_pct/100)
        """
        params = self.params['pct_trail']
        
        # Check if activated
        r_multiple = pos['current_r_multiple']
        
        if r_multiple < params['activation_r']:
            # Not activated yet, use initial stop
            return pos['stop_price']
        
        # Calculate trail from peak
        if 'peak_price' not in pos:
            pos['peak_price'] = pos['entry_price']
        
        pos['peak_price'] = max(pos['peak_price'], current_price)
        
        trail_stop = pos['peak_price'] * (1 - params['trail_pct'] / 100)
        
        # Never lower the stop
        trail_stop = max(trail_stop, pos['stop_price'])
        
        return trail_stop
    
    def _calculate_vol_regime_stop(
        self, 
        pos: Dict, 
        df: pd.DataFrame, 
        current_idx: int,
        current_price: float
    ) -> float:
        """
        Volatility regime-adjusted stop: Uses ATR_Z to determine regime.
        
        Low vol (ATR_Z < -0.5): Tighter stop (1.5 ATR)
        Normal vol: Standard stop (2.0 ATR)
        High vol (ATR_Z > 0.5): Wider stop (2.5 ATR)
        """
        params = self.params['vol_regime']
        
        # Get current ATR and ATR_Z
        current_atr = df.iloc[current_idx]['ATR20']
        atr_z = df.iloc[current_idx].get('ATR_Z', 0)
        
        # Determine regime and multiplier
        if atr_z < params['low_vol_threshold']:
            multiplier = params['low_vol_mult']
        elif atr_z > params['high_vol_threshold']:
            multiplier = params['high_vol_mult']
        else:
            multiplier = params['normal_vol_mult']
        
        # Calculate stop
        stop = pos['entry_price'] - (current_atr * multiplier)
        
        # Never lower the stop
        stop = max(stop, pos['stop_price'])
        
        return stop
    
    def _calculate_time_decay_stop(
        self, 
        pos: Dict, 
        df: pd.DataFrame, 
        current_idx: int,
        current_price: float
    ) -> float:
        """
        Time-decay stop: Gradually tightens as position ages.
        
        Days 1-5: 2.5 ATR
        Days 6-10: 2.0 ATR
        Days 11+: 1.5 ATR
        """
        params = self.params['time_decay']
        
        bars_in_trade = pos['bars_in_trade']
        current_atr = df.iloc[current_idx]['ATR20']
        
        # Determine multiplier based on time in trade
        if bars_in_trade <= 5:
            multiplier = params['day_5_mult']
        elif bars_in_trade <= 10:
            # Linear interpolation between day 5 and day 10
            progress = (bars_in_trade - 5) / 5
            multiplier = params['day_5_mult'] + progress * (params['day_10_mult'] - params['day_5_mult'])
        elif bars_in_trade <= 15:
            # Linear interpolation between day 10 and day 15
            progress = (bars_in_trade - 10) / 5
            multiplier = params['day_10_mult'] + progress * (params['day_15_mult'] - params['day_10_mult'])
        else:
            multiplier = params['day_15_mult']
        
        # Calculate stop
        stop = pos['entry_price'] - (current_atr * multiplier)
        
        # Never lower the stop
        stop = max(stop, pos['stop_price'])
        
        return stop
    
    def update_position_with_variable_stop(
        self, 
        ticker: str, 
        current_date: pd.Timestamp, 
        current_price: float, 
        df: pd.DataFrame, 
        current_idx: int
    ) -> Dict:
        """
        Update position with variable stop loss calculation.
        
        This wraps the parent update_position and adds variable stop logic.
        """
        # First, update position using parent class
        exit_signals = self.update_position(
            ticker, current_date, current_price, df, current_idx
        )
        
        # If position still active and not on entry bar, update stop
        if ticker in self.active_positions and self.active_positions[ticker]['bars_in_trade'] > 0:
            new_stop = self.calculate_variable_stop(ticker, df, current_idx)
            
            if new_stop is not None:
                # Update position's stop price
                self.active_positions[ticker]['stop_price'] = new_stop
                
                # Re-check if new stop was hit
                if current_price < new_stop:
                    exit_signals['should_exit'] = True
                    exit_signals['exit_type'] = f'{self.stop_strategy.upper()}_STOP'
                    exit_signals['exit_price'] = current_price
                    exit_signals['reason'] = f"Variable stop ({self.stop_strategy}) hit at {new_stop:.2f}"
        
        return exit_signals


def run_strategy_backtest(
    ticker: str,
    df: pd.DataFrame,
    strategy: str,
    account_value: float = 100000,
    risk_pct: float = 0.75
) -> Tuple[List[Dict], VariableStopRiskManager]:
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
    # Initialize variable stop risk manager
    risk_mgr = VariableStopRiskManager(
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
            # Use variable stop update method
            exit_check = risk_mgr.update_position_with_variable_stop(
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
    parser.add_argument('--period', default='1y', help='Data period (e.g., 1y, 2y)')
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
    
    print("=" * 80)
    print("VARIABLE STOP LOSS TESTING FRAMEWORK")
    print("=" * 80)
    print(f"\nTickers: {', '.join(tickers)}")
    print(f"Period: {args.period}")
    print(f"Strategies: {', '.join(args.strategies)}")
    print("")
    
    # Run comparison
    results_df = compare_stop_strategies(
        tickers=tickers,
        period=args.period,
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
