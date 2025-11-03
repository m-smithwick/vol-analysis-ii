"""
Error handling and validation framework for vol-analysis-ii.

This module provides centralized error handling, structured logging,
and validation utilities for the volume analysis system.
"""

import logging
import os
import sys
import traceback
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path
import pandas as pd


# Custom Exception Classes
class VolumeAnalysisError(Exception):
    """Base exception for volume analysis errors."""
    pass


class DataValidationError(VolumeAnalysisError):
    """Raised when data validation fails."""
    pass


class CacheError(VolumeAnalysisError):
    """Raised when cache operations fail."""
    pass


class DataDownloadError(VolumeAnalysisError):
    """Raised when data download operations fail."""
    pass


class ConfigurationError(VolumeAnalysisError):
    """Raised when configuration is invalid."""
    pass


class FileOperationError(VolumeAnalysisError):
    """Raised when file operations fail."""
    pass


# Error Context Manager
class ErrorContext:
    """Context manager for error handling with automatic logging."""
    
    def __init__(self, operation: str, ticker: str = None, **context):
        self.operation = operation
        self.ticker = ticker
        self.context = context
        self.logger = get_logger()
    
    def __enter__(self):
        context_str = f"ticker={self.ticker}" if self.ticker else ""
        if self.context:
            context_items = [f"{k}={v}" for k, v in self.context.items()]
            if context_str:
                context_str += f", {', '.join(context_items)}"
            else:
                context_str = ', '.join(context_items)
        
        self.logger.debug(f"Starting operation: {self.operation} ({context_str})")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.logger.debug(f"Operation completed successfully: {self.operation}")
            return False
        
        # Log the error with context
        error_msg = f"Operation failed: {self.operation}"
        if self.ticker:
            error_msg += f" (ticker={self.ticker})"
        
        if issubclass(exc_type, VolumeAnalysisError):
            # Our custom errors - log at warning level
            self.logger.warning(f"{error_msg}: {exc_val}")
        else:
            # Unexpected errors - log at error level with traceback
            self.logger.error(f"{error_msg}: {exc_val}", exc_info=True)
        
        return False  # Don't suppress the exception


# Logging Configuration
def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None) -> logging.Logger:
    """
    Set up structured logging for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path. If None, logs only to console.
    
    Returns:
        Logger instance
    """
    # Remove existing handlers to avoid duplicates
    logger = logging.getLogger("vol_analysis")
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_file:
        # Ensure log directory exists
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)  # File gets everything
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger() -> logging.Logger:
    """Get or create the application logger."""
    logger = logging.getLogger("vol_analysis")
    if not logger.handlers:
        # Set up default logging if not already configured
        setup_logging()
    return logger


# Validation Functions
def validate_ticker(ticker: str) -> str:
    """
    Validate and normalize ticker symbol.
    
    Args:
        ticker: Raw ticker symbol
        
    Returns:
        Normalized ticker symbol
        
    Raises:
        DataValidationError: If ticker is invalid
    """
    if not ticker or not isinstance(ticker, str):
        raise DataValidationError(f"Invalid ticker: {ticker}. Must be a non-empty string.")
    
    # Normalize ticker
    ticker = ticker.strip().upper()
    
    if not ticker:
        raise DataValidationError("Ticker cannot be empty or whitespace only.")
    
    # Basic validation - check for invalid characters
    if not ticker.replace('.', '').replace('-', '').isalnum():
        raise DataValidationError(f"Invalid ticker format: {ticker}. Contains invalid characters.")
    
    if len(ticker) > 10:
        raise DataValidationError(f"Ticker too long: {ticker}. Must be 10 characters or less.")
    
    return ticker


