"""
Momentum Ignition Screening Engine

Identifies momentum candidates using:
1. Relative Strength Velocity (RS ratio slope acceleration)
2. Volatility Contraction Pattern (VCP)
3. Trend confirmation (200-day SMA)
4. Liquidity filters (minimum volume)

Uses local cache only - no external API calls.
"""

from typing import List, Dict, Optional, Tuple
import pandas as pd
import numpy as np
from scipy import stats
from datetime import datetime, timedelta
import argparse
import sys
from pathlib import Path

# Import existing infrastructure
from data_manager import get_smart_data, read_ticker_file
from error_handler import (
    ErrorContext, DataValidationError, CacheError,
    setup_logging, logger
)

# Configure logging
setup_logging()


class MomentumScreener:
    """
    Vectorized momentum screening engine for large ticker universes.
    
    Implements:
    - RS Velocity: Linear regression slopes of RS ratio (10d and 50d)
    - VCP Detection: Volatility contraction patterns
    - Trend & Liquidity: Price > 200 SMA, Volume > 500k
    """
    
    def __init__(self, lookback_days: int = 365):
        """
        Initialize screener.
        
        Args:
            lookback_days (int): Days of historical data to load (min 250 for 200-day SMA)
        """
        self.lookback_days = max(lookback_days, 250)  # Ensure minimum for calculations
        self.benchmark_data: Optional[pd.DataFrame] = None
        self.ticker_data: Dict[str, pd.DataFrame] = {}
        
    def load_data(self, tickers: List[str], benchmark: str = "SPY") -> Dict[str, pd.DataFrame]:
        """
        Load data from local cache for all tickers and benchmark.
        
        Args:
            tickers (List[str]): List of ticker symbols to screen
            benchmark (str): Benchmark ticker for relative strength (default: SPY)
            
        Returns:
            Dict[str, pd.DataFrame]: Successfully loaded ticker data
        """
        with ErrorContext("loading screening data"):
            logger.info(f"📁 Loading {len(tickers)} tickers from cache (lookback: {self.lookback_days} days)")
            
            # Load benchmark first
            try:
                self.benchmark_data = get_smart_data(
                    ticker=benchmark,
                    period=f"{self.lookback_days}d",
                    cache_only=True
                )
                logger.info(f"📊 Benchmark {benchmark}: {len(self.benchmark_data)} periods loaded")
            except CacheError as e:
                logger.error(f"❌ Failed to load benchmark {benchmark}: {e}")
                logger.error(f"   Run: python populate_cache.py {benchmark} --period 24mo")
                raise
            
            # Load all tickers
            loaded = 0
            failed = 0
            
            for ticker in tickers:
                try:
                    df = get_smart_data(
                        ticker=ticker,
                        period=f"{self.lookback_days}d",
                        cache_only=True
                    )
                    
                    # Validate minimum data requirements
                    if len(df) < 200:
                        logger.warning(f"⚠️  {ticker}: Insufficient data ({len(df)} periods, need 200+)")
                        failed += 1
                        continue
                    
                    self.ticker_data[ticker] = df
                    loaded += 1
                    
                except CacheError as e:
                    logger.warning(f"⚠️  {ticker}: Not in cache - {e}")
                    failed += 1
                except Exception as e:
                    logger.warning(f"⚠️  {ticker}: Load error - {e}")
                    failed += 1
            
            logger.info(f"✅ Loaded {loaded} tickers successfully ({failed} failed/skipped)")
            
            if loaded == 0:
                raise DataValidationError("No tickers loaded successfully. Check cache population.")
            
            return self.ticker_data
    
    def apply_velvet_rope_filter(self, ticker: str, df: pd.DataFrame) -> Tuple[bool, Dict]:
        """
        Apply "Velvet Rope" institutional quality filter.
        
        Filters OUT low-quality stocks BEFORE expensive calculations:
        1. Price Floor: Close >= $15 (no penny stocks)
        2. Dollar Volume: 20d avg >= $20M (institutional liquidity)
        3. Trend Alignment: Price > 200 SMA AND 200 SMA rising
        4. Volatility Cap: ADR_20 <= 6% (reject choppy stocks)
        
        Args:
            ticker (str): Ticker symbol
            df (pd.DataFrame): Stock OHLCV data
            
        Returns:
            Tuple[bool, Dict]: (passes_filter, metrics_dict)
        """
        with ErrorContext("applying velvet rope filter", ticker=ticker):
            try:
                # 1. Price Floor
                current_price = df['Close'].iloc[-1]
                if current_price < 15.0:
                    return False, {'filter_failed': 'price_floor', 'price': current_price}
                
                # 2. Institutional Liquidity (Dollar Volume)
                dollar_volume = df['Close'] * df['Volume']
                avg_dollar_vol_20d = dollar_volume.rolling(window=20).mean().iloc[-1]
                
                if np.isnan(avg_dollar_vol_20d) or avg_dollar_vol_20d < 20_000_000:
                    return False, {
                        'filter_failed': 'dollar_volume',
                        'dollar_vol_20d': avg_dollar_vol_20d if not np.isnan(avg_dollar_vol_20d) else 0
                    }
                
                # 3. Trend Alignment (Price > 200 SMA AND 200 SMA rising)
                sma_200 = df['Close'].rolling(window=200).mean()
                current_sma = sma_200.iloc[-1]
                
                if np.isnan(current_sma):
                    return False, {'filter_failed': 'insufficient_data'}
                
                # Check if price above 200 SMA
                if current_price <= current_sma:
                    return False, {
                        'filter_failed': 'trend_alignment',
                        'reason': 'price_below_sma'
                    }
                
                # Check if 200 SMA is rising (current > 20 days ago)
                if len(sma_200) >= 20:
                    sma_20d_ago = sma_200.iloc[-20]
                    if current_sma <= sma_20d_ago:
                        return False, {
                            'filter_failed': 'trend_alignment',
                            'reason': 'sma_not_rising'
                        }
                
                # 4. Volatility Cap (ADR <= 6%)
                daily_range_pct = (df['High'] - df['Low']) / df['Close']
                adr_20 = daily_range_pct.rolling(window=20).mean().iloc[-1]
                
                if np.isnan(adr_20) or adr_20 > 0.06:
                    return False, {
                        'filter_failed': 'volatility_cap',
                        'adr_20': adr_20 if not np.isnan(adr_20) else 0
                    }
                
                # Passed all filters!
                return True, {
                    'price': current_price,
                    'dollar_vol_20d': avg_dollar_vol_20d,
                    'sma_200': current_sma,
                    'sma_slope': current_sma - sma_20d_ago if len(sma_200) >= 20 else np.nan,
                    'adr_20': adr_20
                }
                
            except Exception as e:
                logger.warning(f"{ticker}: Velvet Rope filter error - {e}")
                return False, {'filter_failed': 'error', 'error': str(e)}
    
    def calculate_rs_velocity(self, ticker: str, df: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate Relative Strength Velocity metrics.
        
        RS Velocity measures acceleration in relative strength:
        - RS_Ratio = Stock Close / Benchmark Close
        - Slope_10d = Linear regression slope of RS_Ratio over 10 days
        - Slope_50d = Linear regression slope of RS_Ratio over 50 days
        - Velocity_Increasing = Slope_10d > Slope_50d (acceleration)
        
        Args:
            ticker (str): Ticker symbol
            df (pd.DataFrame): Stock OHLCV data
            
        Returns:
            Dict with RS velocity metrics
        """
        with ErrorContext("calculating RS velocity", ticker=ticker):
            # Align dates between stock and benchmark
            common_dates = df.index.intersection(self.benchmark_data.index)
            
            if len(common_dates) < 50:
                logger.warning(f"{ticker}: Insufficient overlapping dates with benchmark")
                return {
                    'rs_slope_10d': np.nan,
                    'rs_slope_50d': np.nan,
                    'velocity_increasing': False
                }
            
            # Calculate RS Ratio
            stock_close = df.loc[common_dates, 'Close']
            benchmark_close = self.benchmark_data.loc[common_dates, 'Close']
            rs_ratio = stock_close / benchmark_close
            
            # Calculate slopes using linear regression
            # Convert to numeric index for regression
            x = np.arange(len(rs_ratio))
            y = rs_ratio.values
            
            # 10-day slope (most recent 10 periods)
            if len(rs_ratio) >= 10:
                slope_10d, _, _, _, _ = stats.linregress(x[-10:], y[-10:])
            else:
                slope_10d = np.nan
            
            # 50-day slope (most recent 50 periods)
            if len(rs_ratio) >= 50:
                slope_50d, _, _, _, _ = stats.linregress(x[-50:], y[-50:])
            else:
                slope_50d = np.nan
            
            # Check if velocity is increasing (short-term slope > long-term slope)
            velocity_increasing = slope_10d > slope_50d if not (np.isnan(slope_10d) or np.isnan(slope_50d)) else False
            
            return {
                'rs_slope_10d': slope_10d,
                'rs_slope_50d': slope_50d,
                'velocity_increasing': velocity_increasing,
                'current_rs_ratio': rs_ratio.iloc[-1] if len(rs_ratio) > 0 else np.nan
            }
    
    def detect_vcp(self, ticker: str, df: pd.DataFrame) -> Dict[str, float]:
        """
        Detect Volatility Contraction Pattern (VCP).
        
        VCP occurs when current volatility is significantly lower than recent average:
        - Norm_Range = (High - Low) / Close
        - Avg_Range_20 = 20-day SMA of Norm_Range
        - VCP_Active = Current_Norm_Range < 0.5 * Avg_Range_20
        
        Args:
            ticker (str): Ticker symbol
            df (pd.DataFrame): Stock OHLCV data
            
        Returns:
            Dict with VCP metrics
        """
        with ErrorContext("detecting VCP", ticker=ticker):
            # Calculate normalized range
            norm_range = (df['High'] - df['Low']) / df['Close']
            
            # Calculate 20-day average range
            avg_range_20 = norm_range.rolling(window=20).mean()
            
            # Get current values
            current_norm_range = norm_range.iloc[-1]
            current_avg_range = avg_range_20.iloc[-1]
            
            # VCP condition: current range < 50% of average range
            vcp_active = current_norm_range < (0.5 * current_avg_range) if not np.isnan(current_avg_range) else False
            
            return {
                'current_norm_range': current_norm_range,
                'avg_range_20d': current_avg_range,
                'vcp_active': vcp_active,
                'contraction_ratio': current_norm_range / current_avg_range if current_avg_range > 0 else np.nan
            }
    
    def apply_trend_liquidity_filters(self, ticker: str, df: pd.DataFrame) -> Dict[str, float]:
        """
        Apply trend and liquidity filters.
        
        Filters:
        - Price > 200-day SMA (trend confirmation)
        - 20-day Avg Volume > 500,000 (liquidity requirement)
        
        Args:
            ticker (str): Ticker symbol
            df (pd.DataFrame): Stock OHLCV data
            
        Returns:
            Dict with filter metrics
        """
        with ErrorContext("applying filters", ticker=ticker):
            # Calculate 200-day SMA
            sma_200 = df['Close'].rolling(window=200).mean()
            current_price = df['Close'].iloc[-1]
            current_sma_200 = sma_200.iloc[-1]
            
            above_200sma = current_price > current_sma_200 if not np.isnan(current_sma_200) else False
            
            # Calculate 20-day average volume
            avg_volume_20 = df['Volume'].rolling(window=20).mean().iloc[-1]
            
            liquidity_ok = avg_volume_20 > 500_000 if not np.isnan(avg_volume_20) else False
            
            return {
                'current_price': current_price,
                'sma_200': current_sma_200,
                'above_200sma': above_200sma,
                'price_vs_sma_pct': ((current_price / current_sma_200) - 1) * 100 if not np.isnan(current_sma_200) else np.nan,
                'avg_volume_20d': avg_volume_20,
                'liquidity_ok': liquidity_ok
            }
    
    def screen_ticker(self, ticker: str) -> Optional[Dict]:
        """
        Run complete screening process on a single ticker.
        
        Args:
            ticker (str): Ticker symbol
            
        Returns:
            Dict with all screening metrics, or None if processing failed
        """
        if ticker not in self.ticker_data:
            logger.warning(f"{ticker}: No data available")
            return None
        
        df = self.ticker_data[ticker]
        
        try:
            # Calculate all metrics
            rs_metrics = self.calculate_rs_velocity(ticker, df)
            vcp_metrics = self.detect_vcp(ticker, df)
            filter_metrics = self.apply_trend_liquidity_filters(ticker, df)
            
            # Combine all metrics
            result = {
                'ticker': ticker,
                **rs_metrics,
                **vcp_metrics,
                **filter_metrics
            }
            
            # Determine if passes all filters
            result['passes_all_filters'] = (
                result['velocity_increasing'] and
                result['vcp_active'] and
                result['above_200sma'] and
                result['liquidity_ok']
            )
            
            return result
            
        except Exception as e:
            logger.warning(f"⚠️  {ticker}: Screening error - {e}")
            return None
    
    def run_screen(self, tickers: List[str]) -> pd.DataFrame:
        """
        Run two-stage screening on all tickers.
        
        Stage 1: Velvet Rope Filter (fast, institutional quality)
        Stage 2: Momentum Calculations (expensive, only on survivors)
        
        Args:
            tickers (List[str]): List of tickers to screen
            
        Returns:
            pd.DataFrame: Screening results sorted by RS velocity
        """
        logger.info(f"🚪 STAGE 1: Velvet Rope Filter ({len(tickers)} tickers)")
        logger.info(f"   Filtering for institutional quality...")
        
        # Stage 1: Apply Velvet Rope filter to all tickers
        survivors = {}
        filter_stats = {
            'price_floor': 0,
            'dollar_volume': 0,
            'trend_alignment': 0,
            'volatility_cap': 0,
            'insufficient_data': 0,
            'error': 0
        }
        
        for i, ticker in enumerate(tickers, 1):
            if i % 50 == 0:
                logger.info(f"   Filtering: {i}/{len(tickers)}")
            
            if ticker not in self.ticker_data:
                continue
            
            df = self.ticker_data[ticker]
            passes, metrics = self.apply_velvet_rope_filter(ticker, df)
            
            if passes:
                survivors[ticker] = metrics
            else:
                # Track rejection reason
                reason = metrics.get('filter_failed', 'unknown')
                if reason in filter_stats:
                    filter_stats[reason] += 1
        
        # Log Velvet Rope results
        total_filtered = sum(filter_stats.values())
        survivors_count = len(survivors)
        pass_rate = (survivors_count / len(tickers) * 100) if len(tickers) > 0 else 0
        
        logger.info(f"")
        logger.info(f"🎯 Velvet Rope Results:")
        logger.info(f"   Survivors: {survivors_count}/{len(tickers)} ({pass_rate:.1f}%)")
        logger.info(f"   Filtered out: {total_filtered}")
        if total_filtered > 0:
            logger.info(f"   Rejection breakdown:")
            for reason, count in sorted(filter_stats.items(), key=lambda x: x[1], reverse=True):
                if count > 0:
                    pct = (count / total_filtered * 100)
                    logger.info(f"     - {reason}: {count} ({pct:.1f}%)")
        logger.info(f"")
        
        if survivors_count == 0:
            logger.error("❌ No tickers passed Velvet Rope filter")
            return pd.DataFrame()
        
        # Stage 2: Run expensive momentum calculations on survivors only
        logger.info(f"⚙️  STAGE 2: Momentum Screening ({survivors_count} survivors)")
        logger.info(f"   Running RS Velocity and VCP calculations...")
        
        results = []
        for i, ticker in enumerate(survivors.keys(), 1):
            if i % 10 == 0 or i == survivors_count:
                logger.info(f"   Progress: {i}/{survivors_count} tickers processed")
            
            result = self.screen_ticker(ticker)
            if result:
                # Add Velvet Rope metrics to result
                result['velvet_rope_passed'] = True
                result['dollar_vol_20d'] = survivors[ticker].get('dollar_vol_20d', np.nan)
                result['adr_20'] = survivors[ticker].get('adr_20', np.nan)
                results.append(result)
        
        if not results:
            logger.error("❌ No tickers successfully completed momentum screening")
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame(results)
        
        # Sort by RS slope (descending) - strongest momentum first
        df = df.sort_values('rs_slope_10d', ascending=False)
        
        # Log final summary
        total_screened = len(df)
        passed_all = df['passes_all_filters'].sum()
        logger.info(f"")
        logger.info(f"✅ Final Results: {passed_all} of {total_screened} passed all momentum filters")
        logger.info(f"   Pass rate: {passed_all/total_screened*100:.1f}%")
        
        return df


def format_results_table(df: pd.DataFrame, top_n: int = 20) -> str:
    """
    Format results as readable console table.
    
    Args:
        df (pd.DataFrame): Results dataframe
        top_n (int): Number of top results to display
        
    Returns:
        str: Formatted table
    """
    if df.empty:
        return "No results to display"
    
    # Filter to top candidates
    display_df = df.head(top_n).copy()
    
    # Format for display
    display_df['RS_10d'] = display_df['rs_slope_10d'].apply(lambda x: f"{x:.6f}" if not np.isnan(x) else "N/A")
    display_df['RS_50d'] = display_df['rs_slope_50d'].apply(lambda x: f"{x:.6f}" if not np.isnan(x) else "N/A")
    display_df['P/SMA%'] = display_df['price_vs_sma_pct'].apply(lambda x: f"{x:+.1f}%" if not np.isnan(x) else "N/A")
    display_df['Vol_20d'] = display_df['avg_volume_20d'].apply(lambda x: f"{x/1e6:.2f}M" if not np.isnan(x) else "N/A")
    display_df['VCP'] = display_df['vcp_active'].apply(lambda x: "✓" if x else "✗")
    display_df['Vel↑'] = display_df['velocity_increasing'].apply(lambda x: "✓" if x else "✗")
    display_df['Pass'] = display_df['passes_all_filters'].apply(lambda x: "✅" if x else "")
    
    # Select columns for display
    cols = ['ticker', 'RS_10d', 'RS_50d', 'Vel↑', 'VCP', 'P/SMA%', 'Vol_20d', 'Pass']
    display_table = display_df[cols]
    
    return display_table.to_string(index=False)


def export_results(df: pd.DataFrame, output_path: Optional[str] = None) -> str:
    """
    Export results to CSV file.
    
    Args:
        df (pd.DataFrame): Results dataframe
        output_path (str, optional): Output file path. If None, auto-generates timestamp filename.
        
    Returns:
        str: Path to exported file
    """
    if output_path is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = f"momentum_results_{timestamp}.csv"
    
    # Reorder columns for readability
    col_order = [
        'ticker', 'passes_all_filters',
        'rs_slope_10d', 'rs_slope_50d', 'velocity_increasing', 'current_rs_ratio',
        'vcp_active', 'current_norm_range', 'avg_range_20d', 'contraction_ratio',
        'current_price', 'sma_200', 'above_200sma', 'price_vs_sma_pct',
        'avg_volume_20d', 'liquidity_ok'
    ]
    
    # Only include columns that exist
    export_cols = [col for col in col_order if col in df.columns]
    export_df = df[export_cols]
    
    export_df.to_csv(output_path, index=False)
    logger.info(f"📄 Results exported to: {output_path}")
    
    return output_path


def main():
    """CLI entry point for momentum screening."""
    parser = argparse.ArgumentParser(
        description="Momentum Ignition Screening Engine - Identify RS Velocity + VCP candidates",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Screen 4 tickers (quick test)
  python momentum_screener.py --file ticker_lists/short.txt
  
  # Screen 20 tickers with 18 months lookback
  python momentum_screener.py --file ticker_lists/ibd20.txt --period 18mo
  
  # Screen S&P 100 with custom output
  python momentum_screener.py --file ticker_lists/sp100.txt --output sp100_momentum.csv
  
  # Quick check on single ticker
  python momentum_screener.py --tickers AAPL MSFT GOOGL

Note: All tickers must be in local cache. Run populate_cache.py first if needed.
        """
    )
    
    # Input options
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        '--file',
        type=str,
        help='Path to file containing tickers (one per line)'
    )
    input_group.add_argument(
        '--tickers',
        type=str,
        nargs='+',
        help='Space-separated list of tickers'
    )
    
    # Screening parameters
    parser.add_argument(
        '--period',
        type=str,
        default='12mo',
        help='Lookback period (default: 12mo, minimum 250 days for 200-SMA)'
    )
    parser.add_argument(
        '--benchmark',
        type=str,
        default='SPY',
        help='Benchmark ticker for relative strength (default: SPY)'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Output CSV file path (default: auto-generated timestamp)'
    )
    parser.add_argument(
        '--top',
        type=int,
        default=20,
        help='Number of top results to display (default: 20)'
    )
    
    args = parser.parse_args()
    
    # Get ticker list
    if args.file:
        tickers = read_ticker_file(args.file)
        logger.info(f"📁 Loaded {len(tickers)} tickers from {args.file}")
    else:
        tickers = [t.upper() for t in args.tickers]
        logger.info(f"📁 Processing {len(tickers)} tickers from command line")
    
    # Convert period to days
    period_map = {
        '6mo': 180, '12mo': 365, '18mo': 545, '24mo': 730, '36mo': 1095
    }
    lookback_days = period_map.get(args.period, 365)
    
    # Initialize screener
    logger.info(f"🔍 Momentum Ignition Screening Engine")
    logger.info(f"   Benchmark: {args.benchmark}")
    logger.info(f"   Lookback: {args.period} ({lookback_days} days)")
    logger.info("")
    
    screener = MomentumScreener(lookback_days=lookback_days)
    
    # Load data
    try:
        screener.load_data(tickers, benchmark=args.benchmark)
    except Exception as e:
        logger.error(f"❌ Failed to load data: {e}")
        sys.exit(1)
    
    # Run screening
    results = screener.run_screen(list(screener.ticker_data.keys()))
    
    if results.empty:
        logger.error("❌ No results generated")
        sys.exit(1)
    
    # Display results
    print("\n" + "="*80)
    print("TOP MOMENTUM CANDIDATES")
    print("="*80)
    print(format_results_table(results, top_n=args.top))
    print("="*80)
    
    # Export to CSV
    output_file = export_results(results, args.output)
    
    # Summary statistics
    total = len(results)
    passed = results['passes_all_filters'].sum()
    print(f"\n📊 Summary:")
    print(f"   Total screened: {total}")
    print(f"   Passed filters: {passed} ({passed/total*100:.1f}%)")
    print(f"   Top RS_10d: {results['rs_slope_10d'].max():.6f}")
    print(f"   Results saved: {output_file}")


if __name__ == "__main__":
    main()
