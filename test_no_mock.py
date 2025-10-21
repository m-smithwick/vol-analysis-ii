#!/usr/bin/env python3
"""
Test script to verify that the improved news influence module isn't generating mock data.
"""

import sys
from datetime import datetime, timedelta

# First, test with the improved module that should NOT generate mock data
print("===== TESTING IMPROVED MODULE (Should NOT generate mock data) =====")
from news_influence_gemini_improved import fetch_financial_news as fetch_improved

# Define a 5-day date range
end_date = datetime.now()
start_date = end_date - timedelta(days=5)

print(f"Fetching MSFT news from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
news_improved = fetch_improved("MSFT", start_date, end_date)

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
print("\n===== TESTING ORIGINAL MODULE (May generate mock data) =====")
from news_influence_gemini import fetch_financial_news as fetch_original

print(f"Fetching MSFT news from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
news_original = fetch_original("MSFT", start_date, end_date)

print(f"Found {len(news_original)} news items with original module:")
mock_count_original = 0
for i, item in enumerate(news_original):
    is_mock = "mock" in item.get("summary", "").lower()
    status = "MOCK" if is_mock else "REAL"
    if is_mock:
        mock_count_original += 1
    print(f"{i+1}. {item.get('timestamp', '')} | {item.get('headline', '')} | {status}")

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
    print("NOTE: Original module generates mock data as expected")
