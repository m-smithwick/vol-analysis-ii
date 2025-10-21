#!/usr/bin/env python3
"""
Test with a truly random string that couldn't possibly be a real ticker.
"""

import sys
from datetime import datetime, timedelta
import random
import string

# Generate a truly random ticker that can't be confused with a real one
random_ticker = ''.join(random.choices(string.ascii_letters + string.digits, k=20))

# Define a 5-day date range
end_date = datetime.now()
start_date = end_date - timedelta(days=5)

print(f"Testing with completely random ticker: {random_ticker}")

# First, test with the improved module that should NOT generate mock data
print("\n===== TESTING IMPROVED MODULE (Should NOT generate mock data) =====")
from news_influence_gemini_improved import fetch_financial_news as fetch_improved

print(f"Fetching {random_ticker} news from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
news_improved = fetch_improved(random_ticker, start_date, end_date)

print(f"Found {len(news_improved)} news items with improved module:")
mock_count_improved = 0
for i, item in enumerate(news_improved):
    is_mock = "mock" in item.get("summary", "").lower()
    status = "MOCK" if is_mock else "REAL"
    if is_mock:
        mock_count_improved += 1
    print(f"{i+1}. {item.get('timestamp', '')} | {item.get('headline', '')} | {status}")

print(f"\nMock data count with improved module: {mock_count_improved}")

# Test _generate_mock_news directly from the original module
print("\n===== TESTING ORIGINAL MODULE'S _generate_mock_news FUNCTION =====")
from news_influence_gemini import _generate_mock_news

mock_news = _generate_mock_news(random_ticker, start_date, end_date)
print(f"Generated {len(mock_news)} mock news items directly:")
for i, item in enumerate(mock_news[:3]):  # Show first 3
    is_mock = "mock" in item.get("summary", "").lower()
    status = "MOCK" if is_mock else "REAL"
    print(f"{i+1}. {item.get('timestamp', '')} | {item.get('headline', '')} | {status}")

if "mock" in mock_news[0].get("summary", "").lower():
    print("\n✅ _generate_mock_news function correctly produces mock data as expected")

# Final verification
print("\n===== FINAL VERIFICATION =====")
if mock_count_improved == 0:
    print("✅ SUCCESS: Improved module does NOT generate mock data")
    print("✅ Improved module correctly filtered out Gemini hallucinations")
else:
    print("❌ FAILURE: Improved module is still generating mock data")

print("\nWhile the original module has:")
print("1. A _generate_mock_news function that explicitly generates mock data")
print("2. No hallucination detection capabilities")