def validate_period(period: str) -> str:
    """
    Validate analysis period parameter.
    
    Args:
        period: Time period string (e.g., '1mo', '12mo', '2y')
        
    Returns:
        Validated period string
        
    Raises:
        DataValidationError: If period is invalid
    """
    if not period or not isinstance(period, str):
        raise DataValidationError(f"Invalid period: {period}. Must be a non-empty string.")
    
    period = period.strip().lower()
    
    # Valid periods for yfinance
    valid_periods = {
        '1d', '5d', '1mo', '3mo', '6mo', '12mo', '24mo', '36mo', 
        '60mo', '120mo', 'ytd', 'max',
        # Legacy formats (will be normalized)
        '1y', '2y', '3y', '5y', '10y', '1yr', '2yr', '3yr', '5yr', '10yr'
    }
    
    if period not in valid_periods:
        raise DataValidationError(
            f"Invalid period: {period}. Must be one of: {', '.join(sorted(valid_periods))}"
        )
    
    return period


def validate_dataframe(df: pd.DataFrame, required_columns: List[str] = None) -> None:
    """
    Validate DataFrame structure and content.
    
    Args:
        df: DataFrame to validate
        required_columns: List of required column names
        
    Raises:
        DataValidationError: If DataFrame is invalid
    """
    if df is None:
        raise DataValidationError("DataFrame cannot be None")
    
    if df.empty:
        raise DataValidationError("DataFrame cannot be empty")
    
    if required_columns:
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise DataValidationError(
                f"Missing required columns: {missing_columns}. "
                f"Available columns: {list(df.columns)}"
            )
    
    # Check for all-NaN data
    if df.isnull().all().all():
        raise DataValidationError("DataFrame contains only NaN values")
    
    # Validate index
    if not isinstance(df.index, pd.DatetimeIndex):
        raise DataValidationError("DataFrame must have a DatetimeIndex")


def validate_file_path(filepath: str, check_exists: bool = True, 
                      check_readable: bool = True, check_writable: bool = False) -> Path:
    """
    Validate file path and permissions.
    
    Args:
        filepath: Path to validate
        check_exists: Whether file must exist
        check_readable: Whether file must be readable
        check_writable: Whether file/directory must be writable
        
    Returns:
        Validated Path object
        
    Raises:
        FileOperationError: If file validation fails
    """
    if not filepath:
        raise FileOperationError("File path cannot be empty")
    
    path = Path(filepath)
    
    if check_exists and not path.exists():
        raise FileOperationError(f"File does not exist: {filepath}")
    
    if check_exists and check_readable and not os.access(path, os.R_OK):
        raise FileOperationError(f"File is not readable: {filepath}")
    
    if check_writable:
        # For new files, check if parent directory is writable
        if not path.exists():
            parent = path.parent
            if not parent.exists():
                try:
                    parent.mkdir(parents=True, exist_ok=True)
                except OSError as e:
                    raise FileOperationError(f"Cannot create directory: {parent}. {e}")
            
            if not os.access(parent, os.W_OK):
                raise FileOperationError(f"Directory is not writable: {parent}")
        else:
            if not os.access(path, os.W_OK):
                raise FileOperationError(f"File is not writable: {filepath}")
    
    return path


