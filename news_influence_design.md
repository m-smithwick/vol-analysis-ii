# News & Research Influence Analysis Feature: Design Document

## Overview

This document outlines the design for a new feature that determines if daily price increases after market open are influenced by news or research reports. The implementation will build upon the existing `vol_analysis.py` codebase while modularizing shared functionality.

## Current Architecture Analysis

The existing `vol_analysis.py` script has several well-defined functional components:

1. **Data Management**:
   - Cache management (get/load/save/append)
   - Smart data retrieval with Yahoo Finance
   - Period normalization

2. **Analysis Components**:
   - Price-volume indicators (OBV, A/D line)
   - Accumulation/distribution pattern detection
   - Buy/sell signal generation
   - Scoring mechanisms

3. **Output & Visualization**:
   - Text reports
   - Charts and visualizations
   - Batch processing

4. **Command-line Interface**:
   - Argument parsing
   - Mode selection (single ticker, batch, cache management)

## Intraday Interval Analysis

### Recommended Approach for Initial Implementation

For the initial implementation, **hourly intervals** (1h) provide an optimal balance between:
- Sufficient granularity to detect meaningful intraday patterns
- Reasonable processing requirements
- Data availability from free APIs
- Meaningful correlation windows with news events

Hourly data allows us to:
1. Identify post-open momentum without excessive noise
2. Detect key turning points during the trading day
3. Correlate with typical news release timing (pre-market, early hours, lunch, late day)
4. Process data efficiently without overwhelming API limits

### Interval Comparison

| Interval | Advantages | Disadvantages | Use Case |
|----------|------------|---------------|----------|
| 1h | Balanced detail/performance, Clearer trends, Less noise | May miss short-term reactions | **Recommended starting point** |
| 30m | Better detail on rapid news reactions | Double the data points to process | Secondary implementation after validating with hourly |
| 15m | High detail for quick moves | Higher noise, API limits, Processing intensive | Future enhancement for high-volatility events |
| 5m | Very detailed short-term reactions | Excessive noise, Limited historical data, API restrictions | Not recommended initially |

### Data Considerations
- Yahoo Finance free API provides limited history for intraday data (typically ~7-60 days depending on interval)
- Hourly data usually available for ~60 days (sufficient for initial testing)
- Consider implementing a rolling intraday cache to build historical database over time

## Proposed Modular Architecture

### 1. Core Modules

#### `data_manager.py`
```python
# Core data retrieval and caching functionality
from typing import List, Optional, Dict, Any
import pandas as pd
import os
import yfinance as yf
from datetime import datetime, timedelta

def get_cache_directory() -> str:
    """Get or create the data cache directory."""
    # Extracted from existing code
    
def get_cache_filepath(ticker: str, interval: str = "1d") -> str:
    """Get the cache file path for a given ticker and interval."""
    # Modified to support different intervals
    cache_dir = get_cache_directory()
    return os.path.join(cache_dir, f"{ticker}_{interval}_data.csv")

def load_cached_data(ticker: str, interval: str = "1d") -> Optional[pd.DataFrame]:
    """Load cached data for a ticker if it exists and is valid."""
    # Modified to support different intervals
    
def save_to_cache(ticker: str, df: pd.DataFrame, interval: str = "1d") -> None:
    """Save DataFrame to cache with interval support."""
    # Modified to support different intervals
    
def normalize_period(period: str) -> str:
    """Normalize period parameter to ensure compatibility with yfinance."""
    # Extracted from existing code
    
def get_smart_data(ticker: str, period: str, interval: str = "1d", force_refresh: bool = False) -> pd.DataFrame:
    """
    Smart data fetching with caching support.
    
    Args:
        ticker (str): Stock symbol
        period (str): Requested period (e.g., '6mo', '12mo')
        interval (str): Data interval ('1d', '1h', '30m', '15m', etc.)
        force_refresh (bool): If True, ignore cache and download fresh data
        
    Returns:
        pd.DataFrame: Stock data with OHLCV columns
    """
    # Enhanced to handle intraday intervals
    
def get_intraday_data(ticker: str, days: int = 5, interval: str = "1h", force_refresh: bool = False) -> pd.DataFrame:
    """
    Get intraday data for specific number of days.
    
    Args:
        ticker (str): Stock symbol
        days (int): Number of days to retrieve
        interval (str): Intraday interval ('1h', '30m', '15m', '5m', '1m')
        force_refresh (bool): If True, ignore cache and download fresh data
        
    Returns:
        pd.DataFrame: Intraday stock data
    """
    # New function for handling intraday data specifically

def read_ticker_file(filepath: str) -> List[str]:
    """Read ticker symbols from a text file (one ticker per line)."""
    # Extracted from existing code
```

