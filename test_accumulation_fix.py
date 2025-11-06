#!/usr/bin/env python3
"""
Quick test to verify accumulation score fix.
Tests that CMF_Z is calculated correctly and accumulation scores vary properly.
"""

import pandas as pd
import numpy as np
import yfinance as yf

# Import the modules
import volume_features
import indicators
import signal_generator

def test_accumulation_score():
    """Test that accumulation score calculation works properly."""
    
    print("=" * 70)
    print("TESTING ACCUMULATION SCORE FIX")
    print("=" * 70)
    
    # Download sample data
    print("\n📥 Downloading sample data for AAPL (30 days)...")
    ticker = "AAPL"
    df = yf.download(ticker, period="1mo", interval="1d", auto_adjust=True)
    
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
    
    df.dropna(inplace=True)
    
    print(f"✅ Downloaded {len(df)} days of data\n")
    
    # Step 1: Calculate CMF and CMF_Z (as in vol_analysis.py)
    print("🔍 Step 1: Calculating CMF_20 and CMF_Z...")
    df['CMF_20'] = volume_features.calculate_cmf(df, period=20)
    df['CMF_Z'] = volume_features.calculate_cmf_zscore(df, cmf_period=20, zscore_window=20)
    
    cmf_min = df['CMF_20'].min()
    cmf_max = df['CMF_20'].max()
    cmf_z_min = df['CMF_Z'].min()
    cmf_z_max = df['CMF_Z'].max()
    
    print(f"   CMF_20 range: {cmf_min:.4f} to {cmf_max:.4f}")
    print(f"   CMF_Z range: {cmf_z_min:.4f} to {cmf_z_max:.4f}")
    print(f"   CMF_Z has {df['CMF_Z'].isna().sum()} NaN values")
    
    # Step 2: Add required columns for scoring
    print("\n🔍 Step 2: Adding required columns for scoring...")
    df['Volume_MA'] = df['Volume'].rolling(window=20).mean()
    df['Volume_Spike'] = df['Volume'] > (df['Volume_MA'] * 1.5)
    df['Relative_Volume'] = volume_features.calculate_volume_surprise(df, window=20)
    df['VWAP'] = indicators.calculate_vwap(df)
    df['Above_VWAP'] = df['Close'] > df['VWAP']
    df['Support_Level'] = indicators.calculate_support_levels(df, window=20)
    df['Near_Support'] = df['Close'] <= df['Support_Level'] * 1.05
    df['TR'], df['ATR20'] = indicators.calculate_atr(df, period=20)
    
    # Step 3: Run standardize_features (this was causing the bug)
    print("\n🔍 Step 3: Running standardize_features (THE FIX TEST)...")
    print("   CMF_Z before standardize_features:")
    print(f"     Range: {df['CMF_Z'].min():.4f} to {df['CMF_Z'].max():.4f}")
    print(f"     NaN count: {df['CMF_Z'].isna().sum()}")
    
    df = indicators.standardize_features(df, window=20)
    
    print("   CMF_Z after standardize_features:")
    print(f"     Range: {df['CMF_Z'].min():.4f} to {df['CMF_Z'].max():.4f}")
    print(f"     NaN count: {df['CMF_Z'].isna().sum()}")
    
    # Step[ERROR] Failed to process response: The system encountered an unexpected error during processing. Try your request again.
