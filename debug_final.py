#!/usr/bin/env python3
"""
Final debugging script to test the timezone handling fix
"""

from datetime import datetime, timedelta

# Import the modules we need to test
from news_analysis import analyze_news_influence

def test_aapl_analysis():
    """Test analyzing AAPL with fixed timezone handling"""
    print("\n===== FINAL TIMEZONE TEST =====")
    
    print("Testing analyze_news_influence with AAPL (single day)...")
    
    try:
        # Use a specific date to focus the test
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        # Run the analysis
        results = analyze_news_influence(
            ticker="AAPL",
            date_str=yesterday,
            interval="1h",
            save_to_file=False
        )
        
        print("\n✅ Success! The timezone fix worked.")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n===== TEST COMPLETE =====")

if __name__ == "__main__":
    test_aapl_analysis()
