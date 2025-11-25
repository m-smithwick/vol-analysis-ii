#!/usr/bin/env python3
"""
Test script to verify date tick formatting in plotly charts
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from chart_builder_plotly import generate_analysis_chart

# Create synthetic test data
days = 252  # ~1 year of trading days
dates = pd.date_range(end=datetime.now(), periods=days, freq='B')  # Business days only

# Generate synthetic price data
np.random.seed(42)
base_price = 100
price_returns = np.random.normal(0.001, 0.02, days)
prices = base_price * np.exp(np.cumsum(price_returns))

# Convert to Series for rolling calculations
price_series = pd.Series(prices, index=dates)

# Create DataFrame with all required columns
df = pd.DataFrame({
    'Close': prices,
    'Open': prices * (1 + np.random.uniform(-0.01, 0.01, days)),
    'High': prices * (1 + np.random.uniform(0, 0.02, days)),
    'Low': prices * (1 + np.random.uniform(-0.02, 0, days)),
    'Volume': np.random.randint(1000000, 10000000, days),
    'VWAP': prices * (1 + np.random.uniform(-0.005, 0.005, days)),
    'Support_Level': prices * 0.95,
    'SMA_50': price_series.rolling(50, min_periods=1).mean(),
    'SMA_200': price_series.rolling(200, min_periods=1).mean(),
    'Recent_Swing_Low': prices * 0.97,
    'Recent_Swing_High': prices * 1.03,
    'OBV': np.cumsum(np.random.randint(-1000000, 1000000, days)),
    'AD_Line': np.cumsum(np.random.randint(-500000, 500000, days)),
    'OBV_MA': pd.Series(np.cumsum(np.random.randint(-1000000, 1000000, days))).rolling(20, min_periods=1).mean(),
    'AD_MA': pd.Series(np.cumsum(np.random.randint(-500000, 500000, days))).rolling(20, min_periods=1).mean(),
    'Volume_MA': pd.Series(np.random.randint(1000000, 10000000, days)).rolling(20, min_periods=1).mean(),
    'Phase': np.random.choice(['Neutral', 'Strong_Accumulation', 'Moderate_Accumulation', 'Distribution'], days),
    'Accumulation_Score': np.random.uniform(0, 10, days),
    'Exit_Score': np.random.uniform(0, 10, days),
    'Event_Day': np.random.choice([True, False], days, p=[0.05, 0.95])
}, index=dates)

# Add signal columns (all False for simplicity, except a few True)
signal_columns = [
    'Strong_Buy_display', 'Moderate_Buy_display', 'Stealth_Accumulation_display',
    'Confluence_Signal_display', 'Volume_Breakout_display', 'Profit_Taking_display',
    'Distribution_Warning_display', 'Sell_Signal_display', 'Momentum_Exhaustion_display',
    'Stop_Loss_display'
]

for col in signal_columns:
    df[col] = False
    # Add a few random True values
    true_indices = np.random.choice(days, size=5, replace=False)
    df.iloc[true_indices, df.columns.get_loc(col)] = True

print("📊 Testing chart generation with date ticks...")
print(f"Data range: {df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')}")
print(f"Total trading days: {len(df)}")

# Generate chart
output_path = "backtest_results/TEST_date_ticks_chart.html"
generate_analysis_chart(
    df=df,
    ticker="TEST",
    period="1y",
    save_path=output_path,
    show=False
)

print(f"\n✅ Chart generated successfully: {output_path}")
print("\nOpen the HTML file in a browser and test the time range buttons:")
print("  - 1mo & 3mo should show dates like 'Nov 15'")
print("  - 6mo, 12mo, All should show dates like 'Nov 2024'")
