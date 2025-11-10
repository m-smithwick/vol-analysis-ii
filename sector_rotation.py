"""
Sector Rotation Analysis Module

This module provides sector strength scoring and rotation detection
for the volume analysis trading system. It integrates with existing
backtest infrastructure to identify leading and lagging sectors.

Core functionality:
- Momentum scoring (price vs MAs, returns)
- Volume analysis scoring (win rates, expectancy)
- Relative strength scoring (vs SPY benchmark)
- Sector ranking and allocation recommendations
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import os
import json
import vol_analysis

# Sector ETF to sector name mapping
SECTOR_MAP = {
    'XLK': 'Technology',
    'XLC': 'Communication Services',
    'XLY': 'Consumer Discretionary',
    'XLF': 'Financials',
    'XLV': 'Healthcare',
    'XLI': 'Industrials',
    'XLE': 'Energy',
    'XLB': 'Materials',
    'XLRE': 'Real Estate',
    'XLP': 'Consumer Staples',
    'XLU': 'Utilities'
}

# Score thresholds for recommendations
SCORE_THRESHOLDS = {
    'leading': 8,      # Score >= 8: Overweight
    'strong': 6,       # Score >= 6: Market weight
    'neutral': 4,      # Score >= 4: Light weight
    'weak': 0          # Score < 4: Avoid
}

# Allocation guidelines based on score
ALLOCATION_GUIDE = {
    'leading': (0.35, 0.50),   # 35-50% for top sectors
    'strong': (0.15, 0.25),    # 15-25% for strong sectors
    'neutral': (0.05, 0.10),   # 5-10% for neutral sectors
    'weak': (0.00, 0.00)       # 0% for weak sectors
}


def get_sector_info() -> Dict[str, str]:
    """
    Get mapping of ETF ticker to sector name.
    
    Returns:
        Dict mapping ticker symbols to sector names
    """
    return SECTOR_MAP.copy()


def calculate_momentum_score(df: pd.DataFrame) -> Dict:
    """
    Calculate momentum score based on moving averages and recent returns.
    
    Scoring criteria (max 6 points):
    - Above 50-day MA: +2 points
    - Above 200-day MA: +2 points
    - 20-day return > 5%: +2 points
    
    Args:
        df: DataFrame with OHLCV data and calculated indicators
        
    Returns:
        Dict with score breakdown and details
    """
    result = {
        'score': 0,
        'max_score': 6,
        'details': {}
    }
    
    if df is None or len(df) == 0:
        return result
    
    try:
        current_price = df['Close'].iloc[-1]
        
        # Calculate moving averages if not present
        if 'MA_50' not in df.columns:
            df['MA_50'] = df['Close'].rolling(window=50).mean()
        if 'MA_200' not in df.columns:
            df['MA_200'] = df['Close'].rolling(window=200).mean()
        
        ma_50 = df['MA_50'].iloc[-1]
        ma_200 = df['MA_200'].iloc[-1]
        
        # Check 50-day MA
        if not pd.isna(ma_50) and current_price > ma_50:
            result['score'] += 2
            result['details']['above_50ma'] = {
                'passed': True,
                'points': 2,
                'price': f"${current_price:.2f}",
                'ma': f"${ma_50:.2f}"
            }
        else:
            result['details']['above_50ma'] = {
                'passed': False,
                'points': 0,
                'price': f"${current_price:.2f}",
                'ma': f"${ma_50:.2f}" if not pd.isna(ma_50) else "N/A"
            }
        
        # Check 200-day MA
        if not pd.isna(ma_200) and current_price > ma_200:
            result['score'] += 2
            result['details']['above_200ma'] = {
                'passed': True,
                'points': 2,
                'price': f"${current_price:.2f}",
                'ma': f"${ma_200:.2f}"
            }
        else:
            result['details']['above_200ma'] = {
                'passed': False,
                'points': 0,
                'price': f"${current_price:.2f}",
                'ma': f"${ma_200:.2f}" if not pd.isna(ma_200) else "N/A"
            }
        
        # Check 20-day return
        if len(df) >= 20:
            price_20d_ago = df['Close'].iloc[-20]
            return_20d = ((current_price - price_20d_ago) / price_20d_ago) * 100
            
            if return_20d > 5.0:
                result['score'] += 2
                result['details']['return_20d'] = {
                    'passed': True,
                    'points': 2,
                    'return': f"{return_20d:.2f}%"
                }
            else:
                result['details']['return_20d'] = {
                    'passed': False,
                    'points': 0,
                    'return': f"{return_20d:.2f}%"
                }
        else:
            result['details']['return_20d'] = {
                'passed': False,
                'points': 0,
                'return': "N/A (insufficient data)"
            }
            
    except Exception as e:
        result['error'] = str(e)
    
    return result


def calculate_volume_score(backtest_results: Dict) -> Dict:
    """
    Calculate volume analysis score based on backtest performance.
    
    Scoring criteria (max 6 points):
    - Win rate > 60%: +2 points
    - Positive expectancy: +2 points
    - Recent signals (within 14 days): +2 points
    
    Args:
        backtest_results: Dict containing backtest aggregate results
        
    Returns:
        Dict with score breakdown and details
    """
    result = {
        'score': 0,
        'max_score': 6,
        'details': {}
    }
    
    if not backtest_results:
        return result
    
    try:
        # Get Moderate Buy signal stats (most reliable signal)
        entry_stats = backtest_results.get('entry_signal_stats', {})
        moderate_buy = entry_stats.get('Moderate_Buy_filtered', {})
        
        if not moderate_buy:
            result['details']['no_data'] = "No Moderate Buy signal data available"
            return result
        
        # Check win rate
        win_rate = moderate_buy.get('win_rate', 0)
        if win_rate > 60.0:
            result['score'] += 2
            result['details']['win_rate'] = {
                'passed': True,
                'points': 2,
                'value': f"{win_rate:.1f}%",
                'threshold': "60%"
            }
        else:
            result['details']['win_rate'] = {
                'passed': False,
                'points': 0,
                'value': f"{win_rate:.1f}%",
                'threshold': "60%"
            }
        
        # Check expectancy
        expectancy = moderate_buy.get('expectancy', 0)
        if expectancy > 0:
            result['score'] += 2
            result['details']['expectancy'] = {
                'passed': True,
                'points': 2,
                'value': f"{expectancy:+.2f}%",
                'threshold': ">0%"
            }
        else:
            result['details']['expectancy'] = {
                'passed': False,
                'points': 0,
                'value': f"{expectancy:+.2f}%",
                'threshold': ">0%"
            }
        
        # Check for recent signals (need to look at all trades)
        all_trades = backtest_results.get('all_paired_trades', [])
        if all_trades:
            # Find most recent Moderate Buy signal
            recent_trades = [t for t in all_trades 
                           if 'entry_signals' in t 
                           and t.get('entry_signals', {}).get('Moderate_Buy_filtered', False)]
            
            if recent_trades:
                # Get the most recent entry date
                most_recent = max(recent_trades, key=lambda t: t.get('entry_date', datetime.min))
                entry_date = most_recent.get('entry_date')
                
                if entry_date:
                    if isinstance(entry_date, str):
                        entry_date = pd.to_datetime(entry_date)
                    
                    days_ago = (datetime.now() - entry_date).days
                    
                    if days_ago <= 14:
                        result['score'] += 2
                        result['details']['recent_signals'] = {
                            'passed': True,
                            'points': 2,
                            'days_ago': days_ago,
                            'threshold': "14 days"
                        }
                    else:
                        result['details']['recent_signals'] = {
                            'passed': False,
                            'points': 0,
                            'days_ago': days_ago,
                            'threshold': "14 days"
                        }
                else:
                    result['details']['recent_signals'] = {
                        'passed': False,
                        'points': 0,
                        'reason': "No valid entry date"
                    }
            else:
                result['details']['recent_signals'] = {
                    'passed': False,
                    'points': 0,
                    'reason': "No Moderate Buy signals found"
                }
        else:
            result['details']['recent_signals'] = {
                'passed': False,
                'points': 0,
                'reason': "No trades available"
            }
            
    except Exception as e:
        result['error'] = str(e)
    
    return result


def calculate_relative_strength(df: pd.DataFrame, spy_df: pd.DataFrame, 
                                period_days: int = 63) -> Dict:
    """
    Calculate relative strength score vs SPY benchmark.
    
    Scoring criteria (max 2 points):
    - Outperforming SPY over period: +1 point
    - Among top performing sectors: +1 point
    
    Args:
        df: Sector ETF DataFrame
        spy_df: SPY benchmark DataFrame
        period_days: Lookback period (default 63 = ~3 months)
        
    Returns:
        Dict with score breakdown and details
    """
    result = {
        'score': 0,
        'max_score': 2,
        'details': {}
    }
    
    if df is None or spy_df is None or len(df) < period_days or len(spy_df) < period_days:
        result['details']['insufficient_data'] = True
        return result
    
    try:
        # Calculate returns over period
        sector_return = ((df['Close'].iloc[-1] - df['Close'].iloc[-period_days]) / 
                        df['Close'].iloc[-period_days]) * 100
        
        spy_return = ((spy_df['Close'].iloc[-1] - spy_df['Close'].iloc[-period_days]) / 
                     spy_df['Close'].iloc[-period_days]) * 100
        
        # Check if outperforming SPY
        if sector_return > spy_return:
            result['score'] += 1
            result['details']['vs_spy'] = {
                'passed': True,
                'points': 1,
                'sector_return': f"{sector_return:+.2f}%",
                'spy_return': f"{spy_return:+.2f}%",
                'outperformance': f"{sector_return - spy_return:+.2f}%"
            }
        else:
            result['details']['vs_spy'] = {
                'passed': False,
                'points': 0,
                'sector_return': f"{sector_return:+.2f}%",
                'spy_return': f"{spy_return:+.2f}%",
                'underperformance': f"{sector_return - spy_return:+.2f}%"
            }
        
        # Store return for ranking (will add point in rank_sectors function)
        result['sector_return'] = sector_return
        result['spy_return'] = spy_return
        
    except Exception as e:
        result['error'] = str(e)
    
    return result


def calculate_sector_score(ticker: str, period: str = '3mo', 
                          backtest_results: Optional[Dict] = None,
                          spy_df: Optional[pd.DataFrame] = None) -> Dict:
    """
    Calculate comprehensive sector score combining all metrics.
    
    Args:
        ticker: Sector ETF ticker symbol
        period: Analysis period (e.g., '3mo', '6mo', '12mo')
        backtest_results: Pre-computed backtest results (optional)
        spy_df: SPY benchmark data (optional, will fetch if not provided)
        
    Returns:
        Dict with complete sector analysis and score
    """
    result = {
        'ticker': ticker,
        'sector': SECTOR_MAP.get(ticker, 'Unknown'),
        'period': period,
        'total_score': 0,
        'max_score': 14,
        'momentum': {},
        'volume': {},
        'relative_strength': {},
        'recommendation': '',
        'timestamp': datetime.now().isoformat()
    }
    
    try:
        # Fetch sector ETF data
        df = vol_analysis.analyze_ticker(
            ticker=ticker,
            period=period,
            save_to_file=False,
            save_chart=False,
            force_refresh=False,
            show_chart=False,
            show_summary=False
        )
        
        if df is None or len(df) == 0:
            result['error'] = "Failed to fetch data"
            return result
        
        # Calculate momentum score
        momentum_result = calculate_momentum_score(df)
        result['momentum'] = momentum_result
        result['total_score'] += momentum_result['score']
        
        # Calculate volume score (requires backtest)
        if backtest_results:
            volume_result = calculate_volume_score(backtest_results)
            result['volume'] = volume_result
            result['total_score'] += volume_result['score']
        else:
            result['volume'] = {
                'score': 0,
                'max_score': 6,
                'note': 'Backtest results not provided'
            }
        
        # Calculate relative strength vs SPY
        if spy_df is None:
            # Fetch SPY data
            spy_df = vol_analysis.analyze_ticker(
                ticker='SPY',
                period=period,
                save_to_file=False,
                save_chart=False,
                force_refresh=False,
                show_chart=False,
                show_summary=False
            )
        
        if spy_df is not None:
            # Convert period to days for calculation
            period_days = {
                '1mo': 21,
                '3mo': 63,
                '6mo': 126,
                '12mo': 252
            }.get(period, 63)
            
            rs_result = calculate_relative_strength(df, spy_df, period_days)
            result['relative_strength'] = rs_result
            result['total_score'] += rs_result['score']
        else:
            result['relative_strength'] = {
                'score': 0,
                'max_score': 2,
                'note': 'SPY data not available'
            }
        
        # Generate recommendation based on total score
        score = result['total_score']
        if score >= SCORE_THRESHOLDS['leading']:
            result['recommendation'] = 'OVERWEIGHT'
            result['allocation_range'] = ALLOCATION_GUIDE['leading']
        elif score >= SCORE_THRESHOLDS['strong']:
            result['recommendation'] = 'MARKET WEIGHT'
            result['allocation_range'] = ALLOCATION_GUIDE['strong']
        elif score >= SCORE_THRESHOLDS['neutral']:
            result['recommendation'] = 'LIGHT WEIGHT'
            result['allocation_range'] = ALLOCATION_GUIDE['neutral']
        else:
            result['recommendation'] = 'AVOID'
            result['allocation_range'] = ALLOCATION_GUIDE['weak']
        
    except Exception as e:
        result['error'] = str(e)
    
    return result


def rank_sectors(period: str = '3mo', 
                sectors_file: str = 'sector_etfs.txt') -> List[Dict]:
    """
    Analyze and rank all sectors by strength score.
    
    Args:
        period: Analysis period
        sectors_file: Path to file containing sector ETF tickers
        
    Returns:
        List of sector analysis dicts sorted by score (highest first)
    """
    # Read sector tickers
    if not os.path.exists(sectors_file):
        raise FileNotFoundError(f"Sector file not found: {sectors_file}")
    
    with open(sectors_file, 'r') as f:
        tickers = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    # Fetch SPY once for all comparisons
    print("Fetching SPY benchmark data...")
    spy_df = vol_analysis.analyze_ticker(
        ticker='SPY',
        period=period,
        save_to_file=False,
        save_chart=False,
        force_refresh=False,
        show_chart=False,
        show_summary=False
    )
    
    results = []
    for ticker in tickers:
        print(f"Analyzing {ticker} ({SECTOR_MAP.get(ticker, 'Unknown')})...")
        
        # Calculate sector score
        # Note: Backtest integration happens in sector_dashboard.py
        sector_data = calculate_sector_score(
            ticker=ticker,
            period=period,
            backtest_results=None,  # Will be added by dashboard
            spy_df=spy_df
        )
        
        results.append(sector_data)
    
    # Sort by total score (descending)
    results.sort(key=lambda x: x['total_score'], reverse=True)
    
    # Add ranking position and top-sector bonus point
    for i, sector in enumerate(results, 1):
        sector['rank'] = i
        
        # Award top-3 sectors an extra point for relative strength
        if i <= 3 and 'relative_strength' in sector:
            sector['relative_strength']['score'] += 1
            sector['total_score'] += 1
            if 'details' not in sector['relative_strength']:
                sector['relative_strength']['details'] = {}
            sector['relative_strength']['details']['top_sector_bonus'] = {
                'passed': True,
                'points': 1,
                'rank': i
            }
    
    return results


def detect_rotation_alerts(current_scores: List[Dict], 
                          previous_scores: Optional[List[Dict]] = None) -> List[Dict]:
    """
    Detect significant sector rotation opportunities.
    
    Args:
        current_scores: Current sector scores
        previous_scores: Previous period sector scores (optional)
        
    Returns:
        List of rotation alerts
    """
    alerts = []
    
    if not previous_scores:
        return alerts
    
    # Create lookup dict for previous scores
    prev_lookup = {s['ticker']: s for s in previous_scores}
    
    for current in current_scores:
        ticker = current['ticker']
        sector = current['sector']
        curr_score = current['total_score']
        
        if ticker not in prev_lookup:
            continue
        
        prev_score = prev_lookup[ticker]['total_score']
        score_change = curr_score - prev_score
        
        # Alert thresholds
        if score_change >= 3:
            alerts.append({
                'type': 'STRENGTH_IMPROVING',
                'ticker': ticker,
                'sector': sector,
                'previous_score': prev_score,
                'current_score': curr_score,
                'change': score_change,
                'action': 'WATCH for entry opportunity'
            })
        elif score_change <= -3:
            alerts.append({
                'type': 'STRENGTH_DETERIORATING',
                'ticker': ticker,
                'sector': sector,
                'previous_score': prev_score,
                'current_score': curr_score,
                'change': score_change,
                'action': 'Consider reducing exposure'
            })
        elif curr_score >= 6 and prev_score < 6:
            alerts.append({
                'type': 'CROSSING_INTO_STRONG',
                'ticker': ticker,
                'sector': sector,
                'previous_score': prev_score,
                'current_score': curr_score,
                'change': score_change,
                'action': 'Potential entry opportunity'
            })
        elif curr_score < 6 and prev_score >= 6:
            alerts.append({
                'type': 'FALLING_BELOW_STRONG',
                'ticker': ticker,
                'sector': sector,
                'previous_score': prev_score,
                'current_score': curr_score,
                'change': score_change,
                'action': 'Consider exit/reduce position'
            })
    
    return alerts


if __name__ == "__main__":
    # Simple test
    print("Testing sector rotation module...")
    print(f"Sector map: {len(SECTOR_MAP)} sectors")
    print("Use sector_dashboard.py for full analysis")
