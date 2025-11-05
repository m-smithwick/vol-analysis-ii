"""
Market and Sector Regime Filter

Prevents entry signals when broad market or sector is in distribution.
From upgrade_spec.md Item #6 - Enhanced with specific MA thresholds from tweaks.txt.

Rules:
- SPY close > SPY 200-day MA (market regime)
- Sector ETF close > 50-day MA (sector regime)
- Both must be true to allow entry signals

Author: Volume Analysis System
Last Updated: 2025-11-05
"""

import pandas as pd
import yfinance as yf
from typing import Dict, Optional
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Sector ETF mapping
SECTOR_ETFS = {
    # Technology
    'AAPL': 'XLK', 'MSFT': 'XLK', 'GOOGL': 'XLK', 'GOOG': 'XLK',
    'NVDA': 'XLK', 'META': 'XLK', 'TSLA': 'XLK', 'AMD': 'XLK',
    'INTC': 'XLK', 'CRM': 'XLK', 'ORCL': 'XLK', 'CSCO': 'XLK',
    'AVGO': 'XLK', 'ADBE': 'XLK', 'QCOM': 'XLK', 'TXN': 'XLK',
    
    # Financials
    'JPM': 'XLF', 'BAC': 'XLF', 'WFC': 'XLF', 'GS': 'XLF',
    'MS': 'XLF', 'C': 'XLF', 'BLK': 'XLF', 'SCHW': 'XLF',
    'AXP': 'XLF', 'USB': 'XLF', 'PNC': 'XLF', 'TFC': 'XLF',
    
    # Healthcare
    'JNJ': 'XLV', 'PFE': 'XLV', 'UNH': 'XLV', 'MRK': 'XLV',
    'ABBV': 'XLV', 'TMO': 'XLV', 'ABT': 'XLV', 'DHR': 'XLV',
    'LLY': 'XLV', 'BMY': 'XLV', 'AMGN': 'XLV', 'CVS': 'XLV',
    
    # Energy
    'XOM': 'XLE', 'CVX': 'XLE', 'COP': 'XLE', 'SLB': 'XLE',
    'EOG': 'XLE', 'PSX': 'XLE', 'MPC': 'XLE', 'VLO': 'XLE',
    
    # Consumer Discretionary
    'AMZN': 'XLY', 'HD': 'XLY', 'MCD': 'XLY', 'NKE': 'XLY',
    'SBUX': 'XLY', 'LOW': 'XLY', 'TGT': 'XLY', 'DIS': 'XLY',
    
    # Consumer Staples
    'WMT': 'XLP', 'PG': 'XLP', 'KO': 'XLP', 'PEP': 'XLP',
    'COST': 'XLP', 'PM': 'XLP', 'MO': 'XLP', 'CL': 'XLP',
    
    # Industrials
    'CAT': 'XLI', 'BA': 'XLI', 'HON': 'XLI', 'UNP': 'XLI',
    'UPS': 'XLI', 'RTX': 'XLI', 'LMT': 'XLI', 'GE': 'XLI',
    
    # Utilities
    'NEE': 'XLU', 'DUK': 'XLU', 'SO': 'XLU', 'D': 'XLU',
    
    # Real Estate
    'AMT': 'XLRE', 'PLD': 'XLRE', 'CCI': 'XLRE', 'EQIX': 'XLRE',
    
    # Materials
    'LIN': 'XLB', 'APD': 'XLB', 'ECL': 'XLB', 'DD': 'XLB',
    
    # Communication Services
    'NFLX': 'XLC', 'CMCSA': 'XLC', 'T': 'XLC', 'VZ': 'XLC',
    
    # Default fallback
    'DEFAULT': 'SPY'
}


def get_sector_etf(ticker: str) -> str:
    """
    Get the appropriate sector ETF for a ticker.
    
    Args:
        ticker: Stock symbol
        
    Returns:
        Sector ETF symbol (defaults to SPY if unknown)
    """
    return SECTOR_ETFS.get(ticker.upper(), 'SPY')


def load_benchmark_data(ticker: str, period: str = '12mo', end_date: Optional[pd.Timestamp] = None) -> Optional[pd.DataFrame]:
    """
    Load benchmark data (SPY or sector ETF) from Yahoo Finance.
    
    Args:
        ticker: Benchmark symbol
        period: Data period (e.g., '12mo', '6mo')
        end_date: Optional end date for historical analysis
        
    Returns:
        DataFrame with OHLCV data, or None if fetch fails
    """
    try:
        yticker = yf.Ticker(ticker)
        
        if end_date is not None:
            # Historical analysis - fetch up to end_date
            start_date = end_date - pd.DateOffset(months=12)
            df = yticker.history(start=start_date, end=end_date)
        else:
            # Current analysis - fetch recent data
            df = yticker.history(period=period)
        
        if df.empty:
            logger.warning(f"No data returned for {ticker}")
            return None
            
        return df
        
    except Exception as e:
        logger.error(f"Failed to fetch {ticker} data: {e}")
        return None


