#!/usr/bin/env python3
"""
Refresh cache using Massive.com REST API for same-day data.

⚠️  IMPORTANT LIMITATIONS ⚠️
This script requires a Developer or Advanced subscription tier from Massive.com.
The Starter plan does NOT include access to the REST aggregates endpoint.

If you get "DELAYED" status errors, you need to use populate_cache_bulk.py instead.
See docs/EOD_DATA_WORKFLOW.md for the recommended approach for EOD trading.

The REST API provides data with 15-minute delay (vs Flat Files which are T+1).
This is useful for updating SPY and sector ETF data on the same trading day,
avoiding Yahoo Finance weekend/after-hours reliability issues.

However, for end-of-day trading workflows, flat files (populate_cache_bulk.py)
are the better solution as they provide complete EOD data and are included
in all subscription tiers.

Usage:
    # Update SPY + all 11 sector ETFs for last 3 days
    python refresh_cache_rest.py --spy-and-sectors --days 3
    
    # Update specific tickers
    python refresh_cache_rest.py --tickers SPY XLK XLF --days 1
    
    # From ticker files
    python refresh_cache_rest.py --ticker-files indices.txt sector_etfs.txt --days 2

API Key:
    Set MASSIVE_API_KEY environment variable or use --api-key argument.
    Get your API key from: https://massive.com/dashboard/keys

Subscription Requirements:
    - Developer or Advanced tier required for daily aggregates
    - Starter tier: Use populate_cache_bulk.py instead
    - See: https://massive.com/pricing?product=stocks
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Set, Optional

import pandas as pd
import requests

from schema_manager import SchemaManager

schema_manager = SchemaManager()

# SPY + 11 sector ETFs for regime filtering
SPY_AND_SECTORS = ['SPY', 'XLK', 'XLF', 'XLV', 'XLE', 'XLY', 'XLP', 'XLI', 'XLU', 'XLRE', 'XLB', 'XLC']


def get_api_key(args_api_key: Optional[str] = None) -> str:
    """
    Get Massive API key from multiple sources (priority order):
    1. Command-line argument (--api-key)
    2. massive_api_key.txt file in project root
    3. MASSIVE_API_KEY environment variable
    
    Args:
        args_api_key: API key from command-line arguments
        
    Returns:
        API key string
        
    Raises:
        ValueError: If no API key is found
    """
    # Check command line argument first
    if args_api_key:
        return args_api_key
    
    # Check for API key file in project root
    key_file = Path('massive_api_key.txt')
    if key_file.exists():
        try:
            api_key = key_file.read_text().strip()
            if api_key:
                return api_key
        except Exception as e:
            print(f"Warning: Could not read massive_api_key.txt: {e}")
    
    # Check environment variable
    api_key = os.environ.get('MASSIVE_API_KEY')
    if api_key:
        return api_key
    
    raise ValueError(
        "Massive API key not found. Either:\n"
        "  1. Create massive_api_key.txt in project root with your key\n"
        "  2. Set environment variable: export MASSIVE_API_KEY='your_key'\n"
        "  3. Pass via argument: --api-key YOUR_KEY\n"
        "Get your key from: https://massive.com/dashboard/keys"
    )


def read_ticker_file(filepath: str) -> List[str]:
    """Read tickers from a file."""
    tickers = []
    if not os.path.exists(filepath):
        print(f"Warning: File not found: {filepath}")
        return tickers
    
    with open(filepath, 'r') as f:
        for line in f:
            ticker = line.strip().upper()
            if ticker and not ticker.startswith('#'):
                tickers.append(ticker)
    
    return tickers


def collect_tickers(
    ticker_list: Optional[List[str]] = None,
    ticker_files: Optional[List[str]] = None,
    spy_and_sectors: bool = False
) -> Set[str]:
    """
    Collect unique tickers from various sources.
    
    Args:
        ticker_list: Explicit list of ticker symbols
        ticker_files: List of files containing tickers
        spy_and_sectors: Use SPY + 11 sector ETFs preset
        
    Returns:
        Set of unique ticker symbols
    """
    all_tickers = set()
    
    if spy_and_sectors:
        all_tickers.update(SPY_AND_SECTORS)
        print(f"   Using SPY + sectors preset: {len(SPY_AND_SECTORS)} tickers")
    
    if ticker_list:
        all_tickers.update(t.upper() for t in ticker_list)
        print(f"   Added {len(ticker_list)} tickers from command line")
    
    if ticker_files:
        for filepath in ticker_files:
            tickers = read_ticker_file(filepath)
            if tickers:
                all_tickers.update(tickers)
                print(f"   Added {len(tickers)} tickers from {filepath}")
    
    return all_tickers


def generate_trading_days(days_back: int) -> List[datetime]:
    """
    Generate list of trading days (Mon-Fri) going back N days from today.
    
    Args:
        days_back: Number of days to look back
        
    Returns:
        List of trading day dates (excludes weekends)
    """
    today = datetime.now()
    days = []
    
    # Go back enough calendar days to get requested trading days
    for i in range(days_back * 2):  # Conservative: assume worst case
        date = today - timedelta(days=i)
        # Skip weekends (Saturday=5, Sunday=6)
        if date.weekday() < 5:
            days.append(date)
            if len(days) >= days_back:
                break
    
    return sorted(days)


def fetch_ticker_data_rest(
    ticker: str,
    start_date: datetime,
    end_date: datetime,
    api_key: str,
    retry_count: int = 3
) -> Optional[pd.DataFrame]:
    """
    Fetch OHLCV data from Massive REST API.
    
    Args:
        ticker: Stock symbol
        start_date: Start date for data
        end_date: End date for data
        api_key: Massive API key
        retry_count: Number of retries on failure
        
    Returns:
        DataFrame with OHLCV data in yfinance format, or None on error
    """
    # Format dates as YYYY-MM-DD
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')
    
    # Construct API endpoint
    url = (
        f"https://api.massive.com/v2/aggs/ticker/{ticker}/range/1/day/"
        f"{start_str}/{end_str}"
    )
    
    headers = {
        'Authorization': f'Bearer {api_key}'
    }
    
    params = {
        'adjusted': 'true',
        'sort': 'asc',
        'limit': 5000
    }
    
    for attempt in range(retry_count):
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('status') != 'OK':
                    print(f"      API returned non-OK status: {data.get('status')}")
                    return None
                
                results = data.get('results', [])
                if not results:
                    print(f"      No data returned for {ticker}")
                    return None
                
                # Convert to DataFrame
                df = pd.DataFrame(results)
                
                # Convert timestamp (milliseconds) to datetime
                df['Date'] = pd.to_datetime(df['t'], unit='ms')
                
                # Rename columns to yfinance format
                df = df.rename(columns={
                    'o': 'Open',
                    'h': 'High',
                    'l': 'Low',
                    'c': 'Close',
                    'v': 'Volume'
                })
                
                # Select and order columns
                df = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
                
                # Set Date as index
                df.set_index('Date', inplace=True)
                
                # Ensure timezone-naive
                if df.index.tzinfo is not None:
                    df.index = df.index.tz_localize(None)
                
                # Sort by date
                df.sort_index(inplace=True)
                
                return df
                
            elif response.status_code == 429:
                # Rate limit - wait and retry
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"      Rate limit hit, waiting {wait_time}s...")
                time.sleep(wait_time)
                continue
                
            elif response.status_code == 404:
                print(f"      Ticker {ticker} not found")
                return None
                
            else:
                print(f"      API error {response.status_code}: {response.text[:100]}")
                return None
                
        except requests.exceptions.Timeout:
            print(f"      Request timeout (attempt {attempt + 1}/{retry_count})")
            if attempt < retry_count - 1:
                time.sleep(1)
                continue
            return None
            
        except Exception as e:
            print(f"      Error fetching {ticker}: {str(e)[:100]}")
            return None
    
    return None


def get_existing_dates(cache_file: Path) -> Set[datetime]:
    """Get set of dates already in a ticker's cache file."""
    if not cache_file.exists():
        return set()
    
    try:
        df = pd.read_csv(cache_file, index_col=0, parse_dates=True, comment='#')
        # Convert index to set of dates (timezone-naive)
        dates = set(pd.to_datetime(df.index).tz_localize(None).date)
        return {datetime.combine(d, datetime.min.time()) for d in dates}
    except Exception as e:
        print(f"      Warning: Error reading {cache_file}: {e}")
        return set()


