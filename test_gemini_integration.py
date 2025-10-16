#!/usr/bin/env python3
"""
Test script for the Gemini Pro integration in news_influence_gemini.py
This script will test the integration and fall back to mock data if Gemini is not available.
"""

import os
import sys
import json
from datetime import datetime, timedelta

# Import our modified module
try:
    from news_influence_gemini import (
        fetch_financial_news,
        clear_news_cache,
        GEMINI_AVAILABLE
    )
    print(f"✅ Successfully imported news_influence_gemini")
    print(f"🔌 Gemini API available: {GEMINI_AVAILABLE}")
except ImportError as e:
    print(f"❌ Error importing news_influence_gemini: {e}")
    sys.exit(1)

def test_fetch_news(ticker="AAPL", days_back=3):
    """Test fetching news for a ticker with Gemini (falling back to mock if needed)."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    
    print(f"\n📰 Testing news fetching for {ticker} from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    
    # First, clear any existing cache
    print("🗑️  Clearing cache for clean test...")
    clear_news_cache(ticker, start_date, end_date)
    
    # Fetch the news
    news = fetch_financial_news(ticker, start_date, end_date)
    
    # Display the results
    print(f"\n📊 Results: Found {len(news)} news items")
    
    if news:
        print("\nSample news items:")
        for i, item in enumerate(news[:3]):  # Show first 3 items
            print(f"\n--- Item {i+1} ---")
            print(f"Timestamp: {item.get('timestamp', 'Unknown')}")
            print(f"Headline: {item.get('headline', 'No headline')}")
            print(f"Source: {item.get('source', 'Unknown')}")
            print(f"Type: {item.get('type', 'Unknown')}")
            print(f"Sentiment: {item.get('sentiment', 0)}")
            
        # Save to a JSON file for inspection
        output_file = f"{ticker}_news_test.json"
        with open(output_file, "w") as f:
            json.dump(news, f, indent=2)
        print(f"\n💾 Saved complete results to {output_file}")
    else:
        print("❌ No news found")

if __name__ == "__main__":
    # Parse command line arguments
    if len(sys.argv) > 1:
        ticker = sys.argv[1].upper()
    else:
        ticker = "AAPL"  # Default
    
    days_back = 3
    if len(sys.argv) > 2:
        try:
            days_back = int(sys.argv[2])
        except ValueError:
            print(f"Warning: Invalid days value '{sys.argv[2]}', using default of {days_back}")
    
    test_fetch_news(ticker, days_back)
