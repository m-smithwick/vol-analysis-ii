#!/usr/bin/env python3
"""
Bulk cache population from Massive.com flat files.
Downloads daily files containing all US stocks, splits by our tickers, and caches incrementally.
Supports sectional population with automatic duplicate detection.
"""

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
import pandas as pd
import gzip
from io import BytesIO
from datetime import datetime, timedelta
import os
from pathlib import Path
import time
import argparse
from typing import Set, List, Dict

def read_ticker_file(filepath: str) -> List[str]:
    """Read tickers from a file."""
    tickers = []
    if not os.path.exists(filepath):
        return tickers
    with open(filepath, 'r') as f:
        for line in f:
            ticker = line.strip().upper()
            if ticker and not ticker.startswith('#'):
                tickers.append(ticker)
    return tickers

def collect_all_tickers() -> Set[str]:
    """Collect all unique tickers from all ticker files."""
    ticker_files = ['stocks.txt', 'ibd.txt', 'ibd20.txt', 'ltl.txt', 'cmb.txt', 'short.txt']
    all_tickers = set()
    
    for file in ticker_files:
        tickers = read_ticker_file(file)
        all_tickers.update(tickers)
    
    return all_tickers

def generate_trading_days(start_date: datetime, end_date: datetime) -> List[datetime]:
    """
    Generate list of trading days (Mon-Fri) between start and end dates.
    Note: This doesn't account for market holidays, but Massive.com files
    won't exist for those days anyway, so we'll handle missing files gracefully.
    """
    days = []
    current = start_date
    while current <= end_date:
        # Skip weekends (Saturday=5, Sunday=6)
        if current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    return days

def get_existing_dates(cache_file: Path) -> Set[datetime]:
    """Get set of dates already in a ticker's cache file."""
    if not cache_file.exists():
        return set()
    
    try:
        df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
        # Convert index to set of dates (timezone-naive)
        dates = set(pd.to_datetime(df.index).tz_localize(None).date)
        return {datetime.combine(d, datetime.min.time()) for d in dates}
    except Exception as e:
        print(f"      Warning: Error reading {cache_file}: {e}")
        return set()

