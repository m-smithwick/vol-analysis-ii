#!/usr/bin/env python3
"""
Generate SPY and Sector ETF Regime Indicators CSV

Creates a comprehensive 24-month history of regime filter calculations to verify
that regime logic is working correctly and not inverted.

Regime Rules:
- Market regime: SPY close > SPY 200-day moving average
- Sector regime: ETF close > ETF 50-day moving average

Author: Volume Analysis System
Date: 2025-11-19
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from data_manager import get_smart_data
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Sector ETFs to analyze
SECTOR_ETFS = [
    'XLK',   # Technology
    'XLF',   # Financials
    'XLV',   # Healthcare
    'XLE',   # Energy
    'XLY',   # Consumer Discretionary
    'XLP',   # Consumer Staples
    'XLI',   # Industrials
    'XLU',   # Utilities
    'XLRE',  # Real Estate
    'XLB',   # Materials
    'XLC'    # Communication Services
]

def calculate_regime_indicators(period='24mo'):
    """
    Calculate regime indicators for SPY and all sector ETFs.
    
    Args:
        period (str): Data period to analyze (default: '24mo')
        
    Returns:
        pd.DataFrame: DataFrame with regime indicators for all symbols
    """
    logger.info(f"Generating regime indicators for {period} period")
    
    # Start with SPY (market regime)
    logger.info("Loading SPY data for market regime calculation...")
    try:
        spy_data = get_smart_data('SPY', period=period, force_refresh=False)
    except Exception as e:
        logger.error(f"Failed to load SPY data: {e}")
        return pd.DataFrame()
    
    if spy_data.empty:
        logger.error("SPY data is empty")
        return pd.DataFrame()
    
    # Calculate SPY 200-day MA and market regime
    spy_data['SPY_200ma'] = spy_data['Close'].rolling(200, min_periods=200).mean()
    spy_data['SPY_market_regime'] = spy_data['Close'] > spy_data['SPY_200ma']
    
    # Create result DataFrame starting with SPY data
    result_df = pd.DataFrame(index=spy_data.index)
    result_df['SPY_close'] = spy_data['Close']
    result_df['SPY_200ma'] = spy_data['SPY_200ma']
    result_df['SPY_market_regime'] = spy_data['SPY_market_regime']
    
    logger.info(f"SPY data loaded: {len(spy_data)} periods from {spy_data.index[0].date()} to {spy_data.index[-1].date()}")
    
    # Process each sector ETF
    for etf in SECTOR_ETFS:
        logger.info(f"Processing {etf}...")
        
        try:
            etf_data = get_smart_data(etf, period=period, force_refresh=False)
            
            if etf_data.empty:
                logger.warning(f"No data available for {etf}")
                # Fill with NaN for missing ETF
                result_df[f'{etf}_close'] = np.nan
                result_df[f'{etf}_50ma'] = np.nan
                result_df[f'{etf}_sector_regime'] = np.nan
                continue
            
            # Calculate 50-day MA and sector regime
            etf_data['50ma'] = etf_data['Close'].rolling(50, min_periods=50).mean()
            etf_data['sector_regime'] = etf_data['Close'] > etf_data['50ma']
            
            # Align with SPY dates and add to result
            etf_aligned = etf_data.reindex(result_df.index, method='ffill')
            
            result_df[f'{etf}_close'] = etf_aligned['Close']
            result_df[f'{etf}_50ma'] = etf_aligned['50ma']
            result_df[f'{etf}_sector_regime'] = etf_aligned['sector_regime']
            
            logger.info(f"{etf} processed: {len(etf_data)} periods from {etf_data.index[0].date()} to {etf_data.index[-1].date()}")
            
        except Exception as e:
            logger.error(f"Failed to process {etf}: {e}")
            # Fill with NaN for failed ETF
            result_df[f'{etf}_close'] = np.nan
            result_df[f'{etf}_50ma'] = np.nan
            result_df[f'{etf}_sector_regime'] = np.nan
    
    # Remove rows where SPY data is incomplete (before 200-day MA is available)
    result_df = result_df.dropna(subset=['SPY_200ma'])
    
    logger.info(f"Final dataset: {len(result_df)} complete periods")
    return result_df

def generate_summary_stats(df):
    """
    Generate summary statistics for regime indicators.
    
    Args:
        df (pd.DataFrame): Regime indicators DataFrame
        
    Returns:
        dict: Summary statistics
    """
    if df.empty:
        return {}
    
    stats = {
        'total_periods': len(df),
        'date_range': f"{df.index[0].date()} to {df.index[-1].date()}",
        'spy_regime_pass_rate': df['SPY_market_regime'].mean() * 100 if 'SPY_market_regime' in df.columns else 0
    }
    
    # Calculate pass rates for each ETF
    etf_stats = {}
    for etf in SECTOR_ETFS:
        regime_col = f'{etf}_sector_regime'
        if regime_col in df.columns:
            pass_rate = df[regime_col].mean() * 100
            etf_stats[etf] = pass_rate
        else:
            etf_stats[etf] = 0
    
    stats['etf_regime_pass_rates'] = etf_stats
    
    return stats

def main():
    """Main function to generate regime indicators CSV."""
    print("\n" + "="*80)
    print("SPY AND SECTOR ETF REGIME INDICATORS GENERATOR")
    print("="*80)
    
    # Generate regime indicators
    regime_df = calculate_regime_indicators('24mo')
    
    if regime_df.empty:
        print("❌ Failed to generate regime indicators - no data available")
        return
    
    # Generate summary statistics
    stats = generate_summary_stats(regime_df)
    
    # Export to CSV
    output_file = 'regime_indicators_24mo.csv'
    try:
        regime_df.to_csv(output_file)
        logger.info(f"Regime indicators exported to {output_file}")
        print(f"\n✅ Successfully exported to {output_file}")
    except Exception as e:
        logger.error(f"Failed to export CSV: {e}")
        print(f"❌ Failed to export CSV: {e}")
        return
    
    # Display summary
    print(f"\n📊 SUMMARY STATISTICS")
    print("-" * 50)
    print(f"Total periods: {stats.get('total_periods', 0):,}")
    print(f"Date range: {stats.get('date_range', 'N/A')}")
    print(f"SPY market regime pass rate: {stats.get('spy_regime_pass_rate', 0):.1f}%")
    
    print(f"\n📈 SECTOR ETF REGIME PASS RATES:")
    etf_rates = stats.get('etf_regime_pass_rates', {})
    for etf in SECTOR_ETFS:
        rate = etf_rates.get(etf, 0)
        status = "✅" if rate > 0 else "❌"
        print(f"  {etf}: {status} {rate:.1f}%")
    
    # Show recent regime status (last 10 days)
    print(f"\n🔍 RECENT REGIME STATUS (Last 10 Days):")
    recent_df = regime_df.tail(10)
    
    for idx, row in recent_df.iterrows():
        date_str = idx.strftime('%Y-%m-%d')
        spy_regime = "✅" if row.get('SPY_market_regime', False) else "❌"
        
        # Count passing ETFs
        etf_passing = 0
        for etf in SECTOR_ETFS:
            regime_col = f'{etf}_sector_regime'
            if regime_col in row and row[regime_col]:
                etf_passing += 1
        
        print(f"  {date_str}: SPY {spy_regime} | ETFs: {etf_passing}/{len(SECTOR_ETFS)} passing")
    
    print(f"\n📁 File saved: {output_file}")
    print("="*80)

if __name__ == '__main__':
    main()