#### `indicators.py`
```python
import pandas as pd
import numpy as np

def calculate_obv(df: pd.DataFrame) -> pd.Series:
    """Calculate On-Balance Volume."""
    return ((df['Close'] > df['Close'].shift(1)) * df['Volume'] - 
            (df['Close'] < df['Close'].shift(1)) * df['Volume']).cumsum()

def calculate_ad_line(df: pd.DataFrame) -> pd.Series:
    """Calculate Accumulation/Distribution Line."""
    # Extracted from existing code
    
def calculate_vwap(df: pd.DataFrame) -> pd.Series:
    """Calculate Volume-Weighted Average Price."""
    return (df['Close'] * df['Volume']).cumsum() / df['Volume'].cumsum()

def calculate_price_volume_correlation(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """Calculate rolling correlation between price and volume changes."""
    df_temp = df.copy()
    df_temp['Return'] = df_temp['Close'].pct_change()
    df_temp['VolChange'] = df_temp['Volume'].pct_change()
    return df_temp['Return'].rolling(window).corr(df_temp['VolChange'])

def calculate_support_levels(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """Calculate rolling support levels."""
    return df['Low'].rolling(window=window).min()

def calculate_intraday_momentum(df: pd.DataFrame) -> pd.Series:
    """
    Calculate intraday momentum score.
    
    Higher values indicate stronger intraday momentum from open.
    """
    # Calculate percentage change from open
    open_to_close = (df['Close'] - df['Open']) / df['Open'] * 100
    
    # Calculate percentage of daily range achieved
    daily_range = (df['High'] - df['Low'])
    open_to_close_range = (df['Close'] - df['Open']).abs()
    range_percent = open_to_close_range / daily_range
    
    # Combine into momentum score
    momentum = open_to_close * range_percent
    return momentum
```

#### `utils.py`
```python
import os
from datetime import datetime
import sys
from typing import List, Dict, Any, Optional

def generate_output_directory(base_dir: str) -> str:
    """Create and return output directory path."""
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)
    return base_dir

def format_date_range(start_date: datetime, end_date: datetime) -> str:
    """Format a date range as a string."""
    return f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"

def handle_errors(error: Exception, ticker: str = None) -> None:
    """Handle and format errors."""
    if ticker:
        print(f"❌ Error processing {ticker}: {str(error)}")
    else:
        print(f"❌ Error: {str(error)}")
```

### 2. New News/Research Influence Module