# Retry Decorator
def retry_on_failure(max_attempts: int = 3, delay: float = 1.0, 
                    exceptions: tuple = (Exception,)):
    """
    Decorator to retry function calls on failure.
    
    Args:
        max_attempts: Maximum number of attempts
        delay: Delay between attempts in seconds
        exceptions: Tuple of exception types to catch and retry on
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger = get_logger()
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts - 1:
                        # Last attempt failed
                        break
                    
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay} seconds..."
                    )
                    
                    import time
                    time.sleep(delay)
            
            # All attempts failed
            logger.error(f"All {max_attempts} attempts failed for {func.__name__}")
            raise last_exception
        
        return wrapper
    return decorator


# Error Recovery Functions
def handle_cache_error(cache_file: str, error: Exception) -> bool:
    """
    Handle cache-related errors with automatic recovery.
    
    Args:
        cache_file: Path to problematic cache file
        error: Original exception
        
    Returns:
        True if error was handled and cache cleaned up, False otherwise
    """
    logger = get_logger()
    
    try:
        cache_path = Path(cache_file)
        
        if cache_path.exists():
            # Try to backup corrupted cache before removing
            backup_path = cache_path.with_suffix(f'.corrupted.{datetime.now().strftime("%Y%m%d_%H%M%S")}')
            
            try:
                cache_path.rename(backup_path)
                logger.info(f"Moved corrupted cache to: {backup_path}")
            except OSError:
                # If backup fails, just remove the file
                cache_path.unlink()
                logger.info(f"Removed corrupted cache file: {cache_file}")
            
            return True
        
    except Exception as cleanup_error:
        logger.error(f"Failed to clean up corrupted cache {cache_file}: {cleanup_error}")
        return False
    
    return False


def create_error_report(error: Exception, context: Dict[str, Any] = None) -> str:
    """
    Create detailed error report for debugging.
    
    Args:
        error: Exception that occurred
        context: Additional context information
        
    Returns:
        Formatted error report string
    """
    report_lines = []
    report_lines.append("=" * 60)
    report_lines.append("ERROR REPORT")
    report_lines.append("=" * 60)
    report_lines.append(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"Error Type: {type(error).__name__}")
    report_lines.append(f"Error Message: {str(error)}")
    
    if context:
        report_lines.append("\nContext:")
        for key, value in context.items():
            report_lines.append(f"  {key}: {value}")
    
    report_lines.append("\nTraceback:")
    report_lines.append(traceback.format_exc())
    
    report_lines.append("=" * 60)
    
    return "\n".join(report_lines)


# Configuration Management
class ErrorHandlerConfig:
    """Configuration for error handler behavior."""
    
    def __init__(self):
        self.log_level = "INFO"
        self.log_file = None
        self.max_retries = 3
        self.retry_delay = 1.0
        self.auto_cleanup_cache = True
        self.create_error_reports = False
        self.error_report_dir = "error_reports"
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'ErrorHandlerConfig':
        """Create configuration from dictionary."""
        config = cls()
        for key, value in config_dict.items():
            if hasattr(config, key):
                setattr(config, key, value)
        return config


# Initialize default configuration
_default_config = ErrorHandlerConfig()

# Initialize module-level logger
logger = get_logger()

# Export list
__all__ = [
    # Exceptions
    'VolumeAnalysisError', 'DataValidationError', 'CacheError', 
    'DataDownloadError', 'ConfigurationError', 'FileOperationError',
    
    # Core classes and functions
    'ErrorContext', 'logger', 'get_logger', 'setup_logging',
    
    # Validation functions
    'validate_ticker', 'validate_period', 'validate_dataframe', 'validate_file_path',
    
    # Utilities
    'retry_on_failure', 'safe_operation', 'handle_cache_error',
    'create_error_report', 'configure_error_handler', 'get_config',
    'ErrorHandlerConfig'
]


def configure_error_handler(config: ErrorHandlerConfig = None) -> None:
    """Configure the error handler with custom settings."""
    global _default_config
    if config:
        _default_config = config
    
    # Set up logging with new configuration
    setup_logging(
        log_level=_default_config.log_level,
        log_file=_default_config.log_file
    )


def get_config() -> ErrorHandlerConfig:
    """Get current error handler configuration."""
    return _default_config


# Convenience function for common error handling pattern
def safe_operation(operation_name: str, func, *args, ticker: str = None, **kwargs):
    """
    Execute operation with standardized error handling.
    
    Args:
        operation_name: Description of the operation
        func: Function to execute
        *args: Arguments for function
        ticker: Optional ticker symbol for context
        **kwargs: Keyword arguments for function
        
    Returns:
        Function result or None if operation failed
    """
    with ErrorContext(operation_name, ticker=ticker):
        try:
            return func(*args, **kwargs)
        except VolumeAnalysisError:
            # Our custom errors - re-raise as-is
            raise
        except Exception as e:
            # Convert unexpected errors to our format
            raise VolumeAnalysisError(f"Unexpected error in {operation_name}: {str(e)}") from e
