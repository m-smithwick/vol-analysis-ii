"""
DuckDB-based provider for querying massive_cache data.

This module provides a high-performance interface to query the massive_cache
using DuckDB indexes instead of sequential CSV decompression.

Performance:
    - Single ticker query: ~0.1s (vs ~5-10s with CSV decompression)
    - Multi-ticker query: ~0.5s for 50 tickers (vs minutes with CSV)
    - Incremental updates: ~1s per day (vs ~30s with Parquet rewrite)
"""

import pandas as pd
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from datetime import datetime
import gzip

try:
    import duckdb
except ImportError:
    raise ImportError(
        "DuckDB not installed. Install with: pip install duckdb\n"
        "This module provides 10-20x faster queries than CSV decompression."
    )


class MassiveDuckDBProvider:
    """
    Query massive_cache data using DuckDB for high-performance ticker filtering.
    
    This provider uses a DuckDB index built from massive_cache/ to enable
    fast queries without decompressing hundreds of CSV.GZ files.
    
    Example:
        provider = MassiveDuckDBProvider()
        
        # Get single ticker
        df = provider.get_ticker_data('AAPL', '2024-01-01', '2024-12-31')
        
        # Get multiple tickers (much faster than sequential)
        data = provider.get_multiple_tickers(['AAPL', 'MSFT', 'GOOGL'])
    """
    
    def __init__(self, db_path: str = 'massive_index.duckdb'):
        """
        Initialize provider with DuckDB database path.
        
        Args:
            db_path: Path to DuckDB index file
        
        Raises:
            FileNotFoundError: If DuckDB index doesn't exist
        """
        self.db_path = Path(db_path)
        self._con = None
        
        if not self.db_path.exists():
            raise FileNotFoundError(
                f"DuckDB index not found at {self.db_path}\n"
                f"Build index first with: python scripts/build_massive_index.py"
            )
    
    @property
    def con(self) -> duckdb.DuckDBPyConnection:
        """Lazy connection - only open when needed."""
        if self._con is None:
            self._con = duckdb.connect(str(self.db_path), read_only=True)
        return self._con
    
    def get_ticker_data(
        self, 
        ticker: str, 
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Get data for a single ticker.
        
        Args:
            ticker: Stock symbol (e.g., 'AAPL')
            start_date: Start date in 'YYYY-MM-DD' format (optional)
            end_date: End date in 'YYYY-MM-DD' format (optional)
        
        Returns:
            DataFrame in yfinance format:
                Index: Date (datetime)
                Columns: Open, High, Low, Close, Volume
        
        Example:
            df = provider.get_ticker_data('AAPL', '2024-01-01', '2024-12-31')
        """
        query = """
            SELECT 
                date, 
                open, 
                high, 
                low, 
                close, 
                volume 
            FROM daily_data 
            WHERE ticker = ?
        """
        params = [ticker.upper()]
        
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
        
        query += " ORDER BY date"
        
        df = self.con.execute(query, params).df()
        
        if df.empty:
            return pd.DataFrame()
        
        # Convert to yfinance format
        df = df.rename(columns={
            'date': 'Date',
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume'
        })
        df.set_index('Date', inplace=True)
        
        # Ensure timezone-naive for consistency with rest of system
        if df.index.tzinfo is not None:
            df.index = df.index.tz_localize(None)
        
        return df
    
    def get_multiple_tickers(
        self, 
        tickers: List[str], 
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        Get data for multiple tickers in ONE query (much faster than sequential).
        
        Args:
            tickers: List of stock symbols
            start_date: Start date in 'YYYY-MM-DD' format (optional)
            end_date: End date in 'YYYY-MM-DD' format (optional)
        
        Returns:
            Dictionary mapping ticker -> DataFrame
        
        Example:
            data = provider.get_multiple_tickers(['AAPL', 'MSFT', 'GOOGL'])
            aapl_df = data['AAPL']
        """
        if not tickers:
            return {}
        
        # Normalize to uppercase
        tickers = [t.upper() for t in tickers]
        
        # Create parameterized query for SQL injection safety
        placeholders = ','.join(['?'] * len(tickers))
        query = f"""
            SELECT 
                ticker, 
                date, 
                open, 
                high, 
                low, 
                close, 
                volume 
            FROM daily_data 
            WHERE ticker IN ({placeholders})
        """
        params = list(tickers)
        
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
        
        query += " ORDER BY ticker, date"
        
        df = self.con.execute(query, params).df()
        
        if df.empty:
            return {ticker: pd.DataFrame() for ticker in tickers}
        
        # Split into dictionary of DataFrames by ticker
        result = {}
        for ticker in df['ticker'].unique():
            ticker_df = df[df['ticker'] == ticker].drop('ticker', axis=1)
            ticker_df = ticker_df.rename(columns={
                'date': 'Date',
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'volume': 'Volume'
            })
            ticker_df.set_index('Date', inplace=True)
            
            # Ensure timezone-naive
            if ticker_df.index.tzinfo is not None:
                ticker_df.index = ticker_df.index.tz_localize(None)
            
            result[ticker] = ticker_df
        
        # Add empty DataFrames for tickers with no data
        for ticker in tickers:
            if ticker not in result:
                result[ticker] = pd.DataFrame()
        
        return result
    
    def get_date_range(self) -> Tuple[datetime, datetime]:
        """
        Get min/max dates available in the database.
        
        Returns:
            Tuple of (min_date, max_date)
        
        Example:
            min_date, max_date = provider.get_date_range()
            print(f"Data available from {min_date} to {max_date}")
        """
        result = self.con.execute("""
            SELECT 
                MIN(date) as min_date, 
                MAX(date) as max_date 
            FROM daily_data
        """).fetchone()
        
        return result[0], result[1]
    
    def get_ticker_list(self) -> List[str]:
        """
        Get list of all tickers in the database.
        
        Returns:
            Sorted list of ticker symbols
        
        Example:
            all_tickers = provider.get_ticker_list()
            print(f"Database contains {len(all_tickers)} tickers")
        """
        result = self.con.execute("""
            SELECT DISTINCT ticker 
            FROM daily_data 
            ORDER BY ticker
        """).df()
        
        return result['ticker'].tolist()
    
    def get_stats(self) -> Dict[str, any]:
        """
        Get database statistics.
        
        Returns:
            Dictionary with stats about the database
        
        Example:
            stats = provider.get_stats()
            print(f"Total records: {stats['total_records']:,}")
        """
        stats_query = self.con.execute("""
            SELECT 
                COUNT(*) as total_records,
                COUNT(DISTINCT ticker) as unique_tickers,
                COUNT(DISTINCT date) as trading_days,
                MIN(date) as earliest_date,
                MAX(date) as latest_date
            FROM daily_data
        """).fetchone()
        
        return {
            'total_records': stats_query[0],
            'unique_tickers': stats_query[1],
            'trading_days': stats_query[2],
            'earliest_date': stats_query[3],
            'latest_date': stats_query[4],
            'db_size_mb': self.db_path.stat().st_size / 1024 / 1024
        }
    
    def add_new_day(self, date_str: str) -> int:
        """
        Add a new day's data incrementally to the index.
        
        This is called after downloading a new massive_cache/YYYY-MM-DD.csv.gz file.
        Uses INSERT for true incremental updates (no full rewrite needed).
        
        Args:
            date_str: Date string in 'YYYY-MM-DD' format
        
        Returns:
            Number of records added
        
        Example:
            records_added = provider.add_new_day('2025-12-01')
            print(f"Added {records_added} records for 2025-12-01")
        """
        file_path = f"massive_cache/{date_str}.csv.gz"
        
        if not Path(file_path).exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Need write access for INSERT
        con = duckdb.connect(str(self.db_path))
        
        try:
            # Check if date already exists
            existing = con.execute(
                "SELECT COUNT(*) FROM daily_data WHERE file_date = ?",
                [date_str]
            ).fetchone()[0]
            
            if existing > 0:
                print(f"⚠️  Date {date_str} already in database ({existing} records)")
                return 0
            
            # Insert new day's data
            con.execute(fr"""
                INSERT INTO daily_data
                SELECT 
                    ticker,
                    window_start as timestamp_ns,
                    EPOCH_MS(CAST(window_start / 1000000 AS BIGINT)) as date,
                    open, 
                    high, 
                    low, 
                    close, 
                    volume,
                    '{date_str}' as file_date
                FROM read_csv_auto(
                    '{file_path}',
                    union_by_name=true
                )
                WHERE ticker IS NOT NULL
            """)
            
            # Get count of records added
            added = con.execute(
                "SELECT COUNT(*) FROM daily_data WHERE file_date = ?",
                [date_str]
            ).fetchone()[0]
            
            return added
            
        finally:
            con.close()
    
    def check_ticker_coverage(self, ticker: str) -> Dict[str, any]:
        """
        Check what date range is available for a specific ticker.
        
        Args:
            ticker: Stock symbol
        
        Returns:
            Dictionary with coverage info
        
        Example:
            coverage = provider.check_ticker_coverage('AAPL')
            print(f"AAPL data: {coverage['start_date']} to {coverage['end_date']}")
        """
        result = self.con.execute("""
            SELECT 
                MIN(date) as start_date,
                MAX(date) as end_date,
                COUNT(*) as record_count
            FROM daily_data
            WHERE ticker = ?
        """, [ticker.upper()]).fetchone()
        
        if result[0] is None:
            return {
                'ticker': ticker,
                'available': False,
                'start_date': None,
                'end_date': None,
                'record_count': 0
            }
        
        return {
            'ticker': ticker,
            'available': True,
            'start_date': result[0],
            'end_date': result[1],
            'record_count': result[2]
        }
    
    def close(self):
        """Close the database connection."""
        if self._con is not None:
            self._con.close()
            self._con = None
    
    def __del__(self):
        """Ensure connection is closed on deletion."""
        self.close()
    
    def __enter__(self):
        """Context manager support."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager support."""
        self.close()


# Convenience function for quick queries
def quick_query(ticker: str, start_date: Optional[str] = None, 
                end_date: Optional[str] = None) -> pd.DataFrame:
    """
    Quick convenience function for single ticker queries.
    
    Args:
        ticker: Stock symbol
        start_date: Start date (optional)
        end_date: End date (optional)
    
    Returns:
        DataFrame with ticker data
    
    Example:
        df = quick_query('AAPL', '2024-01-01', '2024-12-31')
    """
    with MassiveDuckDBProvider() as provider:
        return provider.get_ticker_data(ticker, start_date, end_date)
