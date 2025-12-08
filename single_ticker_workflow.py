#!/usr/bin/env python3
"""
Single Ticker Complete Workflow Script

This script provides a streamlined workflow for analyzing a single stock ticker:
1. Populate cache from massive_cache (DuckDB fast mode)
2. Run volume analysis with signal generation
3. Execute risk-managed backtest
4. Generate interactive HTML chart
5. Save all outputs to organized directory

Usage:
    python single_ticker_workflow.py AAPL
    python single_ticker_workflow.py NVDA --months 36
    python single_ticker_workflow.py TSLA --config configs/aggressive_config.yaml
    python single_ticker_workflow.py MSFT --skip-cache --account-value 50000
"""

import argparse
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Import cache population
from populate_cache_bulk import populate_cache_bulk_duckdb

# Import analysis components
from analysis_service import prepare_analysis_dataframe
from config_loader import load_config, ConfigValidationError

# Import backtesting
from backtest import run_risk_managed_backtest

# Import chart generation
import chart_builder_plotly


def print_header(title: str):
    """Print a formatted section header."""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")


def print_step(step_num: int, total_steps: int, description: str):
    """Print a formatted step indicator."""
    print(f"[{step_num}/{total_steps}] {description}...")


def populate_ticker_cache(ticker: str, months: int, skip_cache: bool = False) -> bool:
    """
    Populate cache for a single ticker.
    
    Args:
        ticker: Stock symbol
        months: Number of months of history
        skip_cache: Skip if cache already has some data
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Check if we should skip cache population
        if skip_cache:
            cache_file = Path('data_cache') / f"{ticker}_1d_data.csv"
            if cache_file.exists():
                print(f"   Cache file exists, skipping population (--skip-cache)")
                return True
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=months * 30)
        
        print(f"   Fetching {months} months of data ({start_date.date()} to {end_date.date()})")
        print(f"   Using DuckDB fast mode for optimal performance...")
        
        # Use DuckDB fast mode
        stats = populate_cache_bulk_duckdb(
            tickers={ticker},
            start_date=start_date,
            end_date=end_date
        )
        
        if stats is None:
            print(f"   ❌ Cache population failed (DuckDB index may be missing)")
            print(f"   Build index first: python scripts/build_massive_index.py")
            return False
        
        if stats['tickers_added'] > 0 or stats['tickers_skipped'] > 0:
            print(f"   ✅ Cache populated: {stats['total_records_added']} records added")
            return True
        else:
            print(f"   ⚠️  No data found for {ticker}")
            return False
            
    except Exception as e:
        print(f"   ❌ Cache population error: {e}")
        return False


def run_analysis(ticker: str, period: str, config_path: str = None) -> tuple:
    """
    Run volume analysis and generate signals.
    
    Args:
        ticker: Stock symbol
        period: Analysis period (e.g., '24mo')
        config_path: Optional config file path
        
    Returns:
        tuple: (df, config_dict) or (None, None) on failure
    """
    try:
        # Load config if provided
        config_dict = None
        if config_path:
            print(f"   Loading configuration: {config_path}")
            config_loader = load_config(config_path)
            config_dict = config_loader.config
            print(f"   Using threshold: {config_dict['signal_thresholds']['entry']['moderate_buy_pullback']:.1f} for Moderate Buy")
        
        print(f"   Analyzing {ticker} for {period} period...")
        print(f"   Generating signals and indicators...")
        
        # Run analysis
        df = prepare_analysis_dataframe(
            ticker,
            period,
            data_source='yfinance',
            force_refresh=False,
            cache_only=True,
            verbose=False,
            config=config_dict
        )
        
        # Check for signals
        entry_signals = ['Strong_Buy', 'Moderate_Buy', 'Stealth_Accumulation', 
                        'Confluence_Signal', 'Volume_Breakout']
        total_signals = sum(df[sig].sum() for sig in entry_signals)
        
        print(f"   ✅ Analysis complete: {len(df)} days, {total_signals} entry signals")
        return df, config_dict
        
    except Exception as e:
        print(f"   ❌ Analysis error: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def run_backtest_analysis(df, ticker: str, account_value: float, risk_pct: float,
                         output_dir: Path, config_dict: dict = None) -> bool:
    """
    Run risk-managed backtest and save report.
    
    Args:
        df: Analysis DataFrame
        ticker: Stock symbol
        account_value: Account value for position sizing
        risk_pct: Risk percentage per trade
        output_dir: Directory to save output
        config_dict: Optional config dictionary
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        print(f"   Running risk-managed backtest...")
        print(f"   Account: ${account_value:,.0f}, Risk: {risk_pct}% per trade")
        
        # Extract transaction costs from config if available
        transaction_costs = None
        if config_dict and 'transaction_costs' in config_dict:
            transaction_costs = config_dict['transaction_costs']
            print(f"   Using transaction costs from config")
        
        # Extract stop strategy from config if available
        stop_strategy = 'vol_regime'  # Default
        time_stop_bars = 12  # Default
        if config_dict and 'risk_management' in config_dict:
            stop_strategy = config_dict['risk_management'].get('stop_loss_strategy', 'vol_regime')
            time_stop_bars = config_dict['risk_management'].get('time_stop_bars', 12)
            print(f"   Using stop strategy: {stop_strategy} (time stop: {time_stop_bars} bars)")
        
        # Run backtest
        result = run_risk_managed_backtest(
            df=df,
            ticker=ticker,
            account_value=account_value,
            risk_pct=risk_pct,
            stop_strategy=stop_strategy,
            time_stop_bars=time_stop_bars,
            transaction_costs=transaction_costs,
            save_to_file=True,
            output_dir=str(output_dir),
            verbose=False
        )
        
        if result and result['trades']:
            num_trades = len(result['trades'])
            analysis = result['analysis']
            print(f"   ✅ Backtest complete: {num_trades} trades, {analysis.get('Win Rate', 'N/A')} win rate")
            return True
        else:
            print(f"   ⚠️  No trades generated in backtest")
            return True  # Not an error, just no trades
            
    except Exception as e:
        print(f"   ❌ Backtest error: {e}")
        import traceback
        traceback.print_exc()
        return False