def convert_to_yfinance_format(ticker_df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """Convert Massive format to yfinance format."""
    if ticker_df.empty:
        return pd.DataFrame()
    
    # Make a copy to avoid SettingWithCopyWarning
    ticker_df = ticker_df.copy()
    
    # Convert window_start from nanoseconds to datetime
    ticker_df['Date'] = pd.to_datetime(ticker_df['window_start'], unit='ns')
    
    # Rename columns
    ticker_df = ticker_df.rename(columns={
        'open': 'Open',
        'high': 'High',
        'low': 'Low',
        'close': 'Close',
        'volume': 'Volume'
    })
    
    # Select and reorder columns
    ticker_df = ticker_df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
    
    # Set Date as index
    ticker_df.set_index('Date', inplace=True)
    
    # Sort by date
    ticker_df.sort_index(inplace=True)
    
    # Ensure timezone-naive
    if ticker_df.index.tzinfo is not None:
        ticker_df.index = ticker_df.index.tz_localize(None)
    
    return ticker_df

def append_to_ticker_cache(ticker: str, date: datetime, ticker_data: pd.DataFrame, cache_dir: Path) -> str:
    """
    Append data to ticker cache file if date doesn't already exist.
    Returns: 'ADDED', 'SKIPPED', or 'ERROR'
    """
    cache_file = cache_dir / f"{ticker}_1d_data.csv"
    
    try:
        # Convert to yfinance format
        converted = convert_to_yfinance_format(ticker_data, ticker)
        if converted.empty:
            return 'EMPTY'
        
        # Check if date already exists
        existing_dates = get_existing_dates(cache_file)
        if date in existing_dates:
            return 'SKIPPED'
        
        # Load existing data if file exists
        if cache_file.exists():
            existing_df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
            # Combine and sort
            combined = pd.concat([existing_df, converted])
            combined = combined[~combined.index.duplicated(keep='last')]
            combined.sort_index(inplace=True)
        else:
            combined = converted
        
        # Save
        combined.to_csv(cache_file)
        return 'ADDED'
        
    except Exception as e:
        print(f"      Error processing {ticker}: {e}")
        return 'ERROR'

def populate_cache_bulk(
    start_date: datetime,
    end_date: datetime,
    save_others: bool = True
):
    """
    Bulk populate cache from Massive.com for date range.
    
    Args:
        start_date: Start date for data
        end_date: End date for data
        save_others: If True, save non-tracked tickers to massive_cache/
    """
    print("="*70)
    print("BULK CACHE POPULATION FROM MASSIVE.COM")
    print("="*70)
    
    # Collect tickers
    print("\n1. Collecting tickers...")
    all_tickers = collect_all_tickers()
    print(f"   Found {len(all_tickers)} unique tickers across all ticker files")
    
    # Create directories
    cache_dir = Path('data_cache')
    cache_dir.mkdir(exist_ok=True)
    
    if save_others:
        massive_cache_dir = Path('massive_cache')
        massive_cache_dir.mkdir(exist_ok=True)
    
    # Generate trading days
    print(f"\n2. Generating date range...")
    trading_days = generate_trading_days(start_date, end_date)
    print(f"   Date range: {start_date.date()} to {end_date.date()}")
    print(f"   Trading days: {len(trading_days)}")
    
    # Initialize S3 client
    print(f"\n3. Initializing Massive.com connection...")
    session = boto3.Session(profile_name='massive')
    s3 = session.client(
        's3',
        endpoint_url='https://files.massive.com',
        config=Config(signature_version='s3v4'),
    )
    bucket = 'flatfiles'
    print(f"   ✅ Connected to Massive.com")
    
    # Process each day
    print(f"\n4. Processing daily files...")
    print(f"   {'─'*70}")
    
    stats = {
        'days_processed': 0,
        'days_skipped': 0,
        'days_failed': 0,
        'ticker_updates': 0,
        'ticker_skips': 0,
        'total_download_time': 0,
        'total_process_time': 0
    }
    
    start_time = time.time()
    
    for i, date in enumerate(trading_days, 1):
        day_start = time.time()
        date_str = date.strftime('%Y-%m-%d')
        object_key = f"us_stocks_sip/day_aggs_v1/{date.year}/{date.month:02d}/{date_str}.csv.gz"
        
        # Progress indicator
        pct = (i / len(trading_days)) * 100
        print(f"\n   [{i:3d}/{len(trading_days)}] {date_str} ({pct:5.1f}%)")
        
        try:
            # Download
            download_start = time.time()
            response = s3.get_object(Bucket=bucket, Key=object_key)
            download_time = time.time() - download_start
            stats['total_download_time'] += download_time
            
            # Decompress and parse
            with gzip.GzipFile(fileobj=BytesIO(response['Body'].read())) as gz:
                df = pd.read_csv(gz)
            
            # Split data
            our_mask = df['ticker'].isin(all_tickers)
            our_data = df[our_mask].copy()
            
            if save_others:
                other_data = df[~our_mask].copy()
            
            # Process our tickers
            tickers_found = set(our_data['ticker'].unique())
            added = 0
            skipped = 0
            
            for ticker in tickers_found:
                ticker_data = our_data[our_data['ticker'] == ticker]
                result = append_to_ticker_cache(ticker, date, ticker_data, cache_dir)
                if result == 'ADDED':
                    added += 1
                    stats['ticker_updates'] += 1
                elif result == 'SKIPPED':
                    skipped += 1
                    stats['ticker_skips'] += 1
            
            # Save others to compressed cache
            if save_others and not other_data.empty:
                cache_file = massive_cache_dir / f"{date_str}.csv.gz"
                if not cache_file.exists():  # Don't overwrite existing
                    with gzip.open(cache_file, 'wt') as f:
                        other_data.to_csv(f, index=False)
            
            day_time = time.time() - day_start
            stats['total_process_time'] += day_time
            
            print(f"      ✓ {len(tickers_found)} tickers: {added} added, {skipped} skipped ({day_time:.1f}s)")
            stats['days_processed'] += 1
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                print(f"      ⊘ File not found (holiday/weekend)")
                stats['days_skipped'] += 1
            else:
                print(f"      ✗ Error: {e.response['Error']['Code']}")
                stats['days_failed'] += 1
        except Exception as e:
            print(f"      ✗ Error: {str(e)[:50]}")
            stats['days_failed'] += 1
    
    total_time = time.time() - start_time
    
    # Summary
    print(f"\n{'═'*70}")
    print(f"📊 BULK POPULATION SUMMARY")
    print(f"{'═'*70}")
    
    print(f"\nDate Range:")
    print(f"  Start:           {start_date.date()}")
    print(f"  End:             {end_date.date()}")
    print(f"  Trading days:    {len(trading_days)}")
    
    print(f"\nProcessing Results:")
    print(f"  Days processed:  {stats['days_processed']}")
    print(f"  Days skipped:    {stats['days_skipped']} (no file)")
    print(f"  Days failed:     {stats['days_failed']}")
    
    print(f"\nTicker Updates:")
    print(f"  New data added:  {stats['ticker_updates']:,} ticker-days")
    print(f"  Duplicates skip: {stats['ticker_skips']:,} ticker-days")
    print(f"  Unique tickers:  {len(all_tickers)}")
    
    print(f"\nPerformance:")
    print(f"  Download time:   {stats['total_download_time']/60:.1f} min")
    print(f"  Process time:    {stats['total_process_time']/60:.1f} min")
    print(f"  Total time:      {total_time/60:.1f} min")
    
    if stats['days_processed'] > 0:
        avg_time = total_time / stats['days_processed']
        print(f"  Avg per day:     {avg_time:.1f}s")
    
    print(f"\n✅ Bulk cache population complete!")
    print(f"{'═'*70}\n")

def main():
    parser = argparse.ArgumentParser(
        description='Bulk populate cache from Massive.com flat files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Populate last 1 month
  python populate_cache_bulk.py --months 1
  
  # Populate last 24 months
  python populate_cache_bulk.py --months 24
  
  # Populate specific date range
  python populate_cache_bulk.py --start 2024-01-01 --end 2024-12-31
  
  # Extend existing cache (automatically skips duplicates)
  python populate_cache_bulk.py --months 3  # Run after --months 1
  
  # Don't save non-tracked tickers
  python populate_cache_bulk.py --months 6 --no-save-others
        """
    )
    
    date_group = parser.add_mutually_exclusive_group(required=True)
    date_group.add_argument(
        '--months',
        type=int,
        help='Number of months to go back from today'
    )
    date_group.add_argument(
        '--start',
        type=str,
        help='Start date (YYYY-MM-DD)'
    )
    
    parser.add_argument(
        '--end',
        type=str,
        help='End date (YYYY-MM-DD), defaults to today'
    )
    parser.add_argument(
        '--no-save-others',
        action='store_true',
        help='Do not save non-tracked tickers to massive_cache/'
    )
    
    args = parser.parse_args()
    
    # Calculate date range
    end_date = datetime.now()
    if args.end:
        end_date = datetime.strptime(args.end, '%Y-%m-%d')
    
    if args.months:
        start_date = end_date - timedelta(days=args.months * 30)
    else:
        start_date = datetime.strptime(args.start, '%Y-%m-%d')
    
    # Run bulk population
    populate_cache_bulk(
        start_date=start_date,
        end_date=end_date,
        save_others=not args.no_save_others
    )

if __name__ == "__main__":
    main()
