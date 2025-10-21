#!/usr/bin/env python3
"""
Simple test script to debug news fetching issues.
"""

import json
import re
from datetime import datetime, timedelta
import os

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
    print("✅ Gemini library is available")
except ImportError:
    GEMINI_AVAILABLE = False
    print("❌ Gemini library not available")

def load_gemini_api_key():
    """Load Gemini API key from file."""
    try:
        with open("gemini-api-key", 'r') as f:
            key = f.read().strip()
        print(f"✅ API key loaded, length: {len(key)}")
        return key
    except Exception as e:
        print(f"❌ Error loading Gemini API key: {str(e)}")
        return None

def test_gemini_api_directly(ticker="AAPL", days_back=1):
    """Test Gemini API with a simple request."""
    
    if not GEMINI_AVAILABLE:
        print("❌ Cannot test - Gemini library not available")
        return None
    
    api_key = load_gemini_api_key()
    if not api_key:
        print("❌ Cannot test - No API key")
        return None
    
    # Configure Gemini
    genai.configure(api_key=api_key)
    
    # Calculate dates
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    
    print(f"\n🔍 Testing Gemini API for {ticker}")
    print(f"📅 Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    
    # Simple prompt
    prompt = f"""
Please provide REAL financial news for {ticker} stock from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}.

IMPORTANT: If you don't have information about real news for this ticker during this period, return an empty array [].
DO NOT generate fictional or made-up news. Only return news you know is real.

For each news item, include:
1. Timestamp (in ISO format with time - example: "2025-10-15T09:30:00")
2. Headline
3. Brief summary
4. Source (like Bloomberg, CNBC, etc.)
5. Estimated sentiment (number between -1.0 and 1.0 where negative is bad news and positive is good news)
6. Relevance to the ticker (number between 0.0 and 1.0)

Return ONLY valid JSON format like:
[
    {{"timestamp": "2025-10-15T09:30:00", "headline": "Example Headline", "summary": "Brief summary", "source": "Source Name", "sentiment": 0.5, "relevance": 0.9}}
]

If no real news is available, return [].
"""
    
    try:
        print("🔄 Calling Gemini API...")
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        
        print(f"\n📥 Raw response received:")
        print(f"Response length: {len(response.text)}")
        print(f"Response type: {type(response.text)}")
        print("="*80)
        print(response.text)
        print("="*80)
        
        # Try to parse JSON
        print(f"\n🔄 Attempting to parse JSON...")
        
        # Method 1: Look for JSON array pattern
        json_match = re.search(r'\[\s*{.*}\s*\]', response.text, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            print(f"✅ Found JSON pattern, length: {len(json_str)}")
            try:
                news_items = json.loads(json_str)
                print(f"✅ Successfully parsed {len(news_items)} news items")
                return news_items
            except json.JSONDecodeError as e:
                print(f"❌ JSON decode error in matched pattern: {str(e)}")
        else:
            print("⚠️ No JSON pattern found, trying to parse entire response...")
            
        # Method 2: Try parsing entire response
        try:
            news_items = json.loads(response.text)
            print(f"✅ Successfully parsed entire response: {len(news_items)} items")
            return news_items
        except json.JSONDecodeError as e:
            print(f"❌ JSON decode error on entire response: {str(e)}")
            
        # Method 3: Check if response is just an empty array indicator
        if "[]" in response.text or "no news" in response.text.lower():
            print("ℹ️ Response indicates no news available")
            return []
            
        print("❌ Could not parse any valid JSON from response")
        return None
        
    except Exception as e:
        print(f"❌ Error calling Gemini API: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return None

def test_cache_saving(ticker="TEST", news_data=None):
    """Test if cache saving works."""
    
    if news_data is None:
        news_data = [
            {
                "timestamp": "2025-10-16T10:00:00",
                "headline": "Test News Item",
                "summary": "This is a test",
                "source": "Test Source",
                "sentiment": 0.1,
                "relevance": 0.8
            }
        ]
    
    print(f"\n🧪 Testing cache saving with {len(news_data)} items...")
    
    # Simulate cache saving process
    NEWS_CACHE_DIR = "news_cache"
    
    # Create directory if needed
    if not os.path.exists(NEWS_CACHE_DIR):
        os.makedirs(NEWS_CACHE_DIR)
        print(f"✅ Created cache directory: {NEWS_CACHE_DIR}")
    
    # Test file path
    start_date = datetime.now().strftime('%Y%m%d')
    end_date = start_date
    cache_key = f"{ticker}_{start_date}_{end_date}"
    cache_file = os.path.join(NEWS_CACHE_DIR, f"{cache_key}.json")
    
    print(f"📁 Cache file path: {cache_file}")
    
    try:
        with open(cache_file, 'w') as f:
            json.dump(news_data, f, indent=2)
        
        print(f"✅ Successfully wrote cache file")
        
        # Verify file exists and has content
        if os.path.exists(cache_file):
            file_size = os.path.getsize(cache_file)
            print(f"📏 File size: {file_size} bytes")
            
            # Read it back
            with open(cache_file, 'r') as f:
                loaded_data = json.load(f)
            print(f"✅ Successfully read back {len(loaded_data)} items")
            
            # Clean up test file
            os.remove(cache_file)
            print(f"🗑️ Cleaned up test file")
            
        else:
            print("❌ File was not created")
            
    except Exception as e:
        print(f"❌ Error with cache saving: {str(e)}")

def main():
    """Run all tests."""
    print("🔬 NEWS FETCH DEBUGGING")
    print("="*50)
    
    # Test 1: Direct API call
    print("\n1️⃣ TESTING DIRECT API CALL")
    news_items = test_gemini_api_directly("AAPL", days_back=1)
    
    if news_items is not None:
        print(f"\n📊 API Test Results:")
        print(f"   Items returned: {len(news_items)}")
        if news_items:
            print(f"   Sample item keys: {list(news_items[0].keys())}")
            print(f"   Sample headline: {news_items[0].get('headline', 'N/A')}")
    
    # Test 2: Cache saving
    print("\n2️⃣ TESTING CACHE SAVING")
    test_cache_saving("TESTticker", news_items if news_items else None)
    
    # Test 3: Try a different ticker
    print("\n3️⃣ TESTING DIFFERENT TICKER")  
    news_items2 = test_gemini_api_directly("TSLA", days_back=2)
    
    if news_items2 is not None:
        print(f"\n📊 Second API Test Results:")
        print(f"   Items returned: {len(news_items2)}")
        
    # Summary
    print("\n" + "="*50)
    print("🎯 DEBUGGING SUMMARY:")
    if news_items is None and news_items2 is None:
        print("❌ API calls are failing completely")
    elif (news_items is not None and len(news_items) == 0) and (news_items2 is not None and len(news_items2) == 0):
        print("⚠️ API works but returns no news (may be normal)")
    elif news_items is not None or news_items2 is not None:
        print("✅ API is working and returning data")
    
    print("\nNext steps:")
    print("- If API is failing: Check API key and network connectivity")
    print("- If API returns no news: Try different tickers/date ranges")
    print("- If API works: Check integration with main news_analysis.py")

if __name__ == "__main__":
    main()
