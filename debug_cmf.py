#!/usr/bin/env python3
"""Debug CMF calculation to find where NaN values originate."""

import pandas as pd
import yfinance as yf
import volume_features

# Download more data to ensure sufficient window
print("Downloading AAPL data (3 months for sufficient window)...")
df = yf.download("AAPL", period="3mo", interval="1d", auto_adjust=True)
if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.droplevel(1)
df.dropna(inplace=True)
print(f"Downloaded {len(df)} days\n")

# Step-by-step debugging
print("Step 1: Check raw OHLCV data")
print(f"  Close range: {df['Close'].min():.2f} to {df['Close'].max():.2f}")
print(f"  High range: {df['High'].min():.2f} to {df['High'].max():.2f}")
print(f"  Low range: {df['Low'].min():.2f} to {df['Low'].max():.2f}")
print(f"  Volume range: {df['Volume'].min():.0f} to {df['Volume'].max():.0f}")
print(f"  NaN in OHLCV: {df[['Open','High','Low','Close','Volume']].isna().sum().sum()}")

print("\nStep 2: Calculate CMF_20")
df['CMF_20'] = volume_features.calculate_cmf(df, period=20)
print(f"  CMF_20 range: {df['CMF_20'].min():.6f} to {df['CMF_20'].max():.6f}")
print(f"  NaN count: {df['CMF_20'].isna().sum()}")
print(f"  First valid CMF_20 at index: {df['CMF_20'].first_valid_index()}")
print(f"  Sample CMF_20 values (last 5):")
print(df['CMF_20'].tail())

print("\nStep 3: Calculate rolling mean and std")
rolling_mean = df['CMF_20'].rolling(20).mean()
rolling_std = df['CMF_20'].rolling(20).std()
print(f"  Rolling mean range: {rolling_mean.min():.6f} to {rolling_mean.max():.6f}")
print(f"  Rolling std range: {rolling_std.min():.6f} to {rolling_std.max():.6f}")
print(f"  NaN in rolling_mean: {rolling_mean.isna().sum()}")
print(f"  NaN in rolling_std: {rolling_std.isna().sum()}")
print(f"  Zeros in rolling_std: {(rolling_std == 0).sum()}")

print("\nStep 4: Calculate CMF_Z with z-score function")
df['CMF_Z'] = volume_features.calculate_cmf_zscore(df, cmf_period=20, zscore_window=20)
print(f"  CMF_Z range: {df['CMF_Z'].min():.6f} to {df['CMF_Z'].max():.6f}")
print(f"  NaN count: {df['CMF_Z'].isna().sum()}")
print(f"  First valid CMF_Z at index: {df['CMF_Z'].first_valid_index()}")
print(f"  Sample CMF_Z values (last 5):")
print(df[['CMF_20', 'CMF_Z']].tail())

print("\n✅ Diagnosis complete!")