def read_cache_dataframe(cache_file: Path) -> pd.DataFrame:
    """Load existing cache data while ignoring metadata headers."""
    try:
        return pd.read_csv(cache_file, index_col=0, parse_dates=True, comment='#')
    except Exception as e:
        print(f"      Warning: Failed to load {cache_file}: {e}")
        return pd.DataFrame()


def write_cache_with_metadata(cache_file: Path, ticker: str, df: pd.DataFrame) -> None:
    """Persist cache data with metadata headers."""
    df = df.sort_index()
    metadata = schema_manager.create_metadata_header(
        ticker=ticker,
        df=df,
        interval="1d",
        data_source="massive_rest"
    )
    metadata_json = json.dumps(metadata, indent=2)
    
    with open(cache_file, 'w', newline='') as f:
        f.write("# Volume Analysis System - Cache File\n")
        f.write(f"# Generated: {datetime.now().isoformat()}\n")
        f.write("# Metadata (JSON format):\n")
        for line in metadata_json.split('\n'):
            f.write(f"# {line}\n")
        f.write("#\n")
        df.to_csv(f)


def update_ticker_cache(
    ticker: str,
    new_data: pd.DataFrame,
    cache_dir: Path
) -> tuple[int, int]:
    """
    Update ticker cache with new data, skipping duplicates.
    
    Args:
        ticker: Stock symbol
        new_data: New OHLCV data
        cache_dir: Cache directory path
        
    Returns:
        Tuple of (rows_added, rows_skipped)
    """
    cache_file = cache_dir / f"{ticker}_1d_data.csv"
    
    if new_data.empty:
        return 0, 0
    
    # Get dates already in cache
    existing_dates = get_existing_dates(cache_file)
    new_dates = set(datetime.combine(d.date(), datetime.min.time()) 
                   for d in new_data.index)
    
    # Filter to only new dates
    dates_to_add = new_dates - existing_dates
    if not dates_to_add:
        return 0, len(new_dates)
    
    # Filter new_data to only dates we're adding
    mask = new_data.index.map(lambda d: datetime.combine(d.date(), datetime.min.time()) in dates_to_add)
    filtered_data = new_data[mask]
    
    # Load and merge with existing data
    if cache_file.exists():
        existing_df = read_cache_dataframe(cache_file)
        combined = pd.concat([existing_df, filtered_data])
        combined = combined[~combined.index.duplicated(keep='last')]
        combined.sort_index(inplace=True)
    else:
        combined = filtered_data
    
    # Save updated cache
    write_cache_with_metadata(cache_file, ticker, combined)
    
    return len(dates_to_add), len(new_dates) - len(dates_to_add)


