"""
General utility functions for the stock analysis system.
"""

import os
from datetime import datetime
import sys
from typing import List, Dict, Any, Optional, Union

def generate_output_directory(base_dir: str) -> str:
    """
    Create and return output directory path.
    
    Args:
        base_dir (str): Base directory path
        
    Returns:
        str: Absolute path to the created directory
    """
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)
        print(f"📁 Created output directory: {base_dir}")
    return os.path.abspath(base_dir)

def format_date_range(start_date: datetime, end_date: datetime) -> str:
    """
    Format a date range as a string.
    
    Args:
        start_date (datetime): Start date
        end_date (datetime): End date
        
    Returns:
        str: Formatted date range string
    """
    return f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"

def handle_errors(error: Exception, ticker: str = None) -> None:
    """
    Handle and format errors.
    
    Args:
        error (Exception): The error to handle
        ticker (str, optional): Stock symbol related to the error
    """
    if ticker:
        print(f"❌ Error processing {ticker}: {str(error)}")
    else:
        print(f"❌ Error: {str(error)}")

def format_percentage(value: float, precision: int = 2) -> str:
    """
    Format a value as a percentage string with sign.
    
    Args:
        value (float): Value to format
        precision (int): Decimal precision
        
    Returns:
        str: Formatted percentage string
    """
    return f"{'+' if value > 0 else ''}{value:.{precision}f}%"

def format_money(value: float, precision: int = 2, currency: str = "$") -> str:
    """
    Format a value as a money string.
    
    Args:
        value (float): Value to format
        precision (int): Decimal precision
        currency (str): Currency symbol
        
    Returns:
        str: Formatted money string
    """
    return f"{currency}{value:.{precision}f}"

def create_filename(ticker: str, analysis_type: str, start_date: Union[datetime, str], 
                   end_date: Union[datetime, str] = None, extension: str = "txt") -> str:
    """
    Create a standardized filename for analysis results.
    
    Args:
        ticker (str): Stock symbol
        analysis_type (str): Type of analysis
        start_date (Union[datetime, str]): Start date
        end_date (Union[datetime, str], optional): End date
        extension (str): File extension
        
    Returns:
        str: Formatted filename
    """
    # Convert dates to strings if they're datetime objects
    if isinstance(start_date, datetime):
        start_date = start_date.strftime("%Y%m%d")
    
    if end_date is None:
        date_part = start_date
    else:
        if isinstance(end_date, datetime):
            end_date = end_date.strftime("%Y%m%d")
        date_part = f"{start_date}_{end_date}"
    
    return f"{ticker}_{analysis_type}_{date_part}.{extension}"

def parse_date_string(date_str: str) -> Optional[datetime]:
    """
    Parse a date string into a datetime object.
    
    Args:
        date_str (str): Date string in format 'YYYY-MM-DD'
        
    Returns:
        Optional[datetime]: Parsed datetime object or None if invalid
    """
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        print(f"⚠️  Invalid date format: {date_str}. Expected format: YYYY-MM-DD")
        return None

def is_data_stale(data_date: datetime, threshold_hours: int = 24) -> bool:
    """
    Check if data is stale, accounting for weekends.
    
    On weekends (Saturday/Sunday), data from Friday is considered current
    since no market data is available on weekends. This prevents false
    "data is stale" warnings when Friday's data is the most recent available.
    
    Args:
        data_date (datetime): The date of the data to check
        threshold_hours (int): Hours after which data is considered stale (default: 24)
        
    Returns:
        bool: True if data is stale, False if current
        
    Example:
        >>> # On Saturday with Friday's data
        >>> friday_data = datetime(2025, 11, 21, 16, 0)  # Friday 4 PM
        >>> is_data_stale(friday_data)  # Returns False (not stale on weekend)
        
        >>> # On Tuesday with Friday's data  
        >>> is_data_stale(friday_data)  # Returns True (stale on weekday)
    """
    now = datetime.now()
    age_hours = (now - data_date).total_seconds() / 3600
    
    # On weekends, accept data up to 48 hours old (Friday's data)
    # Saturday=5, Sunday=6
    is_weekend = now.weekday() >= 5
    adjusted_threshold = 48 if is_weekend else threshold_hours
    
    return age_hours > adjusted_threshold

def get_trading_days_between(start_date: datetime, end_date: datetime) -> int:
    """
    Estimate the number of trading days between two dates.
    This is a simple approximation assuming 252 trading days per year.
    
    Args:
        start_date (datetime): Start date
        end_date (datetime): End date
        
    Returns:
        int: Estimated number of trading days
    """
    # Simple calculation - doesn't account for holidays
    total_days = (end_date - start_date).days
    weeks = total_days // 7
    remaining_days = total_days % 7
    
    # Calculate weekend days in the remaining days
    weekend_days = sum(1 for i in range(remaining_days) 
                      if (start_date + datetime.timedelta(days=i)).weekday() >= 5)
    
    trading_days = total_days - (weeks * 2) - weekend_days
    return max(0, trading_days)

def summarize_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate summary statistics from a list of result dictionaries.
    
    Args:
        results (List[Dict[str, Any]]): List of analysis result dictionaries
        
    Returns:
        Dict[str, Any]: Summary statistics
    """
    if not results:
        return {
            'count': 0,
            'summary': "No results available"
        }
    
    return {
        'count': len(results),
        'summary': f"Processed {len(results)} items"
    }

def print_progress_bar(iteration: int, total: int, prefix: str = '', suffix: str = '', 
                       decimals: int = 1, length: int = 50, fill: str = '█') -> None:
    """
    Print a progress bar to the console.
    
    Args:
        iteration (int): Current iteration
        total (int): Total iterations
        prefix (str): Prefix string
        suffix (str): Suffix string
        decimals (int): Decimal places in percent
        length (int): Character length of bar
        fill (str): Bar fill character
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end='\r')
    
    # Print new line on complete
    if iteration == total:
        print()
