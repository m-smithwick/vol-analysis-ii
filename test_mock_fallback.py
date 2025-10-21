#!/usr/bin/env python3
"""
Test script to verify mock data generation with a less common ticker.
"""

import sys
from datetime import datetime, timedelta

# Define a test ticker that's less likely to have real news
TEST_TICKER = "XYZABC123"  # A fictional ticker

# Define a 5-day date range
end_date = datetime.now()
start_date = end_date - timedelta(days=5)

print(f"Testing with fictional ticker: {TEST_TICKER}")

# First, test with the improved module that should NOT generate mock data
print("\n===== TESTING IMPROVED MODULE (Should NOT generate mock data) =====")
from news_influence_gemini_improved import fetch_financial_news as fetch_improved

print(f"Fetching {TEST_TICKER} news from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
news_improved = fetch_improved(TEST_TICKER, start_date, end_date)

print(f"Found {len(news_improved)} news items with improved module:")
mock_count_improved = 0
for i, item in enumerate(news_improved):
    is_mock = "mock" in item.get("summary", "").lower()
    status = "MOCK" if is_mock else "REAL"
    if is_mock:
        mock_count_improved += 1
    print(f"{i+1}. {item.get('timestamp', '')} | {item.get('headline', '')} | {status}")

print(f"\nMock data count with improved module: {mock_count_improved}")

# Second, test with the original module that DOES generate mock data
print("\n===== TESTING ORIGINAL MODULE (Should generate mock data) =====")
from news_influence_gemini import fetch_financial_news as fetch_original

print(f"Fetching {TEST_TICKER} news from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
news_original = fetch_original(TEST_TICKER, start_date, end_date)

print(f"Found {len(news_original)} news items with original module:")
mock_count_original = 0
for i, item in enumerate(news_original):
    is_mock = "mock" in item.get("summary", "").lower()
    status = "MOCK" if is_mock else "REAL"
    if is_mock:
        mock_count_original += 1
    if i < 10:  # Limit display to 10 items
        print(f"{i+1}. {item.get('timestamp', '')} | {item.get('headline', '')} | {status}")
    elif i == 10:
        print("... (more items)")

print(f"\nMock data count with original module: {mock_count_original}")

# Final comparison
print("\n===== COMPARISON =====")
print(f"Improved module: {len(news_improved)} total items, {mock_count_improved} mock items")
print(f"Original module: {len(news_original)} total items, {mock_count_original} mock items")

if mock_count_improved == 0:
    print("\n✅ SUCCESS: Improved module does NOT generate mock data!")
else:
    print("\n❌ FAILURE: Improved module is still generating mock data!")

if mock_count_original > 0:
    print("✅ Original module generates mock data when real data not available (as expected)")
else:
    print("❓ Original module did not generate mock data when expected")
