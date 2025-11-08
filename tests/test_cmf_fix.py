#!/usr/bin/env python3
"""Test accumulation score fix - verifies CMF_Z is not overwritten."""

import pandas as pd
import yfinance as yf
import volume_features
import indicators
import signal_generator

print("=" * 70)
print("TESTING ACCUMULATION SCORE FIX")
print("=" * 70)

# Download sample data
print("\nDownloading AAPL data...")
df = yf.download("AAPL", period="1mo", interval="1d", auto_adjust=True)
if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.droplevel(1)
df.dropna(inplace=True)
print(f"Downloaded {len(df)} days\n")

# Calculate CMF_Z first
print("Step 1: Calculate CMF_Z...")
df['CMF_20'] = volume_features.calculate_cmf(df, period=20)
df['CMF_Z'] = volume_features.calculate_cmf_zscore(df, cmf_period=20, zscore_window=20)
print(f"  CMF_Z range: {df['CMF_Z'].min():.4f} to {df['CMF_Z'].max():.4f}")
print(f"  NaN count: {df['CMF_Z'].isna().sum()}")

# Add required columns
df['Volume_MA'] = df['Volume'].rolling(20).mean()
df['Relative_Volume'] = df['Volume'] / df['Volume_MA']
df['VWAP'] = indicators.calculate_vwap(df)
df['Above_VWAP'] = df['Close'] > df['VWAP']
df['Support_Level'] = df['Low'].rolling(20).min()
df['Near_Support'] = df['Close'] <= df['Support_Level'] * 1.05
df['Volume_Spike'] = df['Volume'] > (df['Volume_MA'] * 1.5)
df['TR'], df['ATR20'] = indicators.calculate_atr(df, period=20)

# Run standardize_features (THE FIX TEST)
print("\nStep 2: Run standardize_features (should NOT overwrite CMF_Z)...")
df = indicators.standardize_features(df, window=20)
print(f"  CMF_Z range: {df['CMF_Z'].min():.4f} to {df['CMF_Z'].max():.4f}")
print(f"  NaN count: {df['CMF_Z'].isna().sum()}")

# Calculate accumulation score
print("\nStep 3: Calculate accumulation scores...")
df['Accumulation_Score'] = signal_generator.calculate_accumulation_score(df)
print(f"  Score range: {df['Accumulation_Score'].min():.2f} to {df['Accumulation_Score'].max():.2f}")
print(f"  Score mean: {df['Accumulation_Score'].mean():.2f}")
print(f"  Score std: {df['Accumulation_Score'].std():.2f}")

# Check if scores are varying (not flat-lined)
score_variance = df['Accumulation_Score'].var()
print(f"\n✅ TEST RESULT:")
if score_variance > 0.1:
    print(f"  ✅ PASS - Scores are varying (variance={score_variance:.4f})")
    print(f"  ✅ Accumulation scores are working correctly!")
else:
    print(f"  ❌ FAIL - Scores are flat-lined (variance={score_variance:.4f})")
    print(f"  ❌ Bug still present!")

print("\nLast 5 days:")
print(df[['Close', 'CMF_Z', 'Accumulation_Score']].tail())
