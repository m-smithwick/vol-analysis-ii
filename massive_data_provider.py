"""
Massive.com flat file data provider for daily stock data.

This module provides access to Massive.com (formerly Polygon) flat files
via S3-compatible API, serving as an alternative data source to yfinance.
"""

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
import pandas as pd
import gzip
from io import BytesIO
from datetime import datetime, timedelta
from typing import Optional
import os

from error_handler import (
    ErrorContext, DataValidationError, setup_logging, logger
)

# Configure logging
setup_logging()

class MassiveDataProvider:
    """
    Provider for accessing Massive.com flat files via S3.
    
    Handles authentication, file discovery, downloading, and parsing
    of daily aggregate stock data from Massive.com flat files.
    """
    
    def __init__(self, profile_name: str = "massive", use_local_cache: bool = True):
        """
        Initialize the Massive data provider.
        
        Args:
            profile_name (str): AWS credentials profile name (default: "massive")
            use_local_cache (bool): Whether to check local cache before downloading (default: True)
        """
        with ErrorContext("initializing Massive data provider"):
            try:
                # Create boto3 session with profile
                self.session = boto3.Session(profile_name=profile_name)
                
                # Create S3 client with Massive.com endpoint
                self.s3 = self.session.client(
                    's3',
                    endpoint_url='https://files.massive.com',
                    config=Config(signature_version='s3v4')
                )
                
                self.bucket_name = 'flatfiles'
                self.prefix = 'us_stocks_sip/day_aggs_v1/'
                self.use_local_cache = use_local_cache
                self.local_cache_dir = 'massive_cache'
                
                # Create local cache directory if it doesn't exist
                if self.use_local_cache:
                    os.makedirs(self.local_cache_dir, exist_ok=True)
                
                logger.info("Initialized Massive.com data provider")
                
            except Exception as e:
                raise DataValidationError(f"Failed to initialize Massive provider: {e}")
    
    def _get_file_path(self, date: datetime) -> str:
        """
        Get the S3 object key for a specific date.
        
        Flat files are organized as: us_stocks_sip/day_aggs_v1/YYYY/MM/YYYY-MM-DD.csv.gz
        
        Args:
            date (datetime): Date to get file path for
            
        Returns:
            str: S3 object key
        """
        return f"{self.prefix}{date.year}/{date.month:02d}/{date.strftime('%Y-%m-%d')}.csv.gz"
    
    def _get_local_file_path(self, date: datetime) -> str:
        """
        Get the local cache file path for a specific date.
        
        Args:
            date (datetime): Date to get file path for
            
        Returns:
            str: Local file path
        """
        return os.path.join(self.local_cache_dir, f"{date.strftime('%Y-%m-%d')}.csv.gz")
    
    def _download_file(self, object_key: str, date: datetime) -> Optional[pd.DataFrame]:
        """
        Download and parse a single flat file from S3 or local cache.
        
        Checks local cache first if enabled, only downloads from S3 if not found locally.
        
        Args:
            object_key (str): S3 object key to download
            date (datetime): Date for the file (used for local cache lookup)
            
        Returns:
            Optional[pd.DataFrame]: Parsed data or None if file doesn't exist
        """
        with ErrorContext("loading flat file", object_key=object_key):
            # Check local cache first if enabled
            if self.use_local_cache:
                local_path = self._get_local_file_path(date)
                if os.path.exists(local_path):
                    try:
                        # Read from local cache
                        with gzip.open(local_path, 'rt') as gz:
                            df = pd.read_csv(gz)
                        logger.debug(f"Loaded {len(df)} records from local cache: {local_path}")
                        return df
                    except Exception as e:
                        logger.warning(f"Error reading local cache {local_path}: {e}, will try S3")
                        # Fall through to S3 download
            
            # Download from S3 if not in local cache or local cache disabled
            try:
                # Download the file
                response = self.s3.get_object(Bucket=self.bucket_name, Key=object_key)
                file_content = response['Body'].read()
                
                # Decompress and read CSV
                with gzip.GzipFile(fileobj=BytesIO(file_content)) as gz:
                    df = pd.read_csv(gz)
                
                logger.debug(f"Downloaded {len(df)} records from S3: {object_key}")
                
                # Save to local cache if enabled
                if self.use_local_cache:
                    local_path = self._get_local_file_path(date)
                    try:
                        with open(local_path, 'wb') as f:
                            f.write(file_content)
                        logger.debug(f"Saved to local cache: {local_path}")
                    except Exception as e:
                        logger.warning(f"Failed to save to local cache: {e}")
                
                return df
                
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchKey':
                    logger.debug(f"File not found on S3: {object_key}")
                    return None
                else:
                    logger.error(f"S3 error downloading {object_key}: {e}")
                    raise DataValidationError(f"Failed to download file: {e}")
            except Exception as e:
                logger.error(f"Error processing {object_key}: {e}")
                raise DataValidationError(f"Failed to process file: {e}")
    
    def _convert_to_yfinance_format(self, df: pd.DataFrame, ticker: str) -> pd.DataFrame:
        """
        Convert Massive.com flat file format to yfinance format.
        
        Massive format columns: ticker, volume, open, close, high, low, window_start, transactions
        yfinance format columns: Open, High, Low, Close, Volume (index: Date)
        
        Args:
            df (pd.DataFrame): Data in Massive format
            ticker (str): Stock ticker to filter for
            
        Returns:
            pd.DataFrame: Data in yfinance-compatible format
        """
        with ErrorContext("converting data format", ticker=ticker):
            # Filter for specific ticker
            ticker_df = df[df['ticker'] == ticker].copy()
            
            if ticker_df.empty:
                logger.warning(f"No data found for ticker {ticker} in flat file")
                return pd.DataFrame()
            
            # Convert window_start from nanoseconds to datetime
            ticker_df['Date'] = pd.to_datetime(ticker_df['window_start'], unit='ns')
            
            # Rename columns to match yfinance format
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
            
            # Ensure timezone-naive (consistent with yfinance)
            if ticker_df.index.tzinfo is not None:
                ticker_df.index = ticker_df.index.tz_localize(None)
            
            logger.debug(f"Converted {len(ticker_df)} records for {ticker}")
            return ticker_df
    
    def get_daily_data(
        self,
        ticker: str,
        start_date: datetime,
        end_date: datetime
    ) -> pd.DataFrame:
        """
        Get daily stock data from Massive.com flat files.
        
        Args:
            ticker (str): Stock ticker symbol
            start_date (datetime): Start date (inclusive)
            end_date (datetime): End date (inclusive)
            
        Returns:
            pd.DataFrame: Stock data in yfinance format
        """
        with ErrorContext("fetching Massive daily data", ticker=ticker):
            logger.info(f"Fetching Massive.com data for {ticker}: {start_date.date()} to {end_date.date()}")
            
            all_data = []
            current_date = start_date
            
            while current_date <= end_date:
                # Skip weekends (Saturday=5, Sunday=6)
                if current_date.weekday() < 5:
                    object_key = self._get_file_path(current_date)
                    df = self._download_file(object_key, current_date)
                    
                    if df is not None:
                        ticker_df = self._convert_to_yfinance_format(df, ticker)
                        if not ticker_df.empty:
                            all_data.append(ticker_df)
                
                current_date += timedelta(days=1)
            
            if not all_data:
                logger.warning(f"No data found for {ticker} in date range")
                return pd.DataFrame()
            
            # Combine all data
            combined_df = pd.concat(all_data)
            combined_df.sort_index(inplace=True)
            
            logger.info(f"Retrieved {len(combined_df)} days of data for {ticker} from Massive.com")
            return combined_df