def check_market_regime(date: Optional[pd.Timestamp] = None) -> Dict:
    """
    Check if SPY is above its 200-day moving average.
    
    Args:
        date: Optional date for historical regime check (None = current)
        
    Returns:
        Dict with regime status and details
    """
    spy_data = load_benchmark_data('SPY', period='12mo', end_date=date)
    
    if spy_data is None or len(spy_data) < 200:
        logger.warning("Insufficient SPY data for regime check")
        return {
            'market_regime_ok': False,
            'reason': 'Insufficient data',
            'spy_close': None,
            'spy_200ma': None
        }
    
    # Calculate 200-day MA
    spy_data['MA200'] = spy_data['Close'].rolling(200).mean()
    
    # Get most recent valid data point
    latest = spy_data.dropna(subset=['MA200']).iloc[-1]
    
    spy_close = latest['Close']
    spy_200ma = latest['MA200']
    regime_ok = spy_close > spy_200ma
    
    return {
        'market_regime_ok': regime_ok,
        'spy_close': spy_close,
        'spy_200ma': spy_200ma,
        'pct_above_ma': ((spy_close / spy_200ma - 1) * 100) if spy_200ma > 0 else 0,
        'date': latest.name
    }


def check_sector_regime(ticker: str, date: Optional[pd.Timestamp] = None) -> Dict:
    """
    Check if sector ETF is above its 50-day moving average.
    
    Args:
        ticker: Stock symbol to determine sector
        date: Optional date for historical regime check (None = current)
        
    Returns:
        Dict with regime status and details
    """
    sector_etf = get_sector_etf(ticker)
    sector_data = load_benchmark_data(sector_etf, period='6mo', end_date=date)
    
    if sector_data is None or len(sector_data) < 50:
        logger.warning(f"Insufficient {sector_etf} data for regime check")
        return {
            'sector_regime_ok': False,
            'reason': 'Insufficient data',
            'sector_etf': sector_etf,
            'sector_close': None,
            'sector_50ma': None
        }
    
    # Calculate 50-day MA
    sector_data['MA50'] = sector_data['Close'].rolling(50).mean()
    
    # Get most recent valid data point
    latest = sector_data.dropna(subset=['MA50']).iloc[-1]
    
    sector_close = latest['Close']
    sector_50ma = latest['MA50']
    regime_ok = sector_close > sector_50ma
    
    return {
        'sector_regime_ok': regime_ok,
        'sector_etf': sector_etf,
        'sector_close': sector_close,
        'sector_50ma': sector_50ma,
        'pct_above_ma': ((sector_close / sector_50ma - 1) * 100) if sector_50ma > 0 else 0,
        'date': latest.name
    }


def get_regime_status(ticker: str, date: Optional[pd.Timestamp] = None) -> Dict:
    """
    Get complete regime status for a ticker.
    
    Checks both market (SPY > 200DMA) and sector (ETF > 50DMA) conditions.
    Entry signals only allowed when BOTH conditions are met.
    
    Args:
        ticker: Stock symbol
        date: Optional date for historical regime check (None = current)
        
    Returns:
        Dict with complete regime analysis
    """
    market = check_market_regime(date)
    sector = check_sector_regime(ticker, date)
    
    overall_ok = market['market_regime_ok'] and sector['sector_regime_ok']
    
    result = {
        'ticker': ticker,
        'overall_regime_ok': overall_ok,
        'market_regime_ok': market['market_regime_ok'],
        'sector_regime_ok': sector['sector_regime_ok'],
        'spy_close': market.get('spy_close'),
        'spy_200ma': market.get('spy_200ma'),
        'spy_pct_above': market.get('pct_above_ma'),
        'sector_etf': sector.get('sector_etf'),
        'sector_close': sector.get('sector_close'),
        'sector_50ma': sector.get('sector_50ma'),
        'sector_pct_above': sector.get('pct_above_ma'),
        'check_date': date if date else pd.Timestamp.now()
    }
    
    # Add failure reasons if regime not ok
    if not overall_ok:
        reasons = []
        if not market['market_regime_ok']:
            reasons.append(f"SPY below 200DMA ({market.get('spy_close', 'N/A'):.2f} < {market.get('spy_200ma', 'N/A'):.2f})")
        if not sector['sector_regime_ok']:
            reasons.append(f"{sector.get('sector_etf')} below 50DMA ({sector.get('sector_close', 'N/A'):.2f} < {sector.get('sector_50ma', 'N/A'):.2f})")
        result['failure_reasons'] = reasons
    
    return result


