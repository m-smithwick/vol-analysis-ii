#!/usr/bin/env python3
"""
Test script for the improved Gemini integration with hallucination detection.
"""

import os
import sys
from datetime import datetime, timedelta
import time

# Import our improved module
try:
    from news_influence_gemini_improved import (
        fetch_financial_news_from_gemini,
        verify_ticker_exists,
        detect_hallucinations,
        GEMINI_AVAILABLE
    )
    print(f"✅ Successfully imported news_influence_gemini_improved")
    print(f"🔌 Gemini API available: {GEMINI_AVAILABLE}")
except ImportError as e:
    print(f"❌ Error importing news_influence_gemini_improved: {e}")
    sys.exit(1)

def test_ticker_verification():
    """Test the ticker verification function."""
    print("\n🔍 TESTING TICKER VERIFICATION")
    print("="*60)
    
    # Test with real tickers
    real_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN"]
    for ticker in real_tickers:
        exists = verify_ticker_exists(ticker)
        print(f"Ticker '{ticker}' exists: {exists}")
    
    # Test with fake tickers
    fake_tickers = ["NOTREAL", "FAKECO", "XYZCORP"]
    for ticker in fake_tickers:
        exists = verify_ticker_exists(ticker)
        print(f"Ticker '{ticker}' exists: {exists}")

def test_hallucination_detection():
    """Test the hallucination detection function."""
    print("\n🔍 TESTING HALLUCINATION DETECTION")
    print("="*60)
    
    # Test case 1: Future dates
    print("\n📝 Test Case 1: Future dates")
    now = datetime.now()
    future_date = now + timedelta(days=30)
    news_items = [
        {
            "timestamp": future_date.isoformat(),
            "headline": "Company XYZ Announces Record Earnings",
            "summary": "This is a test summary",
            "source": "Test Source",
            "sentiment": 0.8
        }
    ]
    
    filtered, warnings = detect_hallucinations(
        "AAPL", 
        news_items, 
        now - timedelta(days=3), 
        now
    )
    
    print(f"Original items: {len(news_items)}")
    print(f"Filtered items: {len(filtered)}")
    print("Warnings:")
    for warning in warnings:
        print(f"  - {warning}")
    
    # Test case 2: Invalid ticker
    print("\n📝 Test Case 2: Invalid ticker")
    news_items = [
        {
            "timestamp": (now - timedelta(days=1)).isoformat(),
            "headline": "Company XYZ Announces Record Earnings",
            "summary": "This is a test summary",
            "source": "Test Source",
            "sentiment": 0.8
        }
    ]
    
    filtered, warnings = detect_hallucinations(
        "FAKEXYZ123", 
        news_items, 
        now - timedelta(days=3), 
        now
    )
    
    print(f"Original items: {len(news_items)}")
    print(f"Filtered items: {len(filtered)}")
    print("Warnings:")
    for warning in warnings:
        print(f"  - {warning}")
    
    # Test case 3: Out of range dates
    print("\n📝 Test Case 3: Out of range dates")
    news_items = [
        {
            "timestamp": (now - timedelta(days=10)).isoformat(),
            "headline": "Company XYZ Announces Record Earnings",
            "summary": "This is a test summary",
            "source": "Test Source",
            "sentiment": 0.8
        }
    ]
    
    filtered, warnings = detect_hallucinations(
        "AAPL", 
        news_items, 
        now - timedelta(days=3), 
        now
    )
    
    print(f"Original items: {len(news_items)}")
    print(f"Filtered items: {len(filtered)}")
    print("Warnings:")
    for warning in warnings:
        print(f"  - {warning}")

def test_real_data_fetch(ticker="AAPL"):
    """Test fetching real data with the improved implementation."""
    print("\n🔍 TESTING REAL DATA FETCH")
    print("="*60)
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=3)
    
    print(f"Fetching news for {ticker} from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    
    # Use the improved fetch function that includes hallucination detection
    news = fetch_financial_news_from_gemini(ticker, start_date, end_date)
    
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
    else:
        print("⚠️ No news found or all news filtered due to hallucination detection")

def main():
    """Run all tests."""
    if not GEMINI_AVAILABLE:
        print("❌ Gemini API not available. Please install the package with 'pip install google-generativeai'")
        sys.exit(1)
        
    # Test ticker verification
    test_ticker_verification()
    
    # Test hallucination detection
    test_hallucination_detection()
    
    # Test real data fetching with hallucination detection
    test_real_data_fetch()
    
    # Test with a potentially fake ticker
    test_real_data_fetch("XYZFAKE123")
    
    # Test with a future date
    print("\n🔍 TESTING WITH FUTURE DATE")
    print("="*60)
    future_start = datetime.now() + timedelta(days=30)
    future_end = future_start + timedelta(days=3)
    
    print(f"Fetching news for AAPL from {future_start.strftime('%Y-%m-%d')} to {future_end.strftime('%Y-%m-%d')}")
    news = fetch_financial_news_from_gemini("AAPL", future_start, future_end)
    print(f"Results: Found {len(news)} news items")

if __name__ == "__main__":
    main()
