#!/usr/bin/env python3
"""
Test script for bulk Massive.com data processing.
Downloads a single day, splits by our tickers vs others, and tests recompression.
"""

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
import pandas as pd
import gzip
from io import BytesIO
from datetime import datetime
import os
from pathlib import Path
import time

print("="*70)
print("MASSIVE.COM BULK PROCESSING TEST - SINGLE DAY")
print("="*70)

# ============================================================================
# STEP 1: Collect all our tickers from ticker files
# ============================================================================
print("\n1. Collecting tickers from all ticker files...")

def read_ticker_file(filepath):
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

# Known ticker files
ticker_files = ['stocks.txt', 'ibd.txt', 'ibd20.txt', 'ltl.txt', 'cmb.txt', 'short.txt']
all_tickers = set()

for file in ticker_files:
    tickers = read_ticker_file(file)
    if tickers:
        print(f"   {file:15s}: {len(tickers):3d} tickers")
        all_tickers.update(tickers)

print(f"\n   Total unique tickers: {len(all_tickers)}")
print(f"   Sample tickers: {sorted(list(all_tickers))[:10]}")

# ============================================================================
# STEP 2: Download single day's data
# ============================================================================
print("\n2. Downloading single day's data from Massive.com...")

# Initialize S3 client
session = boto3.Session(profile_name='massive')
s3 = session.client(
    's3',
    endpoint_url='https://files.massive.com',
    config=Config(signature_version='s3v4'),
)

bucket = 'flatfiles'
test_date = '2025-11-11'
object_key = f'us_stocks_sip/day_aggs_v1/2025/11/{test_date}.csv.gz'

print(f"   Date: {test_date}")
print(f"   Object key: {object_key}")

start_time = time.time()

try:
    # Download the file
    response = s3.get_object(Bucket=bucket, Key=object_key)
    download_time = time.time() - start_time
    
    compressed_size = len(response['Body'].read())
    response['Body'] = s3.get_object(Bucket=bucket, Key=object_key)['Body']  # Reset stream
    
    print(f"   ✅ Downloaded: {compressed_size:,} bytes ({compressed_size/(1024*1024):.2f} MB)")
    print(f"   Download time: {download_time:.1f}s")
    
    # Decompress and parse
    print("\n3. Decompressing and parsing CSV...")
    parse_start = time.time()
    
    with gzip.GzipFile(fileobj=BytesIO(response['Body'].read())) as gz:
        df = pd.read_csv(gz)
    
    parse_time = time.time() - parse_start
    
    print(f"   ✅ Parsed {len(df):,} rows")
    print(f"   Parse time: {parse_time:.1f}s")
    print(f"   Columns: {list(df.columns)}")
    print(f"   Unique tickers in file: {df['ticker'].nunique():,}")
    print(f"   Memory usage: {df.memory_usage(deep=True).sum()/(1024*1024):.1f} MB")
    
    # Show sample
    print("\n   Sample data:")
    print(df.head(3).to_string())

except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# ============================================================================
# STEP 4: Split data into our tickers vs others
# ============================================================================
print("\n4. Splitting data by our tickers vs others...")

split_start = time.time()

# Split the data
our_mask = df['ticker'].isin(all_tickers)
our_data = df[our_mask].copy()
other_data = df[~our_mask].copy()

split_time = time.time() - split_start

print(f"   Split time: {split_time:.2f}s")
print(f"   Our tickers: {len(our_data):,} rows ({our_data['ticker'].nunique()} tickers)")
print(f"   Other tickers: {len(other_data):,} rows ({other_data['ticker'].nunique()} tickers)")

# Show which of our tickers are in this day's data
our_tickers_found = set(our_data['ticker'].unique())
our_tickers_missing = all_tickers - our_tickers_found
print(f"\n   Our tickers found: {len(our_tickers_found)}/{len(all_tickers)}")
if our_tickers_missing:
    print(f"   Missing tickers: {sorted(list(our_tickers_missing))[:10]}")

