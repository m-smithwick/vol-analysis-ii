"""
Script to populate cache with historical data for regime analysis.
Downloads 3 years of data for all tickers in specified files.
"""

import argparse
from datetime import datetime, timedelta
import data_manager
from error_handler import setup_logging, logger

def populate_cache_for_tickers(
    ticker_file: str,
    months: int = 36,
    interval: str = "1d",
    force_refresh: bool = False
):
    """
    Populate cache with historical data for all tickers in a file.
    
    Args:
        ticker_file: Path to file with tickers
        months: Number of months of history to download
        interval: Data interval
        force_refresh: Redownload even if cached
        
    Returns:
        Tuple of (success_count, fail_count)
    """
    # Read tickers
    tickers = data_manager.read_ticker_file(ticker_file)
    
    logger.info(f"Populating cache for {len(tickers)} tickers from {ticker_file}")
    logger.info(f"Period: {months} months ({months/12:.1f} years), Interval: {interval}")
    
    # Calculate date range for checking coverage
    end_date = datetime.now()
    start_date = end_date - timedelta(days=months * 30)
    
    success_count = 0
    fail_count = 0
    skipped_count = 0
    
    print(f"\n{'='*70}")
    print(f"📥 CACHE POPULATION: {ticker_file}")
    print(f"{'='*70}")
    print(f"Tickers: {len(tickers)}")
    print(f"Period: {months} months (≈{months/12:.1f} years)")
    print(f"Interval: {interval}")
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
            df = data_manager.get_smart_data(
                ticker=ticker,
                period=f"{months}mo",
                interval=interval,
                force_refresh=force_refresh
            )
            
            print(f"✓ Cached {len(df):4d} periods ({df.index[0].date()} to {df.index[-1].date()})")
            success_count += 1
            
        except Exception as e:
            print(f"✗ Failed: {str(e)[:50]}")
            logger.error(f"Failed to cache {ticker}: {e}")
            fail_count += 1
            continue
    
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
    months: int = 36,
    interval: str = "1d",
    force_refresh: bool = False
):
    """
    Populate cache for all ticker files in the project.
    
    Args:
        months: Number of months of history
        interval: Data interval
        force_refresh: Force redownload
    """
    import os
    
    # Find all .txt files in current directory (excluding documentation files)
    ticker_files = []
    # Known ticker files - being explicit to avoid documentation files
    known_ticker_files = {'ibd.txt', 'ibd20.txt', 'ltl.txt', 'stocks.txt', 'cmb.txt', 'short.txt'}
    
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
            interval=interval,
            force_refresh=force_refresh
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
  # Populate single file with 3 years of daily data
  python populate_cache.py -f ibd.txt -m 36
  
  # Populate all ticker files
  python populate_cache.py --all -m 36
  
  # Force refresh even if cached
  python populate_cache.py -f stocks.txt -m 36 --force
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
    
    parser.add_argument(
        '-m', '--months',
        type=int,
        default=36,
        help='Months of history to download (default: 36 = 3 years)'
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
    
    args = parser.parse_args()
    
    # Run population
    if args.all:
        populate_all_ticker_files(
            months=args.months,
            interval=args.interval,
            force_refresh=args.force
        )
    else:
        populate_cache_for_tickers(
            ticker_file=args.file,
            months=args.months,
            interval=args.interval,
            force_refresh=args.force
        )

if __name__ == "__main__":
    main()