def generate_chart(df, ticker: str, period: str, output_dir: Path) -> bool:
    """
    Generate interactive HTML chart.
    
    Args:
        df: Analysis DataFrame
        ticker: Stock symbol
        period: Analysis period
        output_dir: Directory to save chart
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        print(f"   Generating interactive HTML chart...")
        
        # Generate filename with date range
        start_date = df.index[0].strftime('%Y%m%d')
        end_date = df.index[-1].strftime('%Y%m%d')
        chart_filename = f"{ticker}_{period}_{start_date}_{end_date}_chart.html"
        chart_path = output_dir / chart_filename
        
        # Generate chart
        chart_builder_plotly.generate_analysis_chart(
            df=df,
            ticker=ticker,
            period=period,
            save_path=str(chart_path),
            show=False
        )
        
        print(f"   ✅ Chart saved: {chart_filename}")
        return True
        
    except Exception as e:
        print(f"   ❌ Chart generation error: {e}")
        import traceback
        traceback.print_exc()
        return False


def save_analysis_summary(df, ticker: str, period: str, output_dir: Path) -> bool:
    """
    Save text analysis summary.
    
    Args:
        df: Analysis DataFrame
        ticker: Stock symbol
        period: Analysis period
        output_dir: Directory to save summary
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        from vol_analysis import generate_analysis_text
        
        # Generate filename with date range
        start_date = df.index[0].strftime('%Y%m%d')
        end_date = df.index[-1].strftime('%Y%m%d')
        summary_filename = f"{ticker}_{period}_{start_date}_{end_date}_analysis.txt"
        summary_path = output_dir / summary_filename
        
        # Generate and save analysis text
        analysis_text = generate_analysis_text(ticker, df, period)
        
        with open(summary_path, 'w') as f:
            f.write(analysis_text)
        
        print(f"   ✅ Analysis saved: {summary_filename}")
        return True
        
    except Exception as e:
        print(f"   ❌ Analysis save error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Complete single-ticker analysis workflow',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage (24 months, default config)
  python single_ticker_workflow.py AAPL
  
  # Custom time period
  python single_ticker_workflow.py NVDA --months 36
  
  # With specific config
  python single_ticker_workflow.py TSLA --config configs/aggressive_config.yaml
  
  # Skip cache if already populated
  python single_ticker_workflow.py MSFT --skip-cache
  
  # Custom account parameters
  python single_ticker_workflow.py GOOGL --account-value 50000 --risk-pct 1.0

Workflow Steps:
  1. Populate cache from massive_cache (DuckDB fast mode)
  2. Run volume analysis with signal generation
  3. Execute risk-managed backtest
  4. Generate interactive HTML chart
  5. Save analysis summary
        """
    )
    
    parser.add_argument(
        'ticker',
        help='Stock ticker symbol (e.g., AAPL, NVDA, TSLA)'
    )
    
    parser.add_argument(
        '--months',
        type=int,
        default=24,
        help='Number of months of history to analyze (default: 24)'
    )
    
    parser.add_argument(
        '--config',
        help='Path to YAML configuration file (optional)'
    )
    
    parser.add_argument(
        '--output-dir',
        default='results',
        help='Output directory for all results (default: results)'
    )
    
    parser.add_argument(
        '--skip-cache',
        action='store_true',
        help='Skip cache population if data already exists'
    )
    
    parser.add_argument(
        '--account-value',
        type=float,
        default=100000,
        help='Account value for position sizing (default: 100000)'
    )
    
    parser.add_argument(
        '--risk-pct',
        type=float,
        default=0.75,
        help='Risk percentage per trade (default: 0.75)'
    )
    
    args = parser.parse_args()
    
    # Validate ticker
    ticker = args.ticker.upper()
    
    # Create output directory
    ticker_output_dir = Path(args.output_dir) / ticker
    ticker_output_dir.mkdir(parents=True, exist_ok=True)
    
    # Print workflow header
    print_header(f"SINGLE TICKER WORKFLOW: {ticker}")
    print(f"📊 Ticker: {ticker}")
    print(f"📅 Period: {args.months} months")
    print(f"💰 Account: ${args.account_value:,.0f}")
    print(f"⚠️  Risk: {args.risk_pct}% per trade")
    if args.config:
        print(f"⚙️  Config: {args.config}")
    print(f"📁 Output: {ticker_output_dir}")
    print()
    
    total_steps = 5
    success_count = 0
    
    # Step 1: Populate cache
    print_step(1, total_steps, "Populating cache")
    if populate_ticker_cache(ticker, args.months, args.skip_cache):
        success_count += 1
    else:
        print("\n❌ Cache population failed. Cannot continue.")
        sys.exit(1)
    
    # Step 2: Run analysis
    print_step(2, total_steps, "Running volume analysis")
    df, config_dict = run_analysis(ticker, f"{args.months}mo", args.config)
    if df is not None:
        success_count += 1
    else:
        print("\n❌ Analysis failed. Cannot continue.")
        sys.exit(1)
    
    # Step 3: Run backtest
    print_step(3, total_steps, "Executing risk-managed backtest")
    if run_backtest_analysis(df, ticker, args.account_value, args.risk_pct, 
                            ticker_output_dir, config_dict):
        success_count += 1
    else:
        print("\n⚠️  Backtest failed, continuing with remaining steps...")
    
    # Step 4: Generate chart
    print_step(4, total_steps, "Generating interactive HTML chart")
    if generate_chart(df, ticker, f"{args.months}mo", ticker_output_dir):
        success_count += 1
    else:
        print("\n⚠️  Chart generation failed, continuing...")
    
    # Step 5: Save analysis summary
    print_step(5, total_steps, "Saving analysis summary")
    if save_analysis_summary(df, ticker, f"{args.months}mo", ticker_output_dir):
        success_count += 1
    else:
        print("\n⚠️  Analysis summary save failed")
    
    # Print summary
    print_header("WORKFLOW COMPLETE")
    print(f"✅ Steps completed: {success_count}/{total_steps}")
    print(f"📁 All outputs saved to: {ticker_output_dir}")
    print()
    
    # List generated files
    print("📄 Generated files:")
    for file in sorted(ticker_output_dir.glob(f"{ticker}*")):
        file_size = file.stat().st_size
        if file_size > 1024*1024:
            size_str = f"{file_size/(1024*1024):.1f} MB"
        elif file_size > 1024:
            size_str = f"{file_size/1024:.1f} KB"
        else:
            size_str = f"{file_size} bytes"
        print(f"   • {file.name} ({size_str})")
    
    print()
    
    if success_count == total_steps:
        print("🎉 All operations completed successfully!")
        sys.exit(0)
    else:
        print("⚠️  Some operations failed. Check output above for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
