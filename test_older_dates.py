#!/usr/bin/env python3
"""
Test news fetching with older dates to see if Gemini has historical news data.
"""

import json
import re
from datetime import datetime, timedelta
import os

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("❌ Gemini library not available")

def load_gemini_api_key():
    """Load Gemini API key from file."""
    try:
        with open("gemini-api-key", 'r') as f:
            return f.read().strip()
    except Exception as e:
        print(f"❌ Error loading API key: {str(e)}")
        return None

def test_historical_dates():
    """Test with older dates that Gemini might know about."""
    
    if not GEMINI_AVAILABLE:
        print("❌ Cannot test - Gemini library not available")
        return
    
    api_key = load_gemini_api_key()
    if not api_key:
        print("❌ Cannot test - No API key")
        return
    
    genai.configure(api_key=api_key)
    
    # Test various historical dates
    test_dates = [
        ("2024-10-01", "2024-10-02", "Recent 2024"),
        ("2024-07-01", "2024-07-02", "Mid 2024"),  
        ("2024-01-01", "2024-01-02", "Early 2024"),
        ("2023-10-01", "2023-10-02", "Late 2023"),
    ]
    
    for start_str, end_str, description in test_dates:
        print(f"\n🔍 Testing {description}: {start_str} to {end_str}")
        
        prompt = f"""
Please provide REAL financial news for AAPL stock from {start_str} to {end_str}.

If you have information about real news for this ticker during this period, return it as JSON.
If you don't have information, return an empty array [].
DO NOT generate fictional news.

Return ONLY valid JSON format like:
[
    {{"timestamp": "2024-01-01T09:30:00", "headline": "Real Headline", "summary": "Brief summary", "source": "Source Name", "sentiment": 0.5, "relevance": 0.9}}
]

If no real news is available, return [].
"""
        
        try:
            model = genai.GenerativeModel('gemini-2.5-flash')
            response = model.generate_content(prompt)
            
            print(f"📥 Response length: {len(response.text)}")
            
            # Try to parse
            try:
                if response.text.strip() == "[]":
                    print("   ➤ Empty array response")
                else:
                    # Look for JSON
                    json_match = re.search(r'\[\s*{.*}\s*\]', response.text, re.DOTALL)
                    if json_match:
                        news_items = json.loads(json_match.group(0))
                        print(f"   ➤ Found {len(news_items)} news items!")
                        if news_items:
                            print(f"   ➤ Sample: {news_items[0].get('headline', 'N/A')[:60]}...")
                    else:
                        try:
                            news_items = json.loads(response.text)
                            print(f"   ➤ Parsed {len(news_items)} items from full response")
                        except:
                            print(f"   ➤ Non-JSON response: {response.text[:100]}...")
            except Exception as e:
                print(f"   ➤ Parse error: {str(e)}")
                
        except Exception as e:
            print(f"   ➤ API error: {str(e)}")

def main():
    print("🕰️ TESTING HISTORICAL NEWS DATES")
    print("="*50)
    test_historical_dates()

if __name__ == "__main__":
    main()
