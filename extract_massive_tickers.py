#!/usr/bin/env python3
"""
Extract all unique tickers from massive_cache and split into batch files.

This script reads the most recent massive_cache file, extracts all unique tickers,
and splits them into manageable batch files (~1000 tickers each) for sequential
cache population.

Usage:
    python extract_massive_tickers.py
    python extract_massive_tickers.py --date 2025-12-11
    python extract_massive_tickers.py --batch-size 500
"""

import argparse
import gzip
import pandas as pd
from pathlib import Path
from datetime import datetime


def extract_tickers_from_massive_file(date_str: str) -> list:
    """
    Extract all unique tickers from a massive_cache date file.
    
    Args:
        date_str: Date in YYYY-MM-DD format
        
    Returns:
        Sorted list of unique ticker symbols
    """
    filepath = Path(f"massive_cache/{date_str}.csv.gz")
    
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    
    print(f"📂 Reading {filepath}...")
    
    # Read the CSV file
    with gzip.open(filepath, 'rt') as f:
        df = pd.read_csv(f)
    
    # Extract unique tickers
    if 'ticker' not in df.columns:
        raise ValueError(f"'ticker' column not found in {filepath}")
    
    # Convert to string and remove any NaN values
    tickers = df['ticker'].dropna().astype(str).unique()
    tickers = sorted([t for t in tickers if t and t != 'nan'])
    
    print(f"✅ Found {len(tickers)} unique tickers")
    
    return tickers


def split_into_batches(tickers: list, batch_size: int = 1000) -> list:
    """
    Split ticker list into batches of specified size.
    
    Args:
        tickers: List of ticker symbols
        batch_size: Number of tickers per batch
        
    Returns:
        List of batches (each batch is a list of tickers)
    """
    batches = []
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i + batch_size]
        batches.append(batch)
    
    return batches


def save_batch_files(batches: list, output_dir: str = "ticker_lists") -> list:
    """
    Save ticker batches to individual files.
    
    Args:
        batches: List of ticker batches
        output_dir: Directory to save batch files
        
    Returns:
        List of created file paths
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    created_files = []
    
    for i, batch in enumerate(batches, 1):
        filename = output_path / f"massive_batch_{i:02d}.txt"
        
        with open(filename, 'w') as f:
            for ticker in batch:
                f.write(f"{ticker}\n")
        
        created_files.append(filename)
        print(f"  ✅ Created {filename} ({len(batch)} tickers)")
    
    return created_files


def main():
    parser = argparse.ArgumentParser(
        description='Extract tickers from massive_cache and create batch files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use most recent file (default: 2025-12-11)
  python extract_massive_tickers.py
  
  # Specify different date
  python extract_massive_tickers.py --date 2025-12-01
  
  # Create smaller batches (500 tickers each)
  python extract_massive_tickers.py --batch-size 500
  
  # Custom output directory
  python extract_massive_tickers.py --output-dir my_batches
  
After creating batches, populate cache with:
  python populate_cache_bulk.py --ticker-files ticker_lists/massive_batch_01.txt --months 24 --use-duckdb
        """
    )
    
    parser.add_argument(
        '--date',
        type=str,
        default='2025-12-11',
        help='Date of massive_cache file to read (YYYY-MM-DD format, default: 2025-12-11)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=1000,
        help='Number of tickers per batch file (default: 1000)'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='ticker_lists',
        help='Output directory for batch files (default: ticker_lists)'
    )
    parser.add_argument(
        '--preview',
        action='store_true',
        help='Preview tickers without creating files'
    )
    
    args = parser.parse_args()
    
    print("="*70)
    print("MASSIVE CACHE TICKER EXTRACTOR")
    print("="*70)
    print()
    
    try:
        # Extract tickers
        tickers = extract_tickers_from_massive_file(args.date)
        
        # Show sample
        print(f"\n📋 Sample tickers (first 10):")
        for ticker in tickers[:10]:
            print(f"   {ticker}")
        if len(tickers) > 10:
            print(f"   ... and {len(tickers) - 10} more")
        
        # Split into batches
        batches = split_into_batches(tickers, args.batch_size)
        num_batches = len(batches)
        
        print(f"\n📦 Will create {num_batches} batch files:")
        for i, batch in enumerate(batches, 1):
            batch_num = f"{i:02d}"
            print(f"   massive_batch_{batch_num}.txt - {len(batch)} tickers")
        
        # Preview mode - stop here
        if args.preview:
            print("\n👁️  Preview mode - no files created")
            return
        
        # Confirm before creating files
        print()
        response = input(f"Create {num_batches} batch files in {args.output_dir}/? (y/n): ")
        if response.lower() != 'y':
            print("❌ Cancelled")
            return
        
        # Save batch files
        print(f"\n💾 Creating batch files...")
        created_files = save_batch_files(batches, args.output_dir)
        
        # Summary
        print("\n" + "="*70)
        print("✅ BATCH FILES CREATED")
        print("="*70)
        print(f"\nTotal tickers:  {len(tickers)}")
        print(f"Batch files:    {len(created_files)}")
        print(f"Batch size:     ~{args.batch_size} tickers")
        print(f"Location:       {args.output_dir}/")
        
        print("\n📖 Next Steps:")
        print("\n1. Build DuckDB index (one-time, 30-60 seconds):")
        print("   python scripts/build_massive_index.py")
        
        print("\n2. Populate cache in batches (with DuckDB for speed):")
        for i in range(1, min(4, len(created_files) + 1)):
            print(f"   python populate_cache_bulk.py --ticker-files {args.output_dir}/massive_batch_{i:02d}.txt --months 24 --use-duckdb")
        if len(created_files) > 3:
            print(f"   ... continue through massive_batch_{len(created_files):02d}.txt")
        
        print("\n3. Run momentum screening on completed batches:")
        print(f"   python momentum_screener.py --file {args.output_dir}/massive_batch_01.txt")
        
    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        print("\nAvailable dates in massive_cache:")
        cache_path = Path("massive_cache")
        if cache_path.exists():
            files = sorted(cache_path.glob("*.csv.gz"))
            recent = files[-5:] if len(files) > 5 else files
            for f in recent:
                date = f.stem  # Remove .csv.gz
                print(f"   {date}")
        return 1
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