def refresh_cache_rest(
    tickers: Set[str],
    days: int,
    api_key: str,
    rate_limit_delay: float = 0.1
) -> None:
    """
    Refresh cache using Massive REST API for recent days.
    
    Args:
        tickers: Set of ticker symbols to update
        days: Number of days to look back
        api_key: Massive API key
        rate_limit_delay: Delay between API calls in seconds
    """
    print("="*70)
    print("CACHE REFRESH FROM MASSIVE.COM REST API")
    print("="*70)
    
    # Setup
    cache_dir = Path('data_cache')
    cache_dir.mkdir(exist_ok=True)
    
    # Generate date range
    trading_days = generate_trading_days(days)
    start_date = trading_days[0]
    end_date = trading_days[-1]
    
    print(f"\nDate Range:")
    print(f"  Looking back:    {days} trading days")
    print(f"  Start date:      {start_date.date()}")
    print(f"  End date:        {end_date.date()}")
    print(f"  Tickers:         {len(tickers)}")
    
    # Process each ticker
    print(f"\nProcessing tickers...")
    print(f"{'─'*70}")
    
    stats = {
        'success': 0,
        'failed': 0,
        'rows_added': 0,
        'rows_skipped': 0
    }
    
    start_time = time.time()
    
    for i, ticker in enumerate(sorted(tickers), 1):
        pct = (i / len(tickers)) * 100
        print(f"\n[{i:3d}/{len(tickers)}] {ticker} ({pct:5.1f}%)")
        
        # Fetch data from REST API
        df = fetch_ticker_data_rest(ticker, start_date, end_date, api_key)
        
        if df is None or df.empty:
            print(f"      ✗ Failed to fetch data")
            stats['failed'] += 1
            time.sleep(rate_limit_delay)
            continue
        
        # Update cache
        added, skipped = update_ticker_cache(ticker, df, cache_dir)
        
        stats['success'] += 1
        stats['rows_added'] += added
        stats['rows_skipped'] += skipped
        
        print(f"      ✓ {added} new rows, {skipped} duplicates")
        
        # Rate limiting
        time.sleep(rate_limit_delay)
    
    total_time = time.time() - start_time
    
    # Summary
    print(f"\n{'═'*70}")
    print(f"📊 REFRESH SUMMARY")
    print(f"{'═'*70}")
    
    print(f"\nResults:")
    print(f"  Success:         {stats['success']}/{len(tickers)} tickers")
    print(f"  Failed:          {stats['failed']}")
    print(f"  Rows added:      {stats['rows_added']:,}")
    print(f"  Duplicates skip: {stats['rows_skipped']:,}")
    
    print(f"\nPerformance:")
    print(f"  Total time:      {total_time:.1f}s")
    if stats['success'] > 0:
        avg_time = total_time / stats['success']
        print(f"  Avg per ticker:  {avg_time:.1f}s")
    
    print(f"\n✅ Cache refresh complete!")
    print(f"{'═'*70}\n")


