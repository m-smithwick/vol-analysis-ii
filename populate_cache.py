"""
Script to populate cache with historical data for regime analysis.
Downloads 3 years of data for all tickers in specified files.
"""

import argparse
from datetime import datetime, timedelta
import time
import data_manager
from error_handler import setup_logging, logger

def populate_cache_for_tickers(
    ticker_file: str,
    months: int = None,
    days: int = None,
    interval: str = "1d",
    force_refresh: bool = False,
    data_source: str = "yfinance"
):
    """
    Populate cache with historical data for all tickers in a file.
    
    Args:
        ticker_file: Path to file with tickers
        months: Number of months of history to download (use months OR days, not both)
        days: Number of days of history to download (use months OR days, not both)
        interval: Data interval
        force_refresh: Redownload even if cached
        data_source: Data source to use ('yfinance' or 'massive')
        
    Returns:
        Tuple of (success_count, fail_count)
    """
    # Default to 36 months if neither specified
    if months is None and days is None:
        months = 36
    
    # Construct period string and calculate date range
    if days is not None:
        period = f"{days}d"
        period_display = f"{days} days"
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
    else:
        period = f"{months}mo"
        period_display = f"{months} months (≈{months/12:.1f} years)"
        end_date = datetime.now()
        start_date = end_date - timedelta(days=months * 30)
    
    # Read tickers
    tickers = data_manager.read_ticker_file(ticker_file)
    
    logger.info(f"Populating cache for {len(tickers)} tickers from {ticker_file}")
    logger.info(f"Period: {period_display}, Interval: {interval}, Data Source: {data_source}")
    
    success_count = 0
    fail_count = 0
    skipped_count = 0
    
    print(f"\n{'='*70}")
    print(f"📥 CACHE POPULATION: {ticker_file}")
    print(f"{'='*70}")
    print(f"Tickers: {len(tickers)}")
    print(f"Period: {period_display}")
    print(f"Interval: {interval}")
    print(f"Data Source: {data_source}")
    print(f"Force Refresh: {force_refresh}")
    print(f"{'='*70}\n")
    
    for i, ticker in enumerate(tickers, 1):
        try:
            print(f"[{i:2d}/{len(tickers)}] {ticker:6s} ", end='', flush=True)
            
            # Check if already cached and covered
            if not force_refresh:
                if data_manager.cache_covers_date_range(
                    ticker, start_date, end_date, interval
                ):
                    cache_range = data_manager.get_cache_date_range(ticker, interval)
                    if cache_range:
                        cache_start, cache_end = cache_range
                        print(f"✓ Already cached ({cache_start.date()} to {cache_end.date()})")
                        skipped_count += 1
                        success_count += 1
                        continue
            
            # Download data (smart function will cache it)
            # Must set cache_only=False to allow downloads
            df = data_manager.get_smart_data(
                ticker=ticker,
                period=period,
                interval=interval,
                force_refresh=force_refresh,
                cache_only=False,  # Allow downloading from API
                data_source=data_source
            )
            
            print(f"✓ Cached {len(df):4d} periods ({df.index[0].date()} to {df.index[-1].date()})")
            success_count += 1
            
        except Exception as e:
            print(f"✗ Failed: {str(e)[:50]}")
            logger.error(f"Failed to cache {ticker}: {e}")
            fail_count += 1
            continue
        
        finally:
            # Add 1-second delay after every 10 tickers to avoid API throttling
            if i % 10 == 0 and i < len(tickers):
                print(f"    ⏸️  Pausing 1 second to avoid API throttling...")
                time.sleep(1)
    
    # Summary
    print(f"\n{'='*70}")
    print(f"📊 CACHE POPULATION SUMMARY")
    print(f"{'='*70}")
    print(f"Total Tickers:     {len(tickers)}")
    print(f"✓ Successful:      {success_count} ({success_count/len(tickers)*100:.1f}%)")
    print(f"  - Downloaded:    {success_count - skipped_count}")
    print(f"  - Already Cached: {skipped_count}")
    print(f"✗ Failed:          {fail_count} ({fail_count/len(tickers)*100:.1f}%)")
    print(f"{'='*70}\n")
    
    return success_count, fail_count

