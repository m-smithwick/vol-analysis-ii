#!/usr/bin/env python3
"""
Build DuckDB index from massive_cache for fast ticker queries.

This script creates a DuckDB database that indexes all data in massive_cache/
for O(1) ticker lookups instead of O(days) CSV decompression operations.

Usage:
    python scripts/build_massive_index.py [--rebuild]

Options:
    --rebuild    Force rebuild even if index exists
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import duckdb
except ImportError:
    print("❌ DuckDB not installed. Install with: pip install duckdb")
    sys.exit(1)


def build_duckdb_index(rebuild: bool = False) -> None:
    """
    Build DuckDB index from massive_cache CSV.GZ files.
    
    Args:
        rebuild: If True, rebuild even if index exists
    """
    index_path = Path('massive_index.duckdb')
    massive_cache = Path('massive_cache')
    
    # Check if massive_cache exists
    if not massive_cache.exists():
        print("❌ massive_cache/ directory not found")
        print("   Run populate_cache_bulk.py first to download data")
        sys.exit(1)
    
    # Count files
    csv_files = list(massive_cache.glob('*.csv.gz'))
    if not csv_files:
        print("❌ No CSV.GZ files found in massive_cache/")
        sys.exit(1)
    
    # Check if index already exists
    if index_path.exists() and not rebuild:
        print(f"ℹ️  Index already exists at {index_path}")
        print("   Use --rebuild to force rebuild")
        sys.exit(0)
    
    print("="*70)
    print("BUILDING DUCKDB INDEX FROM MASSIVE_CACHE")
    print("="*70)
    print(f"\nFound {len(csv_files)} daily files in massive_cache/")
    print(f"Date range: {min(csv_files).stem} to {max(csv_files).stem}")
    
    start_time = datetime.now()
    
    # Connect to DuckDB
    print(f"\n1. Connecting to DuckDB...")
    con = duckdb.connect(str(index_path))
    
    try:
        # Drop existing table if rebuilding
        if rebuild:
            print("   Dropping existing table...")
            con.execute("DROP TABLE IF EXISTS daily_data")
        
        # Create table from all CSV.GZ files
        # DuckDB can read gzip directly - NO manual decompression needed!
        print("\n2. Creating indexed table from CSV.GZ files...")
        print("   (This may take 30-60 seconds for 500+ days of data)")
        
        con.execute(r"""
            CREATE TABLE IF NOT EXISTS daily_data AS 
            SELECT 
                ticker,
                window_start as timestamp_ns,
                EPOCH_MS(CAST(window_start / 1000000 AS BIGINT)) as date,
                open, 
                high, 
                low, 
                close, 
                volume,
                -- Extract date from filename for metadata
                regexp_extract(filename, '(\d{4}-\d{2}-\d{2})', 1) as file_date
            FROM read_csv_auto(
                'massive_cache/*.csv.gz',
                filename=true,
                union_by_name=true,
                ignore_errors=false
            )
            WHERE ticker IS NOT NULL
        """)
        
        # Get row count
        row_count = con.execute("SELECT COUNT(*) FROM daily_data").fetchone()[0]
        ticker_count = con.execute("SELECT COUNT(DISTINCT ticker) FROM daily_data").fetchone()[0]
        
        print(f"   ✅ Loaded {row_count:,} records for {ticker_count:,} tickers")
        
        # Create indexes for fast queries
        print("\n3. Creating indexes for fast queries...")
        
        print("   - Creating ticker index...")
        con.execute("CREATE INDEX IF NOT EXISTS idx_ticker ON daily_data(ticker)")
        
        print("   - Creating date index...")
        con.execute("CREATE INDEX IF NOT EXISTS idx_date ON daily_data(date)")
        
        print("   - Creating composite ticker+date index...")
        con.execute("CREATE INDEX IF NOT EXISTS idx_ticker_date ON daily_data(ticker, date)")
        
        # Analyze for query optimization
        print("\n4. Running ANALYZE for query optimization...")
        con.execute("ANALYZE daily_data")
        
        # Get date range
        date_range = con.execute("""
            SELECT 
                MIN(date) as min_date, 
                MAX(date) as max_date,
                COUNT(DISTINCT date) as trading_days
            FROM daily_data
        """).fetchone()
        
        min_date, max_date, trading_days = date_range
        
        # Get file size
        file_size_mb = index_path.stat().st_size / 1024 / 1024
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        print("\n" + "="*70)
        print("✅ DUCKDB INDEX BUILD COMPLETE")
        print("="*70)
        print(f"\nIndex Statistics:")
        print(f"  Database file:   {index_path}")
        print(f"  File size:       {file_size_mb:.1f} MB")
        print(f"  Total records:   {row_count:,}")
        print(f"  Unique tickers:  {ticker_count:,}")
        print(f"  Trading days:    {trading_days}")
        print(f"  Date range:      {min_date} to {max_date}")
        print(f"  Build time:      {elapsed:.1f} seconds")
        print(f"\nPerformance:")
        print(f"  Records/sec:     {int(row_count / elapsed):,}")
        print(f"  Avg time/day:    {elapsed / len(csv_files):.2f}s")
        
        print(f"\n🚀 Ready for fast queries!")
        print(f"   Test with: python scripts/query_massive_index.py AAPL")
        
    except Exception as e:
        print(f"\n❌ Error building index: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        con.close()


def main():
    parser = argparse.ArgumentParser(
        description='Build DuckDB index from massive_cache',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Build index (first time)
  python scripts/build_massive_index.py
  
  # Rebuild existing index
  python scripts/build_massive_index.py --rebuild
        """
    )
    
    parser.add_argument(
        '--rebuild',
        action='store_true',
        help='Force rebuild even if index exists'
    )
    
    args = parser.parse_args()
    
    build_duckdb_index(rebuild=args.rebuild)


if __name__ == "__main__":
    main()
