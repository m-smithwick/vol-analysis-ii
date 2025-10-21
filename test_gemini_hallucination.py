#!/usr/bin/env python3
"""
Test script for detecting hallucinations in Gemini responses.
This script tests if Gemini is generating fictional news for obscure or non-existent tickers.
"""

import sys
from datetime import datetime, timedelta
from news_influence_gemini import (
    fetch_financial_news_from_gemini,
    fetch_financial_news,
    GEMINI_AVAILABLE
)

def test_with_impossible_conditions():
    """Test with conditions where news should not exist."""
    print("\n🔍 TESTING GEMINI FOR HALLUCINATIONS")
    print("="*60)
    
    # Test case 1: Non-existent ticker
    test_ticker = "NONEXISTENT12345XYZ"
    print(f"\n📝 Test Case 1: Non-existent ticker '{test_ticker}'")
    news = fetch_financial_news_from_gemini(
        ticker=test_ticker,
        start_date=datetime.now() - timedelta(days=3),
        end_date=datetime.now()
    )
    
    print(f"Result: Found {len(news)} news items")
    if len(news) > 0:
        print("⚠️ HALLUCINATION DETECTED: Gemini generated news for a non-existent ticker")
        print("Sample news:")
        for i, item in enumerate(news[:2]):
            print(f"  {i+1}. {item.get('headline', 'No headline')} ({item.get('source', 'Unknown')})")
    else:
        print("✅ PASSED: Gemini correctly returned no news")
    
    # Test case 2: Future dates
    test_ticker = "AAPL"  # Real ticker
    future_start = datetime.now() + timedelta(days=30)
    future_end = datetime.now() + timedelta(days=33)
    print(f"\n📝 Test Case 2: Future dates for '{test_ticker}' ({future_start.strftime('%Y-%m-%d')} to {future_end.strftime('%Y-%m-%d')})")
    
    news = fetch_financial_news_from_gemini(
        ticker=test_ticker,
        start_date=future_start,
        end_date=future_end
    )
    
    print(f"Result: Found {len(news)} news items")
    if len(news) > 0:
        print("⚠️ HALLUCINATION DETECTED: Gemini generated news from the future")
        print("Sample news:")
        for i, item in enumerate(news[:2]):
            print(f"  {i+1}. {item.get('headline', 'No headline')} ({item.get('source', 'Unknown')})")
    else:
        print("✅ PASSED: Gemini correctly returned no news")
    
    # Test case 3: Fictional ticker that sounds plausible
    test_ticker = "METAVERSE"  # Sounds plausible but doesn't exist as a ticker
    print(f"\n📝 Test Case 3: Plausible-sounding fictional ticker '{test_ticker}'")
    
    news = fetch_financial_news_from_gemini(
        ticker=test_ticker,
        start_date=datetime.now() - timedelta(days=3),
        end_date=datetime.now()
    )
    
    print(f"Result: Found {len(news)} news items")
    if len(news) > 0:
        print("⚠️ HALLUCINATION DETECTED: Gemini generated news for a fictional ticker")
        print("Sample news:")
        for i, item in enumerate(news[:2]):
            print(f"  {i+1}. {item.get('headline', 'No headline')} ({item.get('source', 'Unknown')})")
    else:
        print("✅ PASSED: Gemini correctly returned no news")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    if not GEMINI_AVAILABLE:
        print("❌ Gemini API not available. Please install the package with 'pip install google-generativeai'")
        sys.exit(1)
    
    test_with_impossible_conditions()