def get_massive_daily_data(ticker: str, period: str) -> pd.DataFrame:
    """
    Convenience function to get daily data using period notation.
    
    This function provides a similar interface to yfinance's period parameter
    for compatibility with existing code.
    
    Args:
        ticker (str): Stock ticker symbol
        period (str): Period string (e.g., '6mo', '12mo', '2yr')
        
    Returns:
        pd.DataFrame: Stock data in yfinance format
    """
    with ErrorContext("fetching Massive data by period", ticker=ticker, period=period):
        # Parse period to determine date range
        period_days = {
            '1d': 1, '5d': 5, '1mo': 30, '3mo': 90, '6mo': 180,
            '12mo': 365, '1yr': 365, '2yr': 730, '3yr': 1095,
            '5yr': 1825, '10yr': 3650
        }
        
        days = period_days.get(period.lower(), 365)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Create provider and fetch data
        provider = MassiveDataProvider()
        return provider.get_daily_data(ticker, start_date, end_date)


def test_massive_connection() -> bool:
    """
    Test the connection to Massive.com S3 endpoint.
    
    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        provider = MassiveDataProvider()
        
        # Try to list a single object as a connectivity test
        response = provider.s3.list_objects_v2(
            Bucket=provider.bucket_name,
            Prefix=provider.prefix,
            MaxKeys=1
        )
        
        if 'Contents' in response:
            logger.info("✅ Successfully connected to Massive.com")
            logger.info(f"   Sample file: {response['Contents'][0]['Key']}")
            return True
        else:
            logger.warning("⚠️ Connected but no files found")
            return False
            
    except Exception as e:
        logger.error(f"❌ Failed to connect to Massive.com: {e}")
        return False


if __name__ == "__main__":
    # Test the connection
    print("Testing Massive.com connection...")
    test_massive_connection()
    
    # Try fetching sample data
    print("\nFetching sample data for AAPL...")
    try:
        df = get_massive_daily_data('AAPL', '5d')
        if not df.empty:
            print(f"✅ Retrieved {len(df)} days of data")
            print(df.head())
        else:
            print("⚠️ No data retrieved")
    except Exception as e:
        print(f"❌ Error: {e}")
