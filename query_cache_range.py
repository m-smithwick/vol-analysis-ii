"""
Tool to query cached data by date range.
Useful for regime-based analysis and testing cache coverage.
"""

import argparse
from datetime import datetime
import data_manager
from error_handler import setup_logging, logger

def query_and_display(
    ticker: str,
    start_date: datetime,
    end_date: datetime,
    interval: str = "1d"
):
    """Query cache and display results."""
    
    print(f"\n{'='*70}")
    print(f"📊 CACHE QUERY: {ticker}")
    print(f"{'='*70}")
    print(f"Requested Range: {start_date.date()} to {end_date.date()}")
    print(f"Interval: {interval}")
    print(f"{'='*70}\n")
    
    # Check cache coverage first
    cache_range = data_manager.get_cache_date_range(ticker, interval)
    
    if cache_range is None:
        print(f"❌ No cached data for {ticker} ({interval})")
        print(f"\nTo populate cache, run:")
        print(f"  python populate_cache.py -f <ticker_file> -m 36")
        return
    
    cache_start, cache_end = cache_range
    print(f"📁 Cache Coverage:")
    print(f"   Start: {cache_start.date()} {cache_start.time()}")
    print(f"   End:   {cache_end.date()} {cache_end.time()}")
    print(f"   Total: {(cache_end - cache_start).days} days\n")
    
    # Check if range is covered
    covered = data_manager.cache_covers_date_range(
        ticker, start_date, end_date, interval
    )
    
    if covered:
        print(f"✓ Cache FULLY covers requested range\n")
    else:
        print(f"⚠️  Cache does NOT fully cover requested range")
        if start_date < cache_start:
            print(f"   Missing: {start_date.date()} to {cache_start.date()} (before cache)")
        if end_date > cache_end:
            print(f"   Missing: {cache_end.date()} to {end_date.date()} (after cache)")
        print()
    
    # Query the range
    df = data_manager.query_cache_by_date_range(
        ticker, start_date, end_date, interval
    )
    
    if df is None or df.empty:
        print(f"❌ No data found in requested range")
        return
    
    print(f"📈 Query Results:")
    print(f"   Periods Retrieved: {len(df)}")
    print(f"   Actual Start: {df.index[0]}")
    print(f"   Actual End:   {df.index[-1]}")
    print(f"   Span: {(df.index[-1] - df.index[0]).days} days\n")
    
    # Show basic stats
    print(f"📊 Price Statistics:")
    print(f"   Open:  ${df['Open'].iloc[0]:8.2f} → ${df['Open'].iloc[-1]:8.2f} ({(df['Open'].iloc[-1]/df['Open'].iloc[0]-1)*100:+.1f}%)")
    print(f"   High:  ${df['High'].max():8.2f} (max)")
    print(f"   Low:   ${df['Low'].min():8.2f} (min)")
    print(f"   Close: ${df['Close'].iloc[0]:8.2f} → ${df['Close'].iloc[-1]:8.2f} ({(df['Close'].iloc[-1]/df['Close'].iloc[0]-1)*100:+.1f}%)")
    print(f"   Avg Volume: {df['Volume'].mean()/1e6:,.1f}M shares\n")
    
    # Show first and last few rows
    print(f"First 5 periods:")
    print(df.head()[['Open', 'High', 'Low', 'Close', 'Volume']].to_string())
    print(f"\n...\n")
    print(f"Last 5 periods:")
    print(df.tail()[['Open', 'High', 'Low', 'Close', 'Volume']].to_string())
    print(f"\n{'='*70}\n")

def main():
    setup_logging()
    
    parser = argparse.ArgumentParser(
        description='Query cached data by date range for regime analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Query choppy market period (Nov 2023 - Apr 2025)
  python query_cache_range.py AAPL --start 2023-11-01 --end 2025-04-04
  
  # Query rally period (Apr 2025 - Nov 2025)
  python query_cache_range.py NVDA --start 2025-04-04 --end 2025-11-07
  
  # Query last 6 months
  python query_cache_range.py MSFT --start 2025-05-01 --end 2025-11-01
        """
    )
    
    parser.add_argument(
        'ticker',
        help='Ticker symbol (e.g., AAPL, NVDA, MSFT)'
    )
    parser.add_argument(
        '--start',
        required=True,
        help='Start date (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--end',
        required=True,
        help='End date (YYYY-MM-DD)'
    )
    parser.add_argument(
        '-i', '--interval',
        default='1d',
        help='Data interval (default: 1d)'
    )
    
    args = parser.parse_args()
    
    # Parse dates
    try:
        start_date = datetime.strptime(args.start, '%Y-%m-%d')
        end_date = datetime.strptime(args.end, '%Y-%m-%d')
    except ValueError as e:
        print(f"❌ Error parsing dates: {e}")
        print("Use format: YYYY-MM-DD (e.g., 2025-04-04)")
        return
    
    # Validate date range
    if start_date >= end_date:
        print(f"❌ Start date must be before end date")
        return
    
    # Query and display
    query_and_display(
        ticker=args.ticker.upper(),
        start_date=start_date,
        end_date=end_date,
        interval=args.interval
    )

if __name__ == "__main__":
    main()
