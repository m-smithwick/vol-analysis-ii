#!/usr/bin/env python3
"""
Bulk cache population from Massive.com flat files.
Downloads daily files containing all US stocks, splits by our tickers, and caches incrementally.
Supports sectional population with automatic duplicate detection.

Performance Modes:
    - Legacy mode: Sequential CSV decompression (~5-10s per day)
    - DuckDB mode: Indexed queries (~0.5s for 50 tickers) - 10-20x faster!

To use DuckDB mode:
    1. Build index once: python scripts/build_massive_index.py
    2. Run with --use-duckdb flag
"""

import argparse
import gzip
import json
import os
import time
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Set, List, Dict, Optional

import boto3
import pandas as pd
from botocore.config import Config
from botocore.exceptions import ClientError

from schema_manager import SchemaManager

schema_manager = SchemaManager()

# Try to import DuckDB provider (optional)
DUCKDB_AVAILABLE = False
try:
    from massive_duckdb_provider import MassiveDuckDBProvider
    DUCKDB_AVAILABLE = True
except ImportError:
    pass

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

def collect_all_tickers(ticker_files: List[str]) -> Set[str]:
    """Collect all unique tickers from specified ticker files."""
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
    """
    Persist cache data with metadata headers so downstream consumers can validate files.
    """
    df = df.sort_index()
    metadata = schema_manager.create_metadata_header(
        ticker=ticker,
        df=df,
        interval="1d",
        data_source="massive_flatfile"
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
            existing_df = read_cache_dataframe(cache_file)
            # Combine and sort
            combined = pd.concat([existing_df, converted])
            combined = combined[~combined.index.duplicated(keep='last')]
            combined.sort_index(inplace=True)
        else:
            combined = converted
        
        # Save
        write_cache_with_metadata(cache_file, ticker, combined)
        return 'ADDED'
        
    except Exception as e:
        print(f"      Error processing {ticker}: {e}")
        return 'ERROR'

def populate_cache_bulk_duckdb(
    tickers: Set[str],
    start_date: datetime,
    end_date: datetime
) -> Dict[str, int]:
    """
    Fast bulk population using DuckDB index (10-20x faster than CSV decompression).
    
    Args:
        tickers: Set of ticker symbols to populate
        start_date: Start date for data
        end_date: End date for data
    
    Returns:
        Dictionary with statistics
    """
    print("\n🚀 Using DuckDB fast mode...")
    
    cache_dir = Path('data_cache')
    cache_dir.mkdir(exist_ok=True)
    
    start_time = time.time()
    stats = {
        'tickers_processed': 0,
        'tickers_added': 0,
        'tickers_skipped': 0,
        'total_records_added': 0,
        'query_time': 0,
        'write_time': 0
    }
    
    try:
        # Initialize DuckDB provider
        provider = MassiveDuckDBProvider()
        
        # Get all data in ONE fast query
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        
        print(f"   Querying {len(tickers)} tickers from {start_date_str} to {end_date_str}...")
        query_start = time.time()
        ticker_data = provider.get_multiple_tickers(
            list(tickers), 
            start_date_str, 
            end_date_str
        )
        stats['query_time'] = time.time() - query_start
        
        print(f"   ✅ Query completed in {stats['query_time']:.1f}s")
        print(f"\n   Processing tickers...")
        
        # Write to data_cache with schema validation
        write_start = time.time()
        for ticker, df in ticker_data.items():
            stats['tickers_processed'] += 1
            
            if df.empty:
                print(f"   [{stats['tickers_processed']:3d}/{len(tickers)}] {ticker:6s} - No data")
                stats['tickers_skipped'] += 1
                continue
            
            cache_file = cache_dir / f"{ticker}_1d_data.csv"
            
            # Check for existing data
            existing_dates = get_existing_dates(cache_file) if cache_file.exists() else set()
            new_dates = set(df.index)
            dates_to_add = new_dates - existing_dates
            
            if not dates_to_add:
                print(f"   [{stats['tickers_processed']:3d}/{len(tickers)}] {ticker:6s} - All dates cached")
                stats['tickers_skipped'] += 1
                continue
            
            # Filter to new dates only
            df_new = df[df.index.isin(dates_to_add)]
            
            # Merge with existing and save
            if cache_file.exists():
                existing_df = read_cache_dataframe(cache_file)
                combined = pd.concat([existing_df, df_new])
                combined = combined[~combined.index.duplicated(keep='last')]
                combined.sort_index(inplace=True)
            else:
                combined = df_new
            
            # Save with schema metadata
            write_cache_with_metadata(cache_file, ticker, combined)
            
            stats['tickers_added'] += 1
            stats['total_records_added'] += len(dates_to_add)
            print(f"   [{stats['tickers_processed']:3d}/{len(tickers)}] {ticker:6s} - Added {len(dates_to_add)} days")
        
        stats['write_time'] = time.time() - write_start
        
        provider.close()
        
    except FileNotFoundError as e:
        print(f"\n❌ {e}")
        print("   Build DuckDB index first: python scripts/build_massive_index.py")
        return None
    except Exception as e:
        print(f"\n❌ Error in DuckDB mode: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    return stats


def populate_cache_bulk(
    start_date: datetime,
    end_date: datetime,
    save_others: bool = True,
    use_duckdb: bool = False,
    **kwargs
):
    """
    Bulk populate cache from Massive.com for date range.
    
    Args:
        start_date: Start date for data
        end_date: End date for data
        save_others: If True, save non-tracked tickers to massive_cache/
        use_duckdb: If True, use DuckDB fast mode (requires index)
    """
    print("="*70)
    print("BULK CACHE POPULATION FROM MASSIVE.COM")
    print("="*70)
    
    # Collect tickers
    print("\n1. Collecting tickers...")
    ticker_files = kwargs.get('ticker_files', ['stocks.txt'])
    all_tickers = collect_all_tickers(ticker_files)
    print(f"   Found {len(all_tickers)} unique tickers from: {', '.join(ticker_files)}")
    
    # Check if DuckDB mode is requested
    if use_duckdb:
        if not DUCKDB_AVAILABLE:
            print("\n⚠️  DuckDB not available. Install with: pip install duckdb")
            print("   Falling back to legacy mode...")
            use_duckdb = False
        elif not Path('massive_index.duckdb').exists():
            print("\n⚠️  DuckDB index not found at massive_index.duckdb")
            print("   Build index first: python scripts/build_massive_index.py")
            print("   Falling back to legacy mode...")
            use_duckdb = False
    
    # Use DuckDB fast mode if available and requested
    if use_duckdb:
        duckdb_stats = populate_cache_bulk_duckdb(all_tickers, start_date, end_date)
        
        if duckdb_stats is None:
            print("\n⚠️  DuckDB mode failed, falling back to legacy mode...")
        else:
            # Print DuckDB summary
            total_time = time.time() - time.time()  # Will be calculated below
            print(f"\n{'═'*70}")
            print(f"📊 DUCKDB FAST MODE SUMMARY")
            print(f"{'═'*70}")
            
            print(f"\nDate Range:")
            print(f"  Start:           {start_date.date()}")
            print(f"  End:             {end_date.date()}")
            
            print(f"\nProcessing Results:")
            print(f"  Tickers queried: {duckdb_stats['tickers_processed']}")
            print(f"  New data added:  {duckdb_stats['tickers_added']} tickers")
            print(f"  Already cached:  {duckdb_stats['tickers_skipped']} tickers")
            print(f"  Total records:   {duckdb_stats['total_records_added']:,} ticker-days")
            
            print(f"\nPerformance:")
            print(f"  Query time:      {duckdb_stats['query_time']:.1f}s")
            print(f"  Write time:      {duckdb_stats['write_time']:.1f}s")
            print(f"  Total time:      {duckdb_stats['query_time'] + duckdb_stats['write_time']:.1f}s")
            
            if duckdb_stats['tickers_processed'] > 0:
                avg_time = (duckdb_stats['query_time'] + duckdb_stats['write_time']) / duckdb_stats['tickers_processed']
                print(f"  Avg per ticker:  {avg_time:.2f}s")
            
            print(f"\n✅ Fast mode complete!")
            print(f"{'═'*70}\n")
            return
    
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
            # Check local cache first
            if save_others:
                local_cache_file = massive_cache_dir / f"{date_str}.csv.gz"
            else:
                local_cache_file = None
            
            # Load data from local cache or S3
            download_start = time.time()
            if local_cache_file and local_cache_file.exists():
                # Use local cached file (FAST)
                with gzip.open(local_cache_file, 'rt') as f:
                    df = pd.read_csv(f)
                download_time = time.time() - download_start
                source = "cache"
            else:
                # Download from S3 (SLOW)
                response = s3.get_object(Bucket=bucket, Key=object_key)
                download_time = time.time() - download_start
                
                # Decompress and parse
                with gzip.GzipFile(fileobj=BytesIO(response['Body'].read())) as gz:
                    df = pd.read_csv(gz)
                source = "s3"
            
            stats['total_download_time'] += download_time
            
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
            
            print(f"      ✓ {len(tickers_found)} tickers: {added} added, {skipped} skipped ({day_time:.1f}s, {source})")
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
  # Populate last 1 month (stocks.txt only by default)
  python populate_cache_bulk.py --months 1
  
  # Populate last 24 months with specific ticker file
  python populate_cache_bulk.py --months 24 --ticker-files ibd20.txt
  
  # Populate with multiple ticker files
  python populate_cache_bulk.py --months 24 --ticker-files stocks.txt ibd20.txt
  
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
    parser.add_argument(
        '--ticker-files',
        nargs='+',
        default=['stocks.txt'],
        help='Ticker file(s) to use (space-separated). Default: stocks.txt'
    )
    parser.add_argument(
        '--use-duckdb',
        action='store_true',
        help='Use DuckDB fast mode (10-20x faster, requires index)'
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
        save_others=not args.no_save_others,
        use_duckdb=args.use_duckdb,
        ticker_files=args.ticker_files
    )

if __name__ == "__main__":
    main()
