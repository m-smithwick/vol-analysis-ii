#!/usr/bin/env python3
"""
Query the massive_cache DuckDB index for testing and exploration.

This script provides a CLI interface to query the DuckDB index and verify
that it's working correctly.

Usage:
    python scripts/query_massive_index.py AAPL
    python scripts/query_massive_index.py AAPL --start 2024-01-01 --end 2024-12-31
    python scripts/query_massive_index.py AAPL MSFT GOOGL --stats
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from massive_duckdb_provider import MassiveDuckDBProvider
except ImportError as e:
    print(f"❌ Error importing provider: {e}")
    sys.exit(1)


def query_single_ticker(provider, ticker, start_date=None, end_date=None, show_sample=True):
    """Query and display data for a single ticker."""
    print(f"\n📊 Querying {ticker}...")
    
    start_time = datetime.now()
    df = provider.get_ticker_data(ticker, start_date, end_date)
    elapsed = (datetime.now() - start_time).total_seconds()
    
    if df.empty:
        print(f"   ⊘ No data found for {ticker}")
        return
    
    print(f"   ✅ Retrieved {len(df)} records in {elapsed:.3f}s")
    print(f"   Date range: {df.index[0].date()} to {df.index[-1].date()}")
    
    if show_sample:
        print(f"\n   Sample data (first 5 rows):")
        print(df.head().to_string(float_format=lambda x: f'{x:.2f}'))


def query_multiple_tickers(provider, tickers, start_date=None, end_date=None):
    """Query and display data for multiple tickers."""
    print(f"\n📊 Querying {len(tickers)} tickers...")
    
    start_time = datetime.now()
    data = provider.get_multiple_tickers(tickers, start_date, end_date)
    elapsed = (datetime.now() - start_time).total_seconds()
    
    print(f"   ✅ Query completed in {elapsed:.3f}s")
    print(f"   Performance: {elapsed / len(tickers):.3f}s per ticker")
    
    print(f"\n   Results:")
    total_records = 0
    for ticker, df in data.items():
        if df.empty:
            print(f"     {ticker:6s} - No data")
        else:
            print(f"     {ticker:6s} - {len(df):4d} records ({df.index[0].date()} to {df.index[-1].date()})")
            total_records += len(df)
    
    print(f"\n   Total records: {total_records:,}")


def show_database_stats(provider):
    """Display database statistics."""
    print("\n" + "="*70)
    print("DATABASE STATISTICS")
    print("="*70)
    
    stats = provider.get_stats()
    
    print(f"\nGeneral:")
    print(f"  Database file:    massive_index.duckdb")
    print(f"  File size:        {stats['db_size_mb']:.1f} MB")
    
    print(f"\nData Coverage:")
    print(f"  Total records:    {stats['total_records']:,}")
    print(f"  Unique tickers:   {stats['unique_tickers']:,}")
    print(f"  Trading days:     {stats['trading_days']}")
    print(f"  Date range:       {stats['earliest_date']} to {stats['latest_date']}")
    
    print(f"\nPerformance Metrics:")
    avg_records_per_ticker = stats['total_records'] / stats['unique_tickers']
    print(f"  Avg records/ticker: {avg_records_per_ticker:.0f}")
    avg_tickers_per_day = stats['total_records'] / stats['trading_days']
    print(f"  Avg tickers/day:    {avg_tickers_per_day:.0f}")


def check_ticker_coverage(provider, ticker):
    """Check coverage for a specific ticker."""
    print(f"\n📋 Checking coverage for {ticker}...")
    
    coverage = provider.check_ticker_coverage(ticker)
    
    if not coverage['available']:
        print(f"   ⊘ No data available for {ticker}")
        return
    
    print(f"   ✅ Data available")
    print(f"   Start date:    {coverage['start_date']}")
    print(f"   End date:      {coverage['end_date']}")
    print(f"   Record count:  {coverage['record_count']:,}")
    
    # Calculate trading days
    start = coverage['start_date']
    end = coverage['end_date']
    days_span = (end - start).days + 1
    
    print(f"   Time span:     {days_span} days")
    print(f"   Coverage:      {coverage['record_count'] / days_span * 100:.1f}% of calendar days")


def main():
    parser = argparse.ArgumentParser(
        description='Query massive_cache DuckDB index',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Query single ticker
  python scripts/query_massive_index.py AAPL
  
  # Query with date range
  python scripts/query_massive_index.py AAPL --start 2024-01-01 --end 2024-12-31
  
  # Query multiple tickers
  python scripts/query_massive_index.py AAPL MSFT GOOGL
  
  # Show database statistics
  python scripts/query_massive_index.py --stats
  
  # Check ticker coverage
  python scripts/query_massive_index.py AAPL --coverage
        """
    )
    
    parser.add_argument(
        'tickers',
        nargs='*',
        help='Ticker symbols to query'
    )
    parser.add_argument(
        '--start',
        type=str,
        help='Start date (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--end',
        type=str,
        help='End date (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show database statistics'
    )
    parser.add_argument(
        '--coverage',
        action='store_true',
        help='Check ticker coverage (use with single ticker)'
    )
    parser.add_argument(
        '--no-sample',
        action='store_true',
        help='Do not show sample data'
    )
    
    args = parser.parse_args()
    
    # Connect to provider
    try:
        provider = MassiveDuckDBProvider()
    except FileNotFoundError as e:
        print(f"❌ {e}")
        sys.exit(1)
    
    try:
        # Show stats if requested
        if args.stats:
            show_database_stats(provider)
            return
        
        # Check if any tickers provided
        if not args.tickers:
            print("❌ No tickers specified. Use --stats to see database statistics.")
            print("   Example: python scripts/query_massive_index.py AAPL")
            sys.exit(1)
        
        # Coverage check
        if args.coverage:
            if len(args.tickers) != 1:
                print("❌ Coverage check requires exactly one ticker")
                sys.exit(1)
            check_ticker_coverage(provider, args.tickers[0])
            return
        
        # Query tickers
        if len(args.tickers) == 1:
            query_single_ticker(
                provider, 
                args.tickers[0], 
                args.start, 
                args.end,
                show_sample=not args.no_sample
            )
        else:
            query_multiple_tickers(
                provider, 
                args.tickers, 
                args.start, 
                args.end
            )
    
    finally:
        provider.close()


if __name__ == "__main__":
    main()