def main():
    parser = argparse.ArgumentParser(
        description='Refresh cache using Massive.com REST API for same-day data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Update SPY + all 11 sector ETFs for last 3 days
  python refresh_cache_rest.py --spy-and-sectors --days 3
  
  # Update specific tickers
  python refresh_cache_rest.py --tickers SPY XLK XLF --days 1
  
  # From ticker files
  python refresh_cache_rest.py --ticker-files indices.txt sector_etfs.txt --days 2
  
  # Combine sources
  python refresh_cache_rest.py --spy-and-sectors --tickers AAPL MSFT --days 1

API Key:
  Set MASSIVE_API_KEY environment variable:
    export MASSIVE_API_KEY='your_key_here'
  
  Or pass via command line:
    python refresh_cache_rest.py --api-key YOUR_KEY ...
  
  Get your key from: https://massive.com/dashboard/keys
        """
    )
    
    # Ticker sources
    parser.add_argument(
        '--spy-and-sectors',
        action='store_true',
        help='Use SPY + 11 sector ETFs preset (for regime filtering)'
    )
    parser.add_argument(
        '--tickers',
        nargs='+',
        help='Specific ticker symbols to update'
    )
    parser.add_argument(
        '--ticker-files',
        nargs='+',
        help='Files containing ticker symbols (one per line)'
    )
    
    # Date range
    parser.add_argument(
        '--days',
        type=int,
        default=3,
        help='Number of trading days to look back (default: 3)'
    )
    
    # API configuration
    parser.add_argument(
        '--api-key',
        help='Massive API key (or use MASSIVE_API_KEY env var)'
    )
    parser.add_argument(
        '--rate-limit-delay',
        type=float,
        default=0.1,
        help='Delay between API calls in seconds (default: 0.1)'
    )
    
    args = parser.parse_args()
    
    # Validate ticker sources
    if not (args.spy_and_sectors or args.tickers or args.ticker_files):
        parser.error("Must specify at least one ticker source: "
                    "--spy-and-sectors, --tickers, or --ticker-files")
    
    try:
        # Get API key
        api_key = get_api_key(args.api_key)
        
        # Collect tickers
        print("\n1. Collecting tickers...")
        tickers = collect_tickers(
            ticker_list=args.tickers,
            ticker_files=args.ticker_files,
            spy_and_sectors=args.spy_and_sectors
        )
        
        if not tickers:
            print("Error: No tickers found")
            sys.exit(1)
        
        print(f"   Total unique tickers: {len(tickers)}")
        
        # Run refresh
        refresh_cache_rest(
            tickers=tickers,
            days=args.days,
            api_key=api_key,
            rate_limit_delay=args.rate_limit_delay
        )
        
    except ValueError as e:
        print(f"\nError: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
