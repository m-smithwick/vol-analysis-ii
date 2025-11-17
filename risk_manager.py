"""
Risk Management Framework for Volume Analysis Trading System

Provides unified risk management across all trades:
- Position sizing based on risk percentage
- Initial stop placement using swing/VWAP logic
- Time-based exits for dead positions
- Hard stops for capital protection
- Profit scaling at +2R with trailing stops
- Integrates with regular exit signals for optimal exits

Part of upgrade_spec.md Item #13
Updated Nov 2025: Removed aggressive momentum checks, uses regular exit signals
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, List


class RiskManager:
    SUPPORTED_STOP_STRATEGIES = {'static', 'vol_regime', 'atr_dynamic', 'pct_trail', 'time_decay'}

    """
    Unified risk management for all trades.
    
    Handles complete trade lifecycle from sizing to exit:
    - Risk-based position sizing (0.5-1% per trade)
    - Initial stop: min(swing_low - 0.5*ATR, VWAP - 1*ATR)
    - Hard stops: Exit below initial stop price
    - Time stops: Exit after 12 bars if <+1R (dead positions)
    - Regular exit signals: Integrates with proven exit system
    - Profit scaling: 50% at +2R, trail rest by 10-day low
    
    Note: Aggressive momentum checks (CMF<0/price<VWAP) removed Nov 2025.
    System now relies on proven exit signals for optimal exit timing.
    """
    
    def __init__(self, account_value: float, risk_pct_per_trade: float = 0.75,
                 stop_strategy: str = 'time_decay'):
        """
        Initialize risk manager.
        
        Args:
            account_value: Total account equity
            risk_pct_per_trade: Risk percentage per trade (0.5-1.0% recommended)
            stop_strategy: Stop loss strategy - 'static', 'vol_regime', 'atr_dynamic', 'pct_trail', 'time_decay'
        """
        self.account_value = account_value
        self.starting_equity = account_value
        self.equity = account_value
        self.risk_pct = risk_pct_per_trade
        strategy = (stop_strategy or 'static').lower()
        if strategy not in self.SUPPORTED_STOP_STRATEGIES:
            raise ValueError(f"Unsupported stop strategy '{stop_strategy}'. Choose from {sorted(self.SUPPORTED_STOP_STRATEGIES)}")
        self.stop_strategy = strategy
        self.active_positions: Dict[str, Dict] = {}
        self.closed_trades: List[Dict] = []
        
        # Stop strategy parameters (lifted from validation harness)
        self.stop_params = {
            'vol_regime': {
                'low_vol_mult': 1.5,
                'normal_vol_mult': 2.0,
                'high_vol_mult': 2.5,
                'low_threshold': -0.5,
                'high_threshold': 0.5
            },
            'atr_dynamic': {
                'multiplier': 2.0,
                'min_multiplier': 1.5,
                'max_multiplier': 3.0
            },
            'pct_trail': {
                'trail_pct': 8.0,
                'activation_r': 1.0
            },
            'time_decay': {
                'day_5_mult': 2.5,
                'day_10_mult': 2.0,
                'day_15_mult': 1.5
            }
        }
    
    def calculate_position_size(self, entry_price: float, stop_price: float) -> int:
        """
        Calculate position size based on risk percentage.
        
        From tweaks.txt: Risk 0.5-1.0% per trade
        
        Formula:
        risk_amount = current_equity * (risk_pct / 100)
        risk_per_share = entry_price - stop_price
        position_size = risk_amount / risk_per_share
        
        Args:
            entry_price: Planned entry price
            stop_price: Initial stop loss price
            
        Returns:
            Number of shares to buy
            
        Raises:
            ValueError: If stop price is invalid
        """
        if stop_price >= entry_price:
            raise ValueError(f"Stop price ({stop_price:.2f}) must be below entry price ({entry_price:.2f})")
        risk_amount = self.equity * (self.risk_pct / 100)
        if risk_amount <= 0:
            raise ValueError("Account equity depleted; cannot calculate position size")
        risk_per_share = entry_price - stop_price
        
        position_size = risk_amount / risk_per_share
        
        return int(position_size)  # Round down to whole shares
    
    def calculate_initial_stop(self, df: pd.DataFrame, entry_idx: int) -> float:
        """
        Calculate initial stop loss placement.
        
        From tweaks.txt:
        stop = min(recent_swing_low - 0.5*ATR, anchored_VWAP - 1*ATR)
        
        Takes the tighter of:
        1. Swing low minus 0.5 ATR (structure-based)
        2. Anchored VWAP minus 1 ATR (cost basis)
        
        Args:
            df: DataFrame with price data and indicators
            entry_idx: Integer position in DataFrame (use .iloc)
            
        Returns:
            Stop loss price
            
        Raises:
            KeyError: If required columns missing
        """
        required_cols = ['Recent_Swing_Low', 'ATR20', 'VWAP']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise KeyError(f"Missing required columns: {missing_cols}")
        
        # Use .iloc for integer positions
        swing_stop = df.iloc[entry_idx]['Recent_Swing_Low'] - (0.5 * df.iloc[entry_idx]['ATR20'])
        vwap_stop = df.iloc[entry_idx]['VWAP'] - (1.0 * df.iloc[entry_idx]['ATR20'])
        
        initial_stop = min(swing_stop, vwap_stop)
        
        return initial_stop
    
    def calculate_vol_regime_stop(
        self, 
        pos: Dict, 
        df: pd.DataFrame, 
        current_idx: int
    ) -> float:
        """
        Calculate volatility regime-adjusted stop loss.
        
        Uses ATR_Z (volatility z-score) to determine market regime and adjust
        stop distance accordingly. Validated with 371 trades showing +30% improvement.
        
        Regime Logic:
        - Low vol (ATR_Z < -0.5): Tighter 1.5 ATR stop (calm markets)
        - Normal vol: Standard 2.0 ATR stop
        - High vol (ATR_Z > 0.5): Wider 2.5 ATR stop (volatile markets)
        
        Args:
            pos: Position dictionary with entry info
            df: DataFrame with indicators including ATR20 and ATR_Z
            current_idx: Current bar index
            
        Returns:
            Updated stop price (never lower than current stop)
        """
        # Get current volatility metrics
        current_atr = df.iloc[current_idx]['ATR20']
        atr_z = df.iloc[current_idx].get('ATR_Z', 0)
        
        # Determine regime and multiplier
        params = self.stop_params['vol_regime']
        if atr_z < params['low_threshold']:
            multiplier = params['low_vol_mult']
        elif atr_z > params['high_threshold']:
            multiplier = params['high_vol_mult']
        else:
            multiplier = params['normal_vol_mult']
        
        # Calculate new stop from entry price
        new_stop = pos['entry_price'] - (current_atr * multiplier)
        
        # Never lower the stop (only tighten)
        return max(new_stop, pos['stop_price'])
    
    def calculate_variable_stop(
        self, 
        ticker: str, 
        df: pd.DataFrame, 
        current_idx: int
    ) -> Optional[float]:
        """
        Calculate variable stop based on selected strategy.
        
        Routes to appropriate stop calculation method based on self.stop_strategy.
        Returns None if static strategy or position doesn't exist.
        
        Args:
            ticker: Stock symbol
            df: DataFrame with indicators
            current_idx: Current bar index
            
        Returns:
            Updated stop price or None
        """
        if ticker not in self.active_positions:
            return None
        
        if self.stop_strategy == 'static':
            # No variable stop adjustment
            return None
        
        pos = self.active_positions[ticker]
        current_price = df.iloc[current_idx]['Close']
        
        if self.stop_strategy == 'vol_regime':
            return self.calculate_vol_regime_stop(pos, df, current_idx)
        if self.stop_strategy == 'atr_dynamic':
            return self._calculate_atr_dynamic_stop(pos, df, current_idx)
        if self.stop_strategy == 'pct_trail':
            return self._calculate_pct_trail_stop(pos, df, current_idx, current_price)
        if self.stop_strategy == 'time_decay':
            return self._calculate_time_decay_stop(pos, df, current_idx)
        
        # Unknown strategy - use static
        return None

    def _calculate_atr_dynamic_stop(
        self,
        pos: Dict,
        df: pd.DataFrame,
        current_idx: int
    ) -> float:
        """
        ATR-based dynamic stop: Adjusts between min/max multipliers.
        """
        params = self.stop_params['atr_dynamic']
        current_atr = df.iloc[current_idx]['ATR20']
        multiplier = params['multiplier']
        stop = pos['entry_price'] - (current_atr * multiplier)
        max_stop = pos['entry_price'] - (current_atr * params['min_multiplier'])
        min_stop = pos['entry_price'] - (current_atr * params['max_multiplier'])
        stop = max(min_stop, min(stop, max_stop))
        return max(stop, pos['stop_price'])

    def _calculate_pct_trail_stop(
        self,
        pos: Dict,
        df: pd.DataFrame,
        current_idx: int,
        current_price: float
    ) -> float:
        """
        Percentage-based trailing stop activated after reaching activation R.
        """
        params = self.stop_params['pct_trail']
        if pos['current_r_multiple'] < params['activation_r']:
            return pos['stop_price']
        if 'peak_price' not in pos:
            pos['peak_price'] = pos['entry_price']
        pos['peak_price'] = max(pos['peak_price'], current_price)
        trail_stop = pos['peak_price'] * (1 - params['trail_pct'] / 100)
        return max(trail_stop, pos['stop_price'])

    def _calculate_time_decay_stop(
        self,
        pos: Dict,
        df: pd.DataFrame,
        current_idx: int
    ) -> float:
        """
        Time-decay stop: gradually tightens as the trade ages.
        """
        params = self.stop_params['time_decay']
        bars_in_trade = pos['bars_in_trade']
        current_atr = df.iloc[current_idx]['ATR20']
        if bars_in_trade <= 5:
            multiplier = params['day_5_mult']
        elif bars_in_trade <= 10:
            progress = (bars_in_trade - 5) / 5
            multiplier = params['day_5_mult'] + progress * (params['day_10_mult'] - params['day_5_mult'])
        elif bars_in_trade <= 15:
            progress = (bars_in_trade - 10) / 5
            multiplier = params['day_10_mult'] + progress * (params['day_15_mult'] - params['day_10_mult'])
        else:
            multiplier = params['day_15_mult']
        stop = pos['entry_price'] - (current_atr * multiplier)
        return max(stop, pos['stop_price'])
    
    def open_position(
        self, 
        ticker: str, 
        entry_date: pd.Timestamp, 
        entry_price: float, 
        stop_price: float, 
        entry_idx: int,
        df: pd.DataFrame
    ) -> Dict:
        """
        Open a new position with full risk management.
        
        Args:
            ticker: Stock symbol
            entry_date: Date of entry
            entry_price: Entry price
            stop_price: Initial stop price
            entry_idx: Index in df for entry
            df: DataFrame with indicators
            
        Returns:
            Position dictionary with all tracking fields
        """
        position_size = self.calculate_position_size(entry_price, stop_price)
        
        if position_size <= 0:
            raise ValueError("Calculated position size is zero - check risk parameters or stop distance")
        
        position = {
            'ticker': ticker,
            'entry_date': entry_date,
            'entry_price': entry_price,
            'stop_price': stop_price,
            'position_size': position_size,
            'original_position_size': position_size,
            'entry_idx': entry_idx,
            'bars_in_trade': 0,
            'peak_r_multiple': 0.0,
            'profit_taken_50pct': False,
            'trail_stop_active': False,
            'trail_stop_price': None,
            'current_r_multiple': 0.0,
            'peak_price': entry_price,
            'equity_at_entry': self.equity
        }
        
        self.active_positions[ticker] = position
        
        return position
    
    def update_position(
        self, 
        ticker: str, 
        current_date: pd.Timestamp, 
        current_price: float, 
        df: pd.DataFrame, 
        current_idx: int
    ) -> Dict:
        """
        Update position status and check risk management exit conditions.
        
        Risk management exits (in order):
        1. Hard stop hit (below initial stop) - Capital protection
        2. Time stop (12 bars if <+1R) - Dead position management
        3. Profit target (+2R for 50% exit) - Lock in gains
        4. Trailing stop (10-day low after +2R) - Let winners run
        
        Note: Regular exit signals (Distribution Warning, Momentum Exhaustion, etc.)
        are checked separately in the backtest loop and integrated with these rules.
        
        CRITICAL: Exit checks only run on bars AFTER entry bar to ensure
        end-of-day signals have at least 1 full bar to develop.
        
        Args:
            ticker: Stock symbol
            current_date: Current date
            current_price: Current price
            df: DataFrame with indicators
            current_idx: Current index in df
            
        Returns:
            Dict with exit signals and reasons
        """
        if ticker not in self.active_positions:
            return {'should_exit': False}
        
        pos = self.active_positions[ticker]
        
        # Calculate position metrics
        pos['bars_in_trade'] = current_idx - pos['entry_idx']
        risk_amount = pos['entry_price'] - pos['stop_price']
        profit_amount = current_price - pos['entry_price']
        r_multiple = profit_amount / risk_amount if risk_amount > 0 else 0
        pos['current_r_multiple'] = r_multiple
        pos['peak_r_multiple'] = max(pos['peak_r_multiple'], r_multiple)
        
        exit_signals = {
            'should_exit': False,
            'exit_type': None,
            'exit_price': current_price,
            'partial_exit': False,
            'exit_pct': 1.0,
            'r_multiple': r_multiple,
            'reason': None
        }
        
        # CRITICAL FIX: Do not check exits on entry bar (bars_in_trade = 0)
        # This ensures end-of-day signals have at least 1 full bar before exit checks
        # Entry happens at open of bar N, we don't check exits until bar N+1
        if pos['bars_in_trade'] == 0:
            return exit_signals
        
        # Exit checks only run when bars_in_trade >= 1
        # This prevents same-day exits for end-of-day signal systems
        
        # UPDATE VARIABLE STOP (if enabled)
        # This runs after bars_in_trade check to ensure at least 1 bar has passed
        if self.stop_strategy != 'static':
            new_stop = self.calculate_variable_stop(ticker, df, current_idx)
            if new_stop is not None:
                pos['stop_price'] = new_stop
        
        # 1. HARD STOP: Below initial stop (or variable stop if enabled)
        if current_price < pos['stop_price']:
            exit_signals['should_exit'] = True
            if self.stop_strategy == 'static':
                exit_signals['exit_type'] = 'HARD_STOP'
            else:
                exit_signals['exit_type'] = f"{self.stop_strategy.upper()}_STOP"
            exit_signals['exit_price'] = pos['stop_price']
            exit_signals['reason'] = f"Stop hit at {pos['stop_price']:.2f}"
            return exit_signals
        
        # 2. TIME STOP: Exit after 12 bars if <+1R
        if pos['bars_in_trade'] >= 12 and r_multiple < 1.0:
            exit_signals['should_exit'] = True
            exit_signals['exit_type'] = 'TIME_STOP'
            exit_signals['reason'] = f"Time stop: {pos['bars_in_trade']} bars, {r_multiple:.2f}R"
            return exit_signals
        
        # NOTE: Momentum failure check removed - use regular exit signals instead
        # Regular exit signals (Distribution Warning, Momentum Exhaustion, etc.)
        # are more reliable for end-of-day trading and should be checked separately
        
        # 3. PROFIT TARGET: Take 50% at +2R
        if r_multiple >= 2.0 and not pos['profit_taken_50pct']:
            exit_signals['should_exit'] = True
            exit_signals['partial_exit'] = True
            exit_signals['exit_pct'] = 0.5
            exit_signals['exit_type'] = 'PROFIT_TARGET'
            exit_signals['reason'] = f"Profit target: {r_multiple:.2f}R achieved, taking 50%"
            
            # Activate trailing stop for remaining 50%
            pos['profit_taken_50pct'] = True
            pos['trail_stop_active'] = True
            
            # Initialize trailing stop to 10-day low
            if current_idx >= 10:
                trail_stop = df.iloc[current_idx-9:current_idx+1]['Close'].min()
            else:
                trail_stop = df.iloc[:current_idx+1]['Close'].min()
            
            pos['trail_stop_price'] = trail_stop
            
            return exit_signals
        
        # 4. TRAILING STOP: 10-day low after +2R
        if pos['trail_stop_active'] and pos['trail_stop_price'] is not None:
            # Update trailing stop to 10-day low
            if current_idx >= 10:
                trail_stop = df.iloc[current_idx-9:current_idx+1]['Close'].min()
            else:
                trail_stop = df.iloc[:current_idx+1]['Close'].min()
            
            # Only raise the stop, never lower it
            pos['trail_stop_price'] = max(pos['trail_stop_price'], trail_stop)
            
            if current_price < pos['trail_stop_price']:
                exit_signals['should_exit'] = True
                exit_signals['exit_type'] = 'TRAIL_STOP'
                exit_signals['reason'] = f"Trailing stop hit at {pos['trail_stop_price']:.2f}"
                return exit_signals
        
        return exit_signals
    
    def close_position(
        self, 
        ticker: str, 
        exit_price: float, 
        exit_type: str, 
        exit_date: pd.Timestamp,
        partial_exit_pct: float = 1.0
    ) -> Optional[Dict]:
        """
        Close position and calculate final P&L.
        
        Args:
            ticker: Stock symbol
            exit_price: Final exit price
            exit_type: Reason for exit
            exit_date: Date of exit
            partial_exit_pct: Percentage of position exited (0.5 for 50%, 1.0 for full)
            
        Returns:
            Trade result dictionary, or None if position doesn't exist
        """
        if ticker not in self.active_positions:
            return None
        
        pos = self.active_positions[ticker]
        
        # Calculate final P&L
        risk_amount = pos['entry_price'] - pos['stop_price']
        profit_amount = exit_price - pos['entry_price']
        r_multiple = profit_amount / risk_amount if risk_amount > 0 else 0
        
        # If partial exit, adjust position size
        if partial_exit_pct < 1.0:
            # This is a 50% exit, keep position open
            exit_size = int(pos['position_size'] * partial_exit_pct)
            pos['position_size'] = pos['position_size'] - exit_size
            
            # Record partial exit as separate trade
            pnl = exit_size * (exit_price - pos['entry_price'])
            self.equity += pnl
            partial_trade = {
                'ticker': ticker,
                'entry_date': pos['entry_date'],
                'entry_price': pos['entry_price'],
                'exit_date': exit_date,
                'exit_price': exit_price,
                'exit_type': exit_type,
                'bars_held': pos['bars_in_trade'],
                'r_multiple': r_multiple,
                'profit_pct': (exit_price / pos['entry_price'] - 1) * 100,
                'position_size': exit_size,
                'partial_exit': True,
                'exit_pct': partial_exit_pct,
                'peak_r_multiple': pos['peak_r_multiple'],
                'profit_taken_50pct': exit_type == 'PROFIT_TARGET',
                'dollar_pnl': pnl,
                'equity_after_trade': self.equity
            }
            
            self.closed_trades.append(partial_trade)
            
            return partial_trade
        else:
            # Full exit - close position
            # Account for partial exit if 50% was taken earlier
            if pos['profit_taken_50pct']:
                # 50% was taken at +2R, calculate blended result
                first_half_r = 2.0
                second_half_r = r_multiple
                blended_r = (first_half_r + second_half_r) / 2
            else:
                blended_r = r_multiple
            
            exit_size = pos['position_size']
            pnl = exit_size * (exit_price - pos['entry_price'])
            self.equity += pnl
            
            trade_result = {
                'ticker': ticker,
                'entry_date': pos['entry_date'],
                'entry_price': pos['entry_price'],
                'exit_date': exit_date,
                'exit_price': exit_price,
                'exit_type': exit_type,
                'bars_held': pos['bars_in_trade'],
                'r_multiple': blended_r,
                'profit_pct': (exit_price / pos['entry_price'] - 1) * 100,
                'position_size': pos['position_size'],
                'partial_exit': False,
                'exit_pct': 1.0,
                'profit_taken_50pct': pos['profit_taken_50pct'],
                'peak_r_multiple': pos['peak_r_multiple'],
                'dollar_pnl': pnl,
                'equity_after_trade': self.equity
            }
            
            self.closed_trades.append(trade_result)
            
            # Remove from active positions
            del self.active_positions[ticker]
            
            return trade_result
    
    def get_position_status(self, ticker: str) -> Optional[Dict]:
        """
        Get current status of an active position.
        
        Args:
            ticker: Stock symbol
            
        Returns:
            Position status dict or None if not found
        """
        return self.active_positions.get(ticker)
    
    def get_all_trades(self) -> List[Dict]:
        """
        Get all closed trades.
        
        Returns:
            List of trade result dictionaries
        """
        return self.closed_trades
    
    def reset(self):
        """Reset risk manager state (for testing/new analysis)."""
        self.active_positions = {}
        self.closed_trades = []
        self.equity = self.starting_equity


def analyze_risk_managed_trades(trades: List[Dict]) -> Dict:
    """
    Analyze trades managed by RiskManager.
    
    Provides comprehensive performance statistics including:
    - Win rate and R-multiple metrics
    - Exit type distribution
    - Profit scaling effectiveness
    
    Args:
        trades: List of trade result dictionaries
        
    Returns:
        Dict with performance analysis
    """
    if not trades:
        return {
            'error': 'No trades to analyze',
            'Total Trades': 0
        }
    
    trades_df = pd.DataFrame(trades)
    
    # Ensure optional columns exist for downstream aggregation
    if 'profit_taken_50pct' not in trades_df.columns:
        trades_df['profit_taken_50pct'] = False
    else:
        trades_df['profit_taken_50pct'] = trades_df['profit_taken_50pct'].fillna(False)
    
    if 'dollar_pnl' not in trades_df.columns:
        trades_df['dollar_pnl'] = 0.0
    else:
        trades_df['dollar_pnl'] = trades_df['dollar_pnl'].fillna(0.0)
    
    if 'equity_after_trade' not in trades_df.columns:
        trades_df['equity_after_trade'] = np.nan
    else:
        trades_df['equity_after_trade'] = trades_df['equity_after_trade'].astype(float)
    
    if 'partial_exit' not in trades_df.columns:
        trades_df['partial_exit'] = False
    else:
        trades_df['partial_exit'] = trades_df['partial_exit'].fillna(False)
    
    total_dollar_pnl = trades_df['dollar_pnl'].sum()
    ending_equity = trades_df['equity_after_trade'].dropna().iloc[-1] if trades_df['equity_after_trade'].notna().any() else None
    
    analysis = {
        'Total Trades': len(trades),
        'Win Rate': f"{(trades_df['r_multiple'] > 0).sum() / len(trades) * 100:.1f}%",
        'Average R-Multiple': f"{trades_df['r_multiple'].mean():.2f}R",
        'Average Profit %': f"{trades_df['profit_pct'].mean():.2f}%",
        'Average Bars Held': f"{trades_df['bars_held'].mean():.1f}",
        'Profit Scaling Used': ((trades_df['profit_taken_50pct']) & (~trades_df['partial_exit'])).sum(),
        'Total Dollar P&L': f"${total_dollar_pnl:,.0f}",
        'Ending Equity': f"${ending_equity:,.0f}" if ending_equity is not None else "N/A",
        
        # By exit type
        'Exit Type Breakdown': {
            'Time Stops': (trades_df['exit_type'] == 'TIME_STOP').sum(),
            'Hard Stops': (trades_df['exit_type'] == 'HARD_STOP').sum(),
            'Momentum Fails': (trades_df['exit_type'] == 'MOMENTUM_FAIL').sum(),
            'Profit Targets': (trades_df['exit_type'] == 'PROFIT_TARGET').sum(),
            'Trailing Stops': (trades_df['exit_type'] == 'TRAIL_STOP').sum(),
        },
        
        # R-multiple distribution
        'R-Multiple Distribution': {
            'Trades > +2R': (trades_df['r_multiple'] >= 2.0).sum(),
            'Trades +1R to +2R': ((trades_df['r_multiple'] >= 1.0) & (trades_df['r_multiple'] < 2.0)).sum(),
            'Trades 0 to +1R': ((trades_df['r_multiple'] > 0) & (trades_df['r_multiple'] < 1.0)).sum(),
            'Losing Trades': (trades_df['r_multiple'] < 0).sum()
        },
        
        # Best/worst trades
        'Best Trade': f"{trades_df['r_multiple'].max():.2f}R",
        'Worst Trade': f"{trades_df['r_multiple'].min():.2f}R",
        'Peak R-Multiple Avg': f"{trades_df['peak_r_multiple'].mean():.2f}R"
    }
    
    return analysis