#### `news_influence.py`
```python
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import requests
import json
import os

# News API configuration
NEWS_API_KEY = "YOUR_API_KEY"  # Should be moved to configuration file
NEWS_CACHE_DIR = "news_cache"

def detect_intraday_price_jumps(df: pd.DataFrame, threshold: float = 0.5) -> List[datetime]:
    """
    Detect significant intraday price jumps.
    
    Args:
        df (pd.DataFrame): Intraday price data
        threshold (float): Minimum percentage increase to be considered significant
        
    Returns:
        List[datetime]: Timestamps where significant jumps occurred
    """
    # Calculate percentage change between intervals
    df['pct_change'] = df['Close'].pct_change() * 100
    
    # Find intervals with significant price increases
    jump_indices = df[df['pct_change'] > threshold].index.tolist()
    
    return jump_indices

def fetch_financial_news(ticker: str, start_date: datetime, end_date: datetime = None) -> List[Dict]:
    """
    Fetch financial news for a given ticker and date range.
    
    Args:
        ticker (str): Stock symbol
        start_date (datetime): Start date for news
        end_date (datetime, optional): End date for news (defaults to start_date + 1 day)
        
    Returns:
        List[Dict]: List of news items with timestamp, headline, and content
    """
    # Check cache first
    cached_news = _check_news_cache(ticker, start_date, end_date)
    if cached_news:
        return cached_news
    
    # Set default end_date if not provided
    if end_date is None:
        end_date = start_date + timedelta(days=1)
    
    # Format dates for API
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')
    
    # Example using a public financial news API (would need to be replaced with actual implementation)
    url = f"https://api.example.com/v1/news?tickers={ticker}&from={start_str}&to={end_str}&apiKey={NEWS_API_KEY}"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            news_data = response.json()
            # Cache the results
            _save_to_news_cache(ticker, start_date, end_date, news_data)
            return news_data
        else:
            print(f"⚠️ Failed to fetch news: {response.status_code}")
            return []
    except Exception as e:
        print(f"⚠️ Error fetching news: {str(e)}")
        return []

def classify_news_type(news_text: str) -> str:
    """
    Classify the type of financial news.
    
    Args:
        news_text (str): News headline or content
        
    Returns:
        str: Classification (earnings, analyst, product, general, etc.)
    """
    # Simple keyword-based classification
    keywords = {
        'earnings': ['earnings', 'revenue', 'profit', 'eps', 'quarterly', 'financial results'],
        'analyst': ['upgrade', 'downgrade', 'rating', 'price target', 'analyst', 'research'],
        'product': ['launch', 'release', 'announce', 'unveil', 'new product', 'innovation'],
        'regulatory': ['sec', 'regulation', 'lawsuit', 'legal', 'investigation', 'compliance'],
        'management': ['ceo', 'executive', 'management', 'appoint', 'resign', 'leadership'],
    }
    
    news_text = news_text.lower()
    
    for category, terms in keywords.items():
        if any(term in news_text for term in terms):
            return category
    
    return 'general'

def correlate_price_movement_with_news(
    price_df: pd.DataFrame, 
    news_items: List[Dict],
    look_ahead_periods: int = 3
) -> Dict[str, Any]:
    """
    Correlate price movements with news events.
    
    Args:
        price_df (pd.DataFrame): Intraday price data
        news_items (List[Dict]): List of news items with timestamp
        look_ahead_periods (int): Number of periods to look ahead after news
        
    Returns:
        Dict: Correlation statistics and detected influence
    """
    if not news_items or price_df.empty:
        return {'influenced_by_news': False, 'confidence': 0.0, 'events': []}
    
    results = []
    
    for news in news_items:
        news_time = datetime.fromisoformat(news['timestamp'])
        
        # Find the first price data point after the news
        post_news_data = price_df[price_df.index > news_time]
        if post_news_data.empty:
            continue
            
        # Calculate price change after news
        first_idx = post_news_data.index[0]
        pre_news_price = price_df['Close'].iloc[price_df.index.get_loc(first_idx) - 1]
        
        # Look at price movement over next several periods
        for i in range(min(look_ahead_periods, len(post_news_data))):
            if i >= len(post_news_data):
                break
                
            period_idx = post_news_data.index[i]
            period_price = post_news_data['Close'].iloc[i]
            pct_change = ((period_price - pre_news_price) / pre_news_price) * 100
            volume_vs_avg = post_news_data['Volume'].iloc[i] / price_df['Volume'].mean()
            
            # Determine if this movement is significant
            is_significant = abs(pct_change) > 1.0 and volume_vs_avg > 1.2
            
            if is_significant:
                results.append({
                    'news_time': news_time,
                    'price_time': period_idx,
                    'delay_minutes': (period_idx - news_time).total_seconds() / 60,
                    'pct_change': pct_change,
                    'volume_ratio': volume_vs_avg,
                    'news_type': news.get('type', classify_news_type(news.get('headline', ''))),
                    'headline': news.get('headline', 'N/A')
                })
    
    # Calculate overall influence
    if not results:
        return {'influenced_by_news': False, 'confidence': 0.0, 'events': []}
    
    # Count significant moves with reasonable timing
    timely_moves = [r for r in results if r['delay_minutes'] < 60]  # Within an hour
    
    # Calculate confidence based on timing, magnitude, and volume
    if timely_moves:
        avg_pct_change = sum(r['pct_change'] for r in timely_moves) / len(timely_moves)
        avg_volume_ratio = sum(r['volume_ratio'] for r in timely_moves) / len(timely_moves)
        confidence = min(0.5 + (avg_pct_change / 10) + (avg_volume_ratio / 10), 1.0)
    else:
        confidence = 0.0
    
    return {
        'influenced_by_news': confidence > 0.6,
        'confidence': confidence,
        'events': results
    }

def calculate_news_influence_score(price_df: pd.DataFrame, ticker: str, date: datetime) -> Dict[str, Any]:
    """
    Calculate a score representing likelihood that price movement was influenced by news.
    
    Args:
        price_df (pd.DataFrame): Intraday price data
        ticker (str): Stock symbol
        date (datetime): Date to analyze
        
    Returns:
        Dict: Influence analysis results
    """
    # 1. Get news for this ticker around this date
    news = fetch_financial_news(ticker, date - timedelta(days=1), date + timedelta(days=1))
    
    # 2. Filter to relevant news (pre-market and during trading hours)
    market_open = datetime(date.year, date.month, date.day, 9, 30)  # 9:30 AM
    market_close = datetime(date.year, date.month, date.day, 16, 0)  # 4:00 PM
    
    relevant_news = [
        n for n in news 
        if (market_open - timedelta(hours=12)) <= datetime.fromisoformat(n['timestamp']) <= market_close
    ]
    
    # 3. Detect intraday price jumps
    price_jumps = detect_intraday_price_jumps(price_df)
    
    # 4. Correlate news with price movements
    correlation = correlate_price_movement_with_news(price_df, relevant_news)
    
    # 5. Calculate the overall score and classification
    if correlation['influenced_by_news']:
        classification = "News Influenced"
        primary_factor = _determine_primary_factor(correlation['events'])
    else:
        classification = "Technical/Organic"
        primary_factor = "Price action appears driven by technical factors or organic trading"
    
    return {
        'date': date.strftime('%Y-%m-%d'),
        'ticker': ticker,
        'classification': classification,
        'confidence': correlation['confidence'],
        'primary_factor': primary_factor,
        'news_count': len(relevant_news),
        'significant_moves': len(correlation['events']),
        'news_details': [{'time': e['news_time'], 'headline': e['headline'], 'impact': e['pct_change']} 
                         for e in correlation['events']]
    }

def _determine_primary_factor(events: List[Dict]) -> str:
    """Determine the primary factor driving the price movement."""
    if not events:
        return "Unknown"
        
    # Group by news type
    news_types = {}
    for event in events:
        news_type = event['news_type']
        if news_type in news_types:
            news_types[news_type].append(event)
        else:
            news_types[news_type] = [event]
    
    # Find the type with the largest average impact
    largest_impact = 0
    primary_type = "general"
    
    for news_type, type_events in news_types.items():
        avg_impact = sum(abs(e['pct_change']) for e in type_events) / len(type_events)
        if avg_impact > largest_impact:
            largest_impact = avg_impact
            primary_type = news_type
    
    # Format the result
    type_descriptions = {
        'earnings': "Earnings report or financial results",
        'analyst': "Analyst research or ratings change",
        'product': "Product announcement or development",
        'regulatory': "Regulatory news or legal development",
        'management': "Management changes or statements",
        'general': "General market news"
    }
    
    return type_descriptions.get(primary_type, primary_type.title())
```

