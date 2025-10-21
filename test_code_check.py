#!/usr/bin/env python3
"""
Check what's actually happening in the original module code.
"""

import inspect
import os
from datetime import datetime, timedelta

print("Examining news_influence_gemini.py to understand when mock data is generated...")

# Import functions from original module
from news_influence_gemini import (
    fetch_financial_news, 
    fetch_financial_news_from_gemini,
    _generate_mock_news, 
    _check_news_cache, 
    _save_to_news_cache
)

# Print the source code of the important functions
print("\n===== FETCH_FINANCIAL_NEWS =====")
print(inspect.getsource(fetch_financial_news))

# Let's look at what's actually in the file line by line
print("\n===== SEARCHING FOR MOCK DATA GENERATION =====")
with open("news_influence_gemini.py", "r") as file:
    lines = file.readlines()
    
    # Look for references to _generate_mock_news in the file
    for i, line in enumerate(lines):
        if "_generate_mock_news" in line:
            line_num = i + 1
            print(f"Line {line_num}: {line.strip()}")
            # Show 5 lines before and after for context
            for j in range(max(0, i - 5), min(len(lines), i + 6)):
                if j != i:
                    print(f"Line {j + 1}: {lines[j].strip()}")

# Test what really happens with a non-existent ticker
print("\n===== TESTING WHAT ACTUALLY HAPPENS =====")
test_ticker = "XYZNONEXISTENT123"
start_date = datetime.now() - timedelta(days=2)
end_date = datetime.now()

print(f"Running fetch_financial_news_from_gemini for {test_ticker}...")
gemini_news = fetch_financial_news_from_gemini(test_ticker, start_date, end_date)
print(f"Gemini returned {len(gemini_news)} items")

print("\nRunning _generate_mock_news directly...")
mock_news = _generate_mock_news(test_ticker, start_date, end_date)
print(f"Mock news function returned {len(mock_news)} items")

print("\nRunning fetch_financial_news (the main function)...")
news = fetch_financial_news(test_ticker, start_date, end_date)
print(f"Main function returned {len(news)} items")

# Check if the returned news is the same as the mock news
is_mock = False
if len(news) > 0 and len(mock_news) > 0:
    # Check if timestamps match between mock news and returned news
    mock_timestamps = set(item.get('timestamp', '') for item in mock_news)
    news_timestamps = set(item.get('timestamp', '') for item in news)
    common_timestamps = mock_timestamps.intersection(news_timestamps)
    
    print(f"\nTimestamp comparison: {len(common_timestamps)} common timestamps out of {len(mock_timestamps)} mock timestamps")
    if len(common_timestamps) == len(mock_timestamps):
        print("✅ The news returned by the main function is identical to the mock news")
        is_mock = True
    else:
        print("⚠️ The news returned is different from the mock news")

# Let's also check if it looks like mock data by looking at the summaries
if len(news) > 0:
    mock_count = sum(1 for item in news if "mock" in item.get("summary", "").lower())
    print(f"\nMock summary count: {mock_count} out of {len(news)}")
    if mock_count > 0:
        print("✅ Confirmed these are mock summaries")
        is_mock = True

if is_mock:
    print("\nCONCLUSION: The original module IS generating mock data despite the comment saying otherwise!")
else:
    print("\nCONCLUSION: The original module is NOT generating mock data as the comment suggests.")