def populate_all_ticker_files(
    months: int = None,
    days: int = None,
    interval: str = "1d",
    force_refresh: bool = False,
    data_source: str = "yfinance"
):
    """
    Populate cache for all ticker files in the project.
    
    Args:
        months: Number of months of history (use months OR days, not both)
        days: Number of days of history (use months OR days, not both)
        interval: Data interval
        force_refresh: Force redownload
        data_source: Data source to use ('yfinance' or 'massive')
    """
    import os
    
    # Find all .txt files in current directory (excluding documentation files)
    ticker_files = []
    # Known ticker files - being explicit to avoid documentation files
    known_ticker_files = {'ibd.txt', 'ibd20.txt', 'ltl.txt', 'stocks.txt', 'cmb.txt', 'short.txt', 'sector_etfs.txt'}
    
    for file in os.listdir('.'):
        if file.endswith('.txt') and file in known_ticker_files:
            ticker_files.append(file)
    
    if not ticker_files:
        print("⚠️  No ticker files found")
        return
    
    print(f"\n{'='*70}")
    print(f"📦 BATCH CACHE POPULATION")
    print(f"{'='*70}")
    print(f"Found {len(ticker_files)} ticker files: {', '.join(ticker_files)}")
    print(f"{'='*70}\n")
    
    total_success = 0
    total_fail = 0
    results = {}
    
    for ticker_file in sorted(ticker_files):
        success, fail = populate_cache_for_tickers(
            ticker_file=ticker_file,
            months=months,
            days=days,
            interval=interval,
            force_refresh=force_refresh,
            data_source=data_source
        )
        results[ticker_file] = (success, fail)
        total_success += success
        total_fail += fail
    
    # Overall summary
    print(f"\n{'='*70}")
    print(f"🎯 OVERALL SUMMARY - ALL TICKER FILES")
    print(f"{'='*70}")
    for ticker_file, (success, fail) in sorted(results.items()):
        total = success + fail
        print(f"{ticker_file:20s}: {success:3d}/{total:3d} successful ({success/total*100:.0f}%)")
    print(f"{'='*70}")
    print(f"Total Success: {total_success}")
    print(f"Total Failed:  {total_fail}")
    print(f"{'='*70}\n")

def main():
    setup_logging()
    
    parser = argparse.ArgumentParser(
        description='Populate cache with historical data for regime analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Populate single file with 3 years of daily data (yfinance)
  python populate_cache.py -f ibd.txt -m 36
  
  # Populate with 5 days of data (quick updates)
  python populate_cache.py -f stocks.txt -d 5
  
  # Populate with 30 days of data
  python populate_cache.py -f ticker_lists/short.txt -d 30
  
  # Populate all ticker files with 24 months from Massive.com
  python populate_cache.py --all -m 24 --data-source massive
  
  # Force refresh with 10 days
  python populate_cache.py -f stocks.txt -d 10 --force
        """
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '-f', '--file',
        help='Single ticker file to populate (e.g., ibd.txt, stocks.txt)'
    )
    group.add_argument(
        '--all',
        action='store_true',
        help='Populate all ticker files in current directory'
    )
    
    # Period group - months OR days (mutually exclusive)
    period_group = parser.add_mutually_exclusive_group()
    period_group.add_argument(
        '-m', '--months',
        type=int,
        help='Months of history to download (e.g., 1, 6, 36). Default: 36 if neither -m nor -d specified'
    )
    period_group.add_argument(
        '-d', '--days',
        type=int,
        help='Days of history to download (e.g., 5, 10, 30). Useful for quick cache updates'
    )
    parser.add_argument(
        '-i', '--interval',
        default='1d',
        help='Data interval (default: 1d for daily data)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force refresh even if already cached'
    )
    parser.add_argument(
        '--data-source',
        choices=['yfinance', 'massive'],
        default='yfinance',
        help='Data source to use (default: yfinance, alternative: massive)'
    )
    
    args = parser.parse_args()
    
    # Run population
    if args.all:
        populate_all_ticker_files(
            months=args.months,
            days=args.days,
            interval=args.interval,
            force_refresh=args.force,
            data_source=args.data_source
        )
    else:
        populate_cache_for_tickers(
            ticker_file=args.file,
            months=args.months,
            days=args.days,
            interval=args.interval,
            force_refresh=args.force,
            data_source=args.data_source
        )

if __name__ == "__main__":
    main()