### 3. Main Scripts

#### New `news_analysis.py`
```python
#!/usr/bin/env python3
"""
News & Research Influence Analysis Tool

This tool analyzes whether daily price increases after market open
are influenced by news or research reports.
"""

import argparse
import sys
import os
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
from typing import List, Dict, Any, Optional

# Import from refactored modules
from data_manager import get_smart_data, get_intraday_data, read_ticker_file
from utils import generate_output_directory, format_date_range, handle_errors
from news_influence import (
    calculate_news_influence_score, 
    fetch_financial_news,
    detect_intraday_price_jumps
)

def analyze_news_influence(
    ticker: str, 
    date_str: str = None,
    days_back: int = 30,
    interval: str = "1h",
    save_to_file: bool = False,
    output_dir: str = "results",
    save_chart: bool = False
):
    """
    Analyze if price increases were influenced by news/research.
    
    Args:
        ticker (str): Stock symbol
        date_str (str, optional): Specific date to analyze (YYYY-MM-DD)
        days_back (int): Days to analyze if no specific date
        interval (str): Data interval for intraday analysis
        save_to_file (bool): Whether to save analysis to file
        output_dir (str): Directory for output files
        save_chart (bool): Whether to save charts
    """
    print(f"\n🔍 ANALYZING NEWS INFLUENCE FOR {ticker}")
    print("="*60)
    
    # Determine analysis date(s)
    if date_str:
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d")
            dates_to_analyze = [target_date]
        except ValueError:
            print(f"❌ Invalid date format: {date_str}. Use YYYY-MM-DD.")
            return
    else:
        end_date = datetime.now()
        dates_to_analyze = [end_date - timedelta(days=i) for i in range(days_back)]
    
    results = []
    
    for analysis_date in dates_to_analyze:
        print(f"\n📅 Analyzing {analysis_date.strftime('%Y-%m-%d')}...")
        
        try:
            # Get intraday data for this date +/- 1 day
            date_from = analysis_date - timedelta(days=1)
            date_to = analysis_date + timedelta(days=1)
            
            # Fetch data
            intraday_data = get_intraday_data(
                ticker=ticker,
                days=3,  # 3 days to cover the range
                interval=interval
            )
            
            # Filter to relevant date range
            mask = (intraday_data.index >= date_from) & (intraday_data.index <= date_to)
            df = intraday_data.loc[mask]
            
            if df.empty:
                print(f"⚠️  No data available for {analysis_date.strftime('%Y-%m-%d')}")
                continue
            
            # Calculate news influence score
            influence_data = calculate_news_influence_score(df, ticker, analysis_date)
            
            # Print summary
            confidence = influence_data['confidence'] * 100
            emoji = "📰" if influence_data['classification'] == "News Influenced" else "📊"
            
            print(f"  {emoji} Classification: {influence_data['classification']}")
            print(f"  ⚖️  Confidence Score: {confidence:.1f}%")
            print(f"  🔍 Primary Factor: {influence_data['primary_factor']}")
            print(f"  📊 News Count: {influence_data['news_count']}")
            
            if influence_data['news_details']:
                print("\n  📰 TOP NEWS IMPACTS:")
                for idx, news in enumerate(sorted(influence_data['news_details'], 
                                              key=lambda x: abs(x['impact']), reverse=True)[:3]):
                    print(f"    {idx+1}. [{news['time'].strftime('%H:%M')}] {news['headline'][:60]}...")
                    print(f"       Impact: {news['impact']:.2f}%")
            
            # Add to results
            results.append(influence_data)
            
            # Generate chart if requested
            if save_chart:
                _generate_news_influence_chart(
                    df=df,
                    ticker=ticker,
                    analysis_date=analysis_date,
                    news_details=influence_data['news_details'],
                    output_dir=output_dir
                )
                
        except Exception as e:
            handle_errors(e, ticker)

def main():
    """
    Main function to handle command-line arguments and run the analysis.
    """
    parser = argparse.ArgumentParser(
        description='📰 News & Research Influence Analysis Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze a single ticker
  python news_analysis.py AAPL                     # Analyze AAPL for past 30 days
  python news_analysis.py TSLA --date 2023-06-15   # Analyze TESLA for specific date
  python news_analysis.py NVDA --interval 30m      # Use 30-minute intervals
  python news_analysis.py MSFT --days 10           # Look back 10 days
  
  # Batch processing
  python news_analysis.py --file stocks.txt        # Process all tickers in stocks.txt
        """
    )
    
    parser.add_argument(
        'ticker', 
        nargs='?',
        help='Stock ticker symbol. Ignored if --file is used.'
    )
    
    parser.add_argument(
        '-f', '--file',
        help='Path to file containing ticker symbols (one per line).'
    )
    
    parser.add_argument(
        '-d', '--date',
        help='Specific date to analyze (YYYY-MM-DD). If not provided, analyzes past --days days.'
    )
    
    parser.add_argument(
        '--days',
        type=int,
        default=30,
        help='Number of days to look back (default: 30).'
    )
    
    parser.add_argument(
        '-i', '--interval',
        default='1h',
        choices=['1h', '30m', '15m', '5m'],
        help='Intraday interval for analysis (default: 1h)'
    )
    
    parser.add_argument(
        '-o', '--output-dir',
        default='results',
        help='Output directory for results (default: results)'
    )
    
    parser.add_argument(
        '--save-charts',
        action='store_true',
        help='Save chart images as PNG files'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.ticker and not args.file:
        parser.error("Either ticker symbol or --file must be provided")
        return
    
    # Create output directory if needed
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
        print(f"📁 Created output directory: {args.output_dir}")
    
    try:
        if args.file:
            # Batch processing mode
            tickers = read_ticker_file(args.file)
            print(f"🚀 Starting batch processing from file: {args.file}")
            
            for i, ticker in enumerate(tickers, 1):
                print(f"\n[{i}/{len(tickers)}] Processing {ticker}...")
                analyze_news_influence(
                    ticker=ticker,
                    date_str=args.date,
                    days_back=args.days,
                    interval=args.interval,
                    save_to_file=True,
                    output_dir=args.output_dir,
                    save_chart=args.save_charts
                )
            
            print(f"\n✅ Batch processing complete!")
        else:
            # Single ticker mode
            analyze_news_influence(
                ticker=args.ticker.upper(),
                date_str=args.date,
                days_back=args.days,
                interval=args.interval,
                save_to_file=True,
                output_dir=args.output_dir,
                save_chart=args.save_charts
            )
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print("Please check your inputs and try again.")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

## Implementation Plan

1. **Code Refactoring**:
   - Extract shared functions from `vol_analysis.py` into the new module structure
   - Update imports in existing code
   - Ensure all tests pass after refactoring

2. **News API Integration**:
   - Research and select appropriate financial news API
   - Implement authentication and data retrieval
   - Add caching for news data to minimize API calls

3. **Algorithm Development**:
   - Develop pattern recognition for price movements
   - Implement news-price correlation logic
   - Create scoring system for influence probability

4. **User Interface**:
   - Command-line arguments for the new feature
   - Report formatting
   - Visualization enhancements

5. **Testing & Validation**:
   - Test with historical cases of known news influence
   - Validate accuracy across different market conditions
   - Optimize algorithms based on results

## Technical Considerations

1. **API Rate Limits**: 
   - Most financial news APIs have rate limits
   - Implement caching and batching strategies

2. **Performance Optimization**:
   - News data processing can be resource-intensive
   - Consider async processing for batch operations

3. **Data Storage**:
   - Add news cache similar to price data cache
   - Consider database integration for larger datasets

4. **Error Handling**:
   - Graceful degradation when news API is unavailable
   - Clear error messages for troubleshooting

## Conclusion

This modular approach allows us to:
1. Maintain the existing functionality
2. Share common code between features
3. Develop the new feature independently
4. Scale the system for future enhancements

Starting with hourly intervals provides a balanced approach that can be refined as the system matures and more data becomes available. The proposed design leverages the strengths of the current implementation while providing a clear path for extending its capabilities with news and research influence analysis.
