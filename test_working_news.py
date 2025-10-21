#!/usr/bin/env python3
"""
Test the news analysis system with dates that have actual news data.
"""

from datetime import datetime
from news_analysis import analyze_news_influence

def main():
    print("🧪 TESTING WITH DATES THAT HAVE NEWS DATA")
    print("="*60)
    
    # Test with early 2024 date that we know has news
    print("\n1️⃣ Testing with January 1, 2024 (confirmed to have news)")
    
    try:
        results = analyze_news_influence(
            ticker="AAPL",
            date_str="2024-01-01",
            days_back=1,
            interval="1h",
            save_to_file=True,
            save_chart=False
        )
        
        if results:
            print(f"✅ Analysis completed successfully!")
            print(f"📊 Results: {len(results)} day(s) analyzed")
        else:
            print("⚠️ No results returned")
            
    except Exception as e:
        print(f"❌ Error during analysis: {str(e)}")
    
    # Check if news was cached
    import os
    cache_files = []
    if os.path.exists("news_cache"):
        cache_files = [f for f in os.listdir("news_cache") if f.endswith('.json')]
    
    print(f"\n📁 News cache status: {len(cache_files)} files")
    for file in cache_files[:3]:  # Show first 3 files
        print(f"   - {file}")

if __name__ == "__main__":
    main()
