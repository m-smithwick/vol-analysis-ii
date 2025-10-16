"""
News influence analysis module for detecting when price increases are influenced by news or research.
With Gemini Pro integration for financial news fetching.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import requests
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("⚠️ google-generativeai package not found. Install it with 'pip install google-generativeai' to use Gemini Pro for news.")

# Constants
NEWS_CACHE_DIR = "news_cache"
NEWS_API_KEY = None  # Configure via environment variable or settings file
GEMINI_API_KEY_PATH = "gemini-api-key"  # Path to Gemini API key file

# Ensure news cache directory exists
if not os.path.exists(NEWS_CACHE_DIR):
    os.makedirs(NEWS_CACHE_DIR)

def _load_gemini_api_key():
    """Load Gemini API key from file."""
    try:
        with open(GEMINI_API_KEY_PATH, 'r') as f:
            return f.read().strip()
    except Exception as e:
        print(f"⚠️ Error loading Gemini API key: {str(e)}")
        return None

def fetch_financial_news_from_gemini(ticker: str, start_date: datetime, end_date: datetime) -> List[Dict]:
    """
    Fetch financial news for a ticker using Google's Gemini Pro.
    
    Args:
        ticker (str): Stock symbol
        start_date (datetime): Start date for news
        end_date (datetime): End date for news
        
    Returns:
        List[Dict]: List of news items with timestamp, headline, etc.
    """
    if not GEMINI_AVAILABLE:
        return []
    
    api_key = _load_gemini_api_key()
    if not api_key:
        print("⚠️ No Gemini API key found")
        return []
    
    # Configure Gemini with the API key
    genai.configure(api_key=api_key)
    
    # Format the prompt for Gemini
    prompt = f"""
    Please provide financial news for {ticker} stock from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}.
    
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
    
    Provide 3-5 most significant news items for this period.
    """
    
    try:
        # Call Gemini 2.5 Flash instead of Gemini Pro (which is no longer available)
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        
        # Parse the response (assuming it returns proper JSON)
        # Extract JSON string from response
        # This regex finds anything that looks like a JSON array
        json_match = re.search(r'\[\s*{.*}\s*\]', response.text, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            news_items = json.loads(json_str)
        else:
            news_items = json.loads(response.text)
            
        # Add type field based on headline content
        for item in news_items:
            item['type'] = classify_news_type(item.get('headline', '') + ' ' + item.get('summary', ''))
        
        print(f"📰 Retrieved {len(news_items)} news items from Gemini for {ticker}")
        return news_items
    except Exception as e:
        print(f"⚠️ Error getting news from Gemini: {str(e)}")
        return []

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
    df_temp = df.copy()
    df_temp['pct_change'] = df_temp['Close'].pct_change() * 100
    
    # Find intervals with significant price increases
    jump_indices = df_temp[df_temp['pct_change'] > threshold].index.tolist()
    
    return jump_indices

def fetch_financial_news(ticker: str, start_date: datetime, end_date: Optional[datetime] = None) -> List[Dict]:
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
    
    # Try Gemini Pro first
    news_items = fetch_financial_news_from_gemini(ticker, start_date, end_date)
    if news_items:
        # Cache the results
        _save_to_news_cache(ticker, start_date, end_date, news_items)
        return news_items
    
    # Fall back to Alpha Vantage if Gemini fails
    try:
        # Try to get actual news from a free API (Alpha Vantage news endpoint if key is provided)
        api_key = os.environ.get('ALPHA_VANTAGE_API_KEY', NEWS_API_KEY)
        
        if api_key:
            # Alpha Vantage news API
            start_str = start_date.strftime('%Y-%m-%d')
            end_str = end_date.strftime('%Y-%m-%d')
            url = f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={ticker}&time_from={start_str}T0000&time_to={end_str}T2359&apikey={api_key}"
            
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                
                # Format the news data into our standard format
                news_items = []
                if 'feed' in data:
                    for item in data['feed']:
                        timestamp = item.get('time_published', '')
                        if timestamp:
                            # Format: 20230131T120000
                            timestamp = f"{timestamp[:4]}-{timestamp[4:6]}-{timestamp[6:8]}T{timestamp[9:11]}:{timestamp[11:13]}:{timestamp[13:15]}"
                        
                        news_items.append({
                            'timestamp': timestamp,
                            'headline': item.get('title', ''),
                            'summary': item.get('summary', ''),
                            'source': item.get('source', ''),
                            'url': item.get('url', ''),
                            'sentiment': item.get('overall_sentiment_score', 0),
                            'relevance': item.get('relevance_score', {}).get(ticker, 0)
                        })
                    
                    # Cache the results
                    _save_to_news_cache(ticker, start_date, end_date, news_items)
                    return news_items
                else:
                    print(f"⚠️ No news data found in API response for {ticker}")
            else:
                print(f"⚠️ Failed to fetch news: {response.status_code}")
    except Exception as e:
        print(f"⚠️ Error fetching news from API: {str(e)}")
    
    # If we reach here, all external sources failed
    # Generate mock news data as fallback
    return _generate_mock_news(ticker, start_date, end_date)

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
        'earnings': ['earnings', 'revenue', 'profit', 'eps', 'quarterly', 'financial results', 'q1', 'q2', 'q3', 'q4'],
        'analyst': ['upgrade', 'downgrade', 'rating', 'price target', 'analyst', 'research', 'overweight', 'underweight', 'neutral', 'buy rating', 'sell rating', 'outperform'],
        'product': ['launch', 'release', 'announce', 'unveil', 'new product', 'innovation', 'patent'],
        'regulatory': ['sec', 'regulation', 'lawsuit', 'legal', 'investigation', 'compliance', 'fda', 'approval'],
        'management': ['ceo', 'executive', 'management', 'appoint', 'resign', 'leadership', 'board', 'director'],
        'merger': ['merger', 'acquisition', 'takeover', 'buyout', 'consolidation', 'purchase'],
        'dividend': ['dividend', 'payout', 'yield', 'distribution'],
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
        # Parse the timestamp string to datetime
        try:
            if 'timestamp' not in news or not news['timestamp']:
                continue
            
            # Convert to timezone-naive datetime for comparison
            news_time = pd.to_datetime(news['timestamp'])
            if news_time.tzinfo is not None:
                news_time = news_time.tz_localize(None)
            
            # Find the first price data point after the news
            # Ensure price_df index is also timezone-naive
            price_df_naive = price_df.copy()
            if price_df_naive.index.tzinfo is not None:
                price_df_naive.index = price_df_naive.index.tz_localize(None)
            
            post_news_data = price_df_naive[price_df_naive.index > news_time]
            if post_news_data.empty:
                continue
                
            # Calculate price change after news
            first_idx = post_news_data.index[0]
            
            # Find the price point right before the news
            pre_news_indices = price_df[price_df.index <= news_time].index
            if pre_news_indices.empty:
                continue
                
            pre_news_idx = pre_news_indices[-1]
            pre_news_price = price_df.loc[pre_news_idx, 'Close']
            
            # Look at price movement over next several periods
            for i in range(min(look_ahead_periods, len(post_news_data))):
                if i >= len(post_news_data):
                    break
                    
                period_idx = post_news_data.index[i]
                period_price = post_news_data.iloc[i]['Close']
                pct_change = ((period_price - pre_news_price) / pre_news_price) * 100
                
                # Get volume data
                try:
                    volume = post_news_data.iloc[i]['Volume']
                    avg_volume = price_df['Volume'].mean()
                    volume_vs_avg = volume / avg_volume
                except (KeyError, ValueError):
                    volume_vs_avg = 1.0
                
                # Determine if this movement is significant
                is_significant = abs(pct_change) > 1.0 and volume_vs_avg > 1.2
                
                # If we have sentiment data from the API, use it to enhance analysis
                sentiment = news.get('sentiment', 0)
                relevance = news.get('relevance', 0)
                
                # For positive sentiment, we expect price to go up
                # For negative sentiment, we expect price to go down
                sentiment_aligned = (sentiment > 0 and pct_change > 0) or (sentiment < 0 and pct_change < 0)
                
                if is_significant:
                    results.append({
                        'news_time': news_time,
                        'price_time': period_idx,
                        'delay_minutes': (period_idx - news_time).total_seconds() / 60,
                        'pct_change': pct_change,
                        'volume_ratio': volume_vs_avg,
                        'sentiment': sentiment,
                        'relevance': relevance,
                        'sentiment_aligned': sentiment_aligned,
                        'news_type': news.get('type', classify_news_type(news.get('headline', ''))),
                        'headline': news.get('headline', 'N/A')
                    })
        except Exception as e:
            print(f"⚠️ Error processing news item: {str(e)}")
            continue
    
    # Calculate overall influence
    if not results:
        return {'influenced_by_news': False, 'confidence': 0.0, 'events': []}
    
    # Count significant moves with reasonable timing
    timely_moves = [r for r in results if r['delay_minutes'] < 60]  # Within an hour
    
    # Calculate confidence based on timing, magnitude, and volume
    if timely_moves:
        avg_pct_change = sum(r['pct_change'] for r in timely_moves) / len(timely_moves)
        avg_volume_ratio = sum(r['volume_ratio'] for r in timely_moves) / len(timely_moves)
        
        # Base confidence calculation
        confidence = min(0.5 + (abs(avg_pct_change) / 10) + (avg_volume_ratio / 10), 1.0)
        
        # Enhance with sentiment alignment if available
        sentiment_alignments = [r.get('sentiment_aligned', True) for r in timely_moves]
        alignment_ratio = sum(1 for a in sentiment_alignments if a) / len(sentiment_alignments)
        
        # Adjust confidence based on sentiment alignment
        confidence = confidence * (0.5 + 0.5 * alignment_ratio)
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
    # Ensure the input date is timezone-naive
    if hasattr(date, 'tzinfo') and date.tzinfo is not None:
        date = date.replace(tzinfo=None)
        
    # 1. Get news for this ticker around this date
    news = fetch_financial_news(ticker, date - timedelta(days=1), date + timedelta(days=1))
    
    # 2. Filter to relevant news (pre-market and during trading hours)
    market_open = datetime(date.year, date.month, date.day, 9, 30)  # 9:30 AM
    market_close = datetime(date.year, date.month, date.day, 16, 0)  # 4:00 PM
    
    relevant_news = []
    for n in news:
        try:
            if 'timestamp' not in n or not n['timestamp']:
                continue
            
            # Ensure consistent timezone handling
            news_time = pd.to_datetime(n['timestamp'])
            if news_time.tzinfo is not None:
                news_time = news_time.replace(tzinfo=None)
                
            if (market_open - timedelta(hours=12)) <= news_time <= market_close:
                # Add news type if not present
                if 'type' not in n:
                    n['type'] = classify_news_type(n.get('headline', '') + ' ' + n.get('summary', ''))
                relevant_news.append(n)
        except Exception as e:
            print(f"⚠️ Error processing news item timestamp: {str(e)}")
    
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
    
    # 6. Identify the most significant news event if any
    significant_event = None
    if correlation['events']:
        # Sort by absolute percentage change
        sorted_events = sorted(correlation['events'], key=lambda x: abs(x['pct_change']), reverse=True)
        if sorted_events:
            significant_event = sorted_events[0]
    
    # 7. Create comprehensive result
    return {
        'date': date.strftime('%Y-%m-%d'),
        'ticker': ticker,
        'classification': classification,
        'confidence': correlation['confidence'],
        'primary_factor': primary_factor,
        'news_count': len(relevant_news),
        'significant_moves': len(correlation['events']),
        'news_details': [{'time': e['news_time'], 'headline': e['headline'], 'impact': e['pct_change']} 
                         for e in correlation['events']],
        'price_jumps': len(price_jumps),
        'significant_event': significant_event,
        'market_open': market_open,
        'market_close': market_close
    }

def analyze_multiple_days(ticker: str, start_date: datetime, end_date: datetime, interval: str = "1h") -> List[Dict]:
    """
    Analyze news influence for a ticker over multiple days.
    
    Args:
        ticker (str): Stock symbol
        start_date (datetime): Start date
        end_date (datetime): End date
        interval (str): Data interval ('1h', '30m', etc.)
        
    Returns:
        List[Dict]: List of daily analysis results
    """
    from data_manager import get_intraday_data
    
    results = []
    current_date = start_date
    
    while current_date <= end_date:
        try:
            # Get intraday data for this date +/- 1 day
            date_from = current_date - timedelta(days=1)
            date_to = current_date + timedelta(days=1)
            
            # Calculate total days needed based on the full analysis period
            total_days_needed = (end_date - start_date).days + 3  # Add 3 for buffer (1 before start, 1 after end, 1 for inclusive count)
            
            # Fetch data for the full range needed - ensure we get at least total_days_needed
            intraday_data = get_intraday_data(
                ticker=ticker,
                days=max(total_days_needed, 30),  # Ensure we get at least 30 days or what's needed, whichever is greater
                interval=interval
            )
            
            # Ensure datetime objects are consistently timezone-naive for comparison
            if intraday_data.index.tzinfo is not None:
                # Convert to timezone-naive index for filtering
                naive_index = intraday_data.index.tz_localize(None)
                intraday_data.index = naive_index
            
            # Ensure date_from and date_to are timezone-naive for comparison
            if getattr(date_from, 'tzinfo', None) is not None:
                date_from = date_from.replace(tzinfo=None)
            if getattr(date_to, 'tzinfo', None) is not None:
                date_to = date_to.replace(tzinfo=None)
            
            # Filter to the complete date range
            mask = (intraday_data.index >= date_from) & (intraday_data.index <= date_to)
            df = intraday_data.loc[mask]
            
            if not df.empty:
                # Calculate news influence score
                result = calculate_news_influence_score(df, ticker, current_date)
                results.append(result)
                
        except Exception as e:
            print(f"⚠️ Error analyzing {ticker} on {current_date.strftime('%Y-%m-%d')}: {str(e)}")
        
        # Move to next day
        current_date += timedelta(days=1)
    
    return results

def batch_analyze_tickers(tickers: List[str], start_date: datetime, end_date: datetime, interval: str = "1h", 
                          max_workers: int = 5) -> Dict[str, List[Dict]]:
    """
    Analyze news influence for multiple tickers in parallel.
    
    Args:
        tickers (List[str]): List of stock symbols
        start_date (datetime): Start date
        end_date (datetime): End date
        interval (str): Data interval ('1h', '30m', etc.)
        max_workers (int): Maximum number of parallel workers
        
    Returns:
        Dict[str, List[Dict]]: Dictionary of ticker -> results list
    """
    results = {}
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit tasks
        future_to_ticker = {
            executor.submit(analyze_multiple_days, ticker, start_date, end_date, interval): ticker 
            for ticker in tickers
        }
        
        # Process results as they complete
        for future in concurrent.futures.as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            try:
                ticker_results = future.result()
                results[ticker] = ticker_results
            except Exception as e:
                print(f"⚠️ Error processing {ticker}: {str(e)}")
                results[ticker] = []
    
    return results

def _determine_primary_factor(events: List[Dict]) -> str:
    """
    Determine the primary factor driving the price movement.
    
    Args:
        events (List[Dict]): List of news-price correlation events
        
    Returns:
        str: Description of the primary factor
    """
    if not events:
        return "Unknown"
        
    # Group by news type
    news_types = {}
    for event in events:
        news_type = event['news_type']
        if news_type not in news_types:
            news_types[news_type] = []
        news_types[news_type].append(event)
    
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
        'merger': "Merger or acquisition activity",
        'dividend': "Dividend announcement",
        'general': "General market news"
    }
    
    return type_descriptions.get(primary_type, primary_type.title())

def _check_news_cache(ticker: str, start_date: datetime, end_date: Optional[datetime] = None) -> Optional[List[Dict]]:
    """
    Check if news is available in cache.
    
    Args:
        ticker (str): Stock symbol
        start_date (datetime): Start date
        end_date (datetime, optional): End date
        
    Returns:
        Optional[List[Dict]]: Cached news data or None
    """
    # Ensure dates are timezone-naive
    if hasattr(start_date, 'tzinfo') and start_date.tzinfo is not None:
        start_date = start_date.replace(tzinfo=None)
        
    if end_date is None:
        end_date = start_date + timedelta(days=1)
    elif hasattr(end_date, 'tzinfo') and end_date.tzinfo is not None:
        end_date = end_date.replace(tzinfo=None)
        
    cache_key = f"{ticker}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
    cache_file = os.path.join(NEWS_CACHE_DIR, f"{cache_key}.json")
    
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r') as f:
                return json.load(f)
        except:
            return None
    
    return None

def _save_to_news_cache(ticker: str, start_date: datetime, end_date: Optional[datetime], news_data: List[Dict]) -> None:
    """
    Save news data to cache.
    
    Args:
        ticker (str): Stock symbol
        start_date (datetime): Start date
        end_date (datetime, optional): End date
        news_data (List[Dict]): News data to cache
    """
    # Ensure dates are timezone-naive
    if hasattr(start_date, 'tzinfo') and start_date.tzinfo is not None:
        start_date = start_date.replace(tzinfo=None)
        
    if end_date is None:
        end_date = start_date + timedelta(days=1)
    elif hasattr(end_date, 'tzinfo') and end_date.tzinfo is not None:
        end_date = end_date.replace(tzinfo=None)
        
    cache_key = f"{ticker}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
    cache_file = os.path.join(NEWS_CACHE_DIR, f"{cache_key}.json")
    
    try:
        with open(cache_file, 'w') as f:
            json.dump(news_data, f)
    except Exception as e:
        print(f"⚠️ Error saving to news cache: {str(e)}")

def _generate_mock_news(ticker: str, start_date: datetime, end_date: datetime) -> List[Dict]:
    """
    Generate mock news data for testing and demonstration.
    
    Args:
        ticker (str): Stock symbol
        start_date (datetime): Start date
        end_date (datetime): End date
        
    Returns:
        List[Dict]: Mock news items
    """
    news_items = []
    current_date = start_date
    
    # Generate mock news for the requested period
    while current_date <= end_date:
        # Generate 0-3 news items per day
        n_items = np.random.randint(0, 4)
        
        for _ in range(n_items):
            # Randomly assign a time during the day
            hour = np.random.randint(5, 18)  # 5 AM to 6 PM
            minute = np.random.randint(0, 60)
            
            news_time = current_date.replace(hour=hour, minute=minute)
            
            # Generate news type
            news_types = ['earnings', 'analyst', 'product', 'regulatory', 'management', 'general']
            weights = [0.15, 0.25, 0.15, 0.1, 0.1, 0.25]
            news_type = np.random.choice(news_types, p=weights)
            
            # Generate headline based on type
            headlines = {
                'earnings': [
                    f"{ticker} Reports Q{np.random.randint(1, 5)} Earnings",
                    f"{ticker} Beats Earnings Estimates",
                    f"{ticker} Misses Revenue Expectations",
                    f"{ticker} Raises Full-Year Guidance"
                ],
                'analyst': [
                    f"Analyst Upgrades {ticker} to Buy",
                    f"Goldman Sachs Raises {ticker} Price Target",
                    f"Morgan Stanley Initiates {ticker} Coverage with Overweight Rating",
                    f"JPMorgan Downgrades {ticker} to Neutral"
                ],
                'product': [
                    f"{ticker} Unveils New Product Line",
                    f"{ticker} Announces Partnership with Major Tech Company",
                    f"{ticker} Launches Next-Generation Platform",
                    f"{ticker} Files Patent for Innovative Technology"
                ],
                'regulatory': [
                    f"{ticker} Receives FDA Approval",
                    f"{ticker} Settles Regulatory Investigation",
                    f"{ticker} Faces New Legal Challenge",
                    f"Regulators Review {ticker}'s Market Practices"
                ],
                'management': [
                    f"{ticker} Names New CEO",
                    f"{ticker} CFO Steps Down",
                    f"{ticker} Announces Board Restructuring",
                    f"{ticker} Expands Leadership Team"
                ],
                'general': [
                    f"{ticker} Shares Trade Higher on Market Optimism",
                    f"{ticker} Stock Volatile Amid Sector Rotation",
                    f"{ticker} Mentioned in Industry Report",
                    f"{ticker} Among Most Active Stocks Today"
                ]
            }
            
            headline = np.random.choice(headlines[news_type])
            
            # Generate sentiment (more positive for product announcements, mixed for others)
            if news_type == 'product':
                sentiment = np.random.uniform(0.2, 0.8)
            elif news_type == 'regulatory':
                sentiment = np.random.uniform(-0.7, 0.3)
            else:
                sentiment = np.random.uniform(-0.5, 0.5)
            
            news_items.append({
                'timestamp': news_time.isoformat(),
                'headline': headline,
                'summary': f"This is a mock summary for {ticker} news on {news_time.strftime('%Y-%m-%d')}.",
                'source': np.random.choice(['Reuters', 'Bloomberg', 'CNBC', 'WSJ', 'MarketWatch']),
                'url': f"https://example.com/news/{ticker}/{news_time.strftime('%Y%m%d')}/{np.random.randint(1000, 9999)}",
                'type': news_type,
                'sentiment': sentiment,
                'relevance': np.random.uniform(0.5, 1.0)
            })
        
        current_date += timedelta(days=1)
    
    # Cache this mock data
    _save_to_news_cache(ticker, start_date, end_date, news_items)
    
    return news_items

def clear_news_cache(ticker: str = None, start_date: datetime = None, end_date: datetime = None) -> None:
    """
    Clear news cache for a specific ticker and date range, or all cache.
    
    Args:
        ticker (str, optional): Stock symbol
        start_date (datetime, optional): Start date
        end_date (datetime, optional): End date
    """
    if ticker and start_date and end_date:
        # Clear specific ticker and date range
        cache_key = f"{ticker}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
        cache_file = os.path.join(NEWS_CACHE_DIR, f"{cache_key}.json")
        if os.path.exists(cache_file):
            os.remove(cache_file)
            print(f"🗑️  Cleared news cache for {ticker} from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        else:
            print(f"ℹ️  No cache found for {ticker} in the specified date range")
    
    elif ticker:
        # Clear all cache for ticker
        files_removed = 0
        for file in os.listdir(NEWS_CACHE_DIR):
            if file.startswith(f"{ticker}_") and file.endswith(".json"):
                os.remove(os.path.join(NEWS_CACHE_DIR, file))
                files_removed += 1
        
        if files_removed > 0:
            print(f"🗑️  Cleared {files_removed} news cache files for {ticker}")
        else:
            print(f"ℹ️  No news cache files found for {ticker}")
    
    else:
        # Clear entire cache directory
        if os.path.exists(NEWS_CACHE_DIR):
            for file in os.listdir(NEWS_CACHE_DIR):
                if file.endswith(".json"):
                    os.remove(os.path.join(NEWS_CACHE_DIR, file))
            print(f"🗑️  Cleared all news cache files")
        else:
            print(f"ℹ️  No news cache directory found")