def apply_regime_filter(df: pd.DataFrame, ticker: str, verbose: bool = False) -> pd.DataFrame:
    """
    Apply regime filter to signal DataFrame.
    
    Creates regime status columns and filters entry signals when regime is not ok.
    Original signals preserved in *_raw columns for analysis.
    
    Args:
        df: DataFrame with signals
        ticker: Stock symbol
        verbose: Print regime status details
        
    Returns:
        DataFrame with regime-filtered signals
    """
    # Get regime status (uses most recent data)
    regime = get_regime_status(ticker)
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"REGIME FILTER - {ticker}")
        print(f"{'='*60}")
        print(f"Market (SPY): {'✅ PASS' if regime['market_regime_ok'] else '❌ FAIL'}")
        if regime.get('spy_close') and regime.get('spy_200ma'):
            print(f"  SPY: ${regime['spy_close']:.2f} vs 200DMA: ${regime['spy_200ma']:.2f} ({regime.get('spy_pct_above', 0):+.2f}%)")
        
        print(f"\nSector ({regime['sector_etf']}): {'✅ PASS' if regime['sector_regime_ok'] else '❌ FAIL'}")
        if regime.get('sector_close') and regime.get('sector_50ma'):
            print(f"  {regime['sector_etf']}: ${regime['sector_close']:.2f} vs 50DMA: ${regime['sector_50ma']:.2f} ({regime.get('sector_pct_above', 0):+.2f}%)")
        
        print(f"\nOVERALL: {'✅ SIGNALS ALLOWED' if regime['overall_regime_ok'] else '❌ SIGNALS BLOCKED'}")
        
        if not regime['overall_regime_ok'] and 'failure_reasons' in regime:
            print("\nFailure Reasons:")
            for reason in regime['failure_reasons']:
                print(f"  • {reason}")
        print(f"{'='*60}\n")
    
    # Add regime status columns to DataFrame
    df['Market_Regime_OK'] = regime['market_regime_ok']
    df['Sector_Regime_OK'] = regime['sector_regime_ok']
    df['Overall_Regime_OK'] = regime['overall_regime_ok']
    
    # Identify entry signal columns
    entry_signals = [col for col in df.columns if any(x in col for x in ['Buy', 'Accumulation', 'Breakout', 'Confluence'])]
    
    # Preserve raw signals and apply filter
    for signal_col in entry_signals:
        if signal_col.endswith('_raw') or signal_col.endswith('_display'):
            continue  # Skip already processed columns
            
        # Create raw signal column
        raw_col = f"{signal_col}_raw"
        if raw_col not in df.columns:
            df[raw_col] = df[signal_col].copy()
        
        # Apply regime filter to entry signals
        # Ensure boolean types for proper AND operation
        signal_bool = df[raw_col].fillna(False).astype(bool)
        df[signal_col] = signal_bool & regime['overall_regime_ok']
    
    return df


def create_regime_summary(ticker: str) -> str:
    """
    Create human-readable regime summary for reports.
    
    Args:
        ticker: Stock symbol
        
    Returns:
        Formatted regime summary string
    """
    regime = get_regime_status(ticker)
    
    summary = []
    summary.append(f"Regime Filter Status for {ticker}:")
    summary.append(f"  Overall: {'✅ PASS' if regime['overall_regime_ok'] else '❌ FAIL'}")
    
    if regime.get('spy_close') and regime.get('spy_200ma'):
        spy_status = '✅' if regime['market_regime_ok'] else '❌'
        summary.append(f"  Market (SPY): {spy_status} ${regime['spy_close']:.2f} vs 200DMA ${regime['spy_200ma']:.2f}")
    
    if regime.get('sector_close') and regime.get('sector_50ma'):
        sector_status = '✅' if regime['sector_regime_ok'] else '❌'
        summary.append(f"  Sector ({regime['sector_etf']}): {sector_status} ${regime['sector_close']:.2f} vs 50DMA ${regime['sector_50ma']:.2f}")
    
    if not regime['overall_regime_ok'] and 'failure_reasons' in regime:
        summary.append("  Failure Reasons:")
        for reason in regime['failure_reasons']:
            summary.append(f"    • {reason}")
    
    return '\n'.join(summary)


if __name__ == '__main__':
    # Test regime filter with sample tickers
    test_tickers = ['AAPL', 'JPM', 'XOM', 'TSLA']
    
    print("\n" + "="*80)
    print("REGIME FILTER TEST")
    print("="*80)
    
    for ticker in test_tickers:
        print(f"\n{create_regime_summary(ticker)}")
        print("-" * 80)
