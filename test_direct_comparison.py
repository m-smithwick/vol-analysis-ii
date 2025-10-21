#!/usr/bin/env python3
"""
Direct comparison of both modules with verbose output to show exactly what's happening.
"""

import sys
import os
from datetime import datetime, timedelta

# Set up date range for testing
end_date = datetime.now()
start_date = end_date - timedelta(days=5)
test_ticker = "NONEXISTENT123XYZ"  # Definitely shouldn't exist

print(f"Testing with nonexistent ticker: {test_ticker}")

# First test the improved module's news fetching process
print("\n===== TESTING IMPROVED MODULE =====")
from news_influence_gemini_improved import (
    fetch_financial_news as fetch_improved,
    fetch_financial_news_from_gemini as fetch_gemini_improved
)

print(f"\nStep 1: Check if cached news exists (shouldn't, we cleared cache)...")
cache_path = os.path.join("news_cache", f"{test_ticker}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.json")
if os.path.exists(cache_path):
    print(f"Cache exists at: {cache_path}")
else:
    print(f"No cache found (expected)")

print(f"\nStep 2: Try to get news from Gemini...")
gemini_news = fetch_gemini_improved(test_ticker, start_date, end_date)
print(f"Gemini returned {len(gemini_news)} news items")

print(f"\nStep 3: Call main fetch_financial_news function...")
news_improved = fetch_improved(test_ticker, start_date, end_date)
print(f"Main function returned {len(news_improved)} news items")

if len(news_improved) == 0:
    print("\n✅ Improved module returned no fake data for nonexistent ticker")
else:
    print("\n⚠️ Improved module returned data for nonexistent ticker - checking if it's mock data...")
    mock_count = sum(1 for item in news_improved if "mock" in item.get("summary", "").lower())
    print(f"Mock data count: {mock_count} out of {len(news_improved)}")

# Next test the original module's news fetching process
print("\n\n===== TESTING ORIGINAL MODULE =====")
from news_influence_gemini import (
    fetch_financial_news as fetch_original,
    fetch_financial_news_from_gemini as fetch_gemini_original,
    _generate_mock_news  # Directly import the mock news function
)

print(f"\nStep 1: Check if cached news exists (shouldn't, we cleared cache)...")
if os.path.exists(cache_path):
    print(f"Cache exists at: {cache_path}")
else:
    print(f"No cache found (expected)")

print(f"\nStep 2: Try to get news from Gemini...")
gemini_news = fetch_gemini_original(test_ticker, start_date, end_date)
print(f"Gemini returned {len(gemini_news)} news items")

print(f"\nStep 3: Try to generate mock news directly...")
try:
    mock_news = _generate_mock_news(test_ticker, start_date, end_date)
    print(f"Mock news generator returned {len(mock_news)} items")
    if len(mock_news) > 0:
        print(f"First mock item summary: {mock_news[0].get('summary', 'No summary')}")
        if "mock" in mock_news[0].get("summary", "").lower():
            print("✅ Confirmed this is mock data")
except Exception as e:
    print(f"Error generating mock news: {e}")

print(f"\nStep 4: Call main fetch_financial_news function...")
news_original = fetch_original(test_ticker, start_date, end_date)
print(f"Main function returned {len(news_original)} news items")

if len(news_original) > 0:
    print("\nChecking if returned data is mock data:")
    mock_count = sum(1 for item in news_original if "mock" in item.get("summary", "").lower())
    print(f"Mock data count: {mock_count} out of {len(news_original)}")
    
    if mock_count > 0:
        print("✅ Original module returned mock data as fallback")
    else:
        print("⚠️ Original module returned data that doesn't appear to be mock data")
else:
    print("\n⚠️ Original module did not return any data - no mock generation happened")

# Print source of fetch_financial_news in original module to see the logic
print("\n===== ORIGINAL MODULE'S FETCH_FINANCIAL_NEWS LOGIC =====")
import inspect
print(inspect.getsource(fetch_original))

print("\n===== COMPARISON RESULTS =====")
print(f"Improved module: {len(news_improved)} items, {sum(1 for item in news_improved if 'mock' in item.get('summary', '').lower())} mock")
print(f"Original module: {len(news_original)} items, {sum(1 for item in news_original if 'mock' in item.get('summary', '').lower())} mock")
