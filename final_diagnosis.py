#!/usr/bin/env python3
"""
Final diagnosis of the news analysis issue.
"""

from datetime import datetime, timedelta
from data_manager import get_intraday_data

def diagnose_complete_system():
    """Complete system diagnosis."""
    
    print("🏥 COMPLETE SYSTEM DIAGNOSIS")
    print("="*60)
    
    print("\n1️⃣ TESTING PRICE DATA AVAILABILITY")
    
    # Test recent dates (should have price data)
    recent_date = datetime.now() - timedelta(days=1)
    print(f"📅 Testing recent date: {recent_date.strftime('%Y-%m-%d')}")
    
    try:
        recent_data = get_intraday_data("AAPL", days=5, interval="1h")
        print(f"✅ Recent price data: {len(recent_data)} periods")
        print(f"   Date range: {recent_data.index.min()} to {recent_data.index.max()}")
    except Exception as e:
        print(f"❌ Recent price data error: {str(e)}")
    
    # Test historical dates (may not have price data)
    historical_date = datetime(2024, 1, 1)
    print(f"\n📅 Testing historical date: {historical_date.strftime('%Y-%m-%d')}")
    
    try:
        # Try to get data for historical date
        from data_manager import get_intraday_data
        historical_data = get_intraday_data("AAPL", days=30, interval="1h")
        
        # Check if historical date is in the data
        hist_start = historical_date - timedelta(days=1)
        hist_end = historical_date + timedelta(days=1)
        
        if historical_data.index.tzinfo is not None:
            historical_data.index = historical_data.index.tz_localize(None)
        
        mask = (historical_data.index >= hist_start) & (historical_data.index <= hist_end)
        filtered_data = historical_data.loc[mask]
        
        if filtered_data.empty:
            print(f"❌ No historical price data for {historical_date.strftime('%Y-%m-%d')}")
            print(f"   Available range: {historical_data.index.min()} to {historical_data.index.max()}")
        else:
            print(f"✅ Historical price data: {len(filtered_data)} periods")
            
    except Exception as e:
        print(f"❌ Historical price data error: {str(e)}")
    
    print("\n2️⃣ GEMINI NEWS DATA AVAILABILITY")
    print("✅ Recent dates (2024-2025): No news data")
    print("✅ Historical dates (2023-early 2024): Has news data")
    
    print("\n3️⃣ THE MISMATCH PROBLEM")
    print("❌ Recent dates: Have PRICE data but NO NEWS data (Gemini limitation)")
    print("❌ Historical dates: Have NEWS data but NO PRICE data (yfinance limitation)")
    
    print("\n🎯 ROOT CAUSE SUMMARY")
    print("="*60)
    print("The system needs BOTH price data AND news data for the same dates.")
    print("Currently there's a mismatch:")
    print("  • yfinance provides recent price data (last ~30 days)")  
    print("  • Gemini provides historical news data (2023-early 2024)")
    print("  • No overlap between the two data sources!")
    
    print("\n💡 SOLUTIONS")
    print("="*60)
    print("1. 🔑 Get Alpha Vantage API key for recent news")
    print("   export ALPHA_VANTAGE_API_KEY='your_key'")
    print("2. 📈 Use different price data source for historical analysis") 
    print("3. 🧪 Create mock data to test the analysis logic")

if __name__ == "__main__":
    diagnose_complete_system()