# ============================================================================
# STEP 5: Save our tickers to data_cache (uncompressed)
# ============================================================================
print("\n5. Saving our tickers to data_cache/...")

# Create data_cache directory
cache_dir = Path('data_cache')
cache_dir.mkdir(exist_ok=True)

save_start = time.time()

def convert_to_yfinance_format(ticker_df, ticker):
    """Convert Massive format to yfinance format."""
    if ticker_df.empty:
        return pd.DataFrame()
    
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

# Save each ticker
saved_count = 0
for ticker in our_tickers_found:
    ticker_data = our_data[our_data['ticker'] == ticker]
    converted = convert_to_yfinance_format(ticker_data, ticker)
    
    if not converted.empty:
        cache_file = cache_dir / f"{ticker}_1d_data.csv"
        converted.to_csv(cache_file)
        saved_count += 1

save_time = time.time() - save_start

print(f"   ✅ Saved {saved_count} ticker files")
print(f"   Save time: {save_time:.2f}s")
print(f"   Example: {cache_dir / 'AI_1d_data.csv'}")

# Show sample of saved file
if (cache_dir / 'AI_1d_data.csv').exists():
    sample_df = pd.read_csv(cache_dir / 'AI_1d_data.csv', index_col=0, nrows=3)
    print("\n   Sample saved file (AI):")
    print(sample_df.to_string())

# ============================================================================
# STEP 6: Recompress and save other tickers to massive_cache
# ============================================================================
print("\n6. Recompressing other tickers to massive_cache/...")

# Create massive_cache directory
massive_cache_dir = Path('massive_cache')
massive_cache_dir.mkdir(exist_ok=True)

recompress_start = time.time()

# Save to compressed file
cache_file = massive_cache_dir / f"{test_date}.csv.gz"
with gzip.open(cache_file, 'wt') as f:
    other_data.to_csv(f, index=False)

recompress_time = time.time() - recompress_start
recompressed_size = os.path.getsize(cache_file)

print(f"   ✅ Saved: {cache_file}")
print(f"   Size: {recompressed_size:,} bytes ({recompressed_size/(1024*1024):.2f} MB)")
print(f"   Recompress time: {recompress_time:.2f}s")
print(f"   Compression ratio: {len(other_data.to_csv(index=False))/recompressed_size:.1f}x")

# ============================================================================
# STEP 7: Summary
# ============================================================================
print("\n" + "="*70)
print("📊 SUMMARY")
print("="*70)

total_time = time.time() - start_time

print(f"\nTiming Breakdown:")
print(f"  Download:      {download_time:6.2f}s")
print(f"  Parse:         {parse_time:6.2f}s")
print(f"  Split:         {split_time:6.2f}s")
print(f"  Save our data: {save_time:6.2f}s")
print(f"  Recompress:    {recompress_time:6.2f}s")
print(f"  {'─'*25}")
print(f"  Total:         {total_time:6.2f}s")

print(f"\nData Processing:")
print(f"  Total rows:      {len(df):,}")
print(f"  Our tickers:     {len(our_data):,} rows ({len(our_tickers_found)} tickers)")
print(f"  Other tickers:   {len(other_data):,} rows ({other_data['ticker'].nunique()} tickers)")

print(f"\nStorage:")
print(f"  Original (compressed):    {compressed_size/(1024*1024):.2f} MB")
print(f"  Our cache (uncompressed): ~{saved_count * 0.001:.2f} MB (est.)")
print(f"  Others (recompressed):    {recompressed_size/(1024*1024):.2f} MB")

print(f"\nScalability Estimate (24 months = ~500 trading days):")
print(f"  Total download time: ~{(download_time * 500)/60:.0f} minutes")
print(f"  Total process time:  ~{(total_time * 500)/60:.0f} minutes")

print("\n✅ Single-day bulk processing test completed successfully!")
print("="*70)
