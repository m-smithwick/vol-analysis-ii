#!/usr/bin/env python3
"""
Test script for the Week 1 Error Handling Framework implementation.
This tests all key components of the error handling system.
"""

import sys
import os
from pathlib import Path
import tempfile
import pandas as pd

# Add current directory to path for imports
sys.path.insert(0, os.getcwd())

def test_error_handler_imports():
    """Test that all error handling components can be imported correctly."""
    print("Testing error_handler imports...")
    
    try:
        # Test importing the logger directly
        from error_handler import logger
        print("✓ Logger import successful")
        
        # Test importing all key components
        from error_handler import (
            VolumeAnalysisError, DataValidationError, CacheError,
            ErrorContext, validate_ticker, validate_period,
            safe_operation, handle_cache_error
        )
        print("✓ All error handler components imported successfully")
        
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False

def test_validation_functions():
    """Test the validation functions work correctly."""
    print("\nTesting validation functions...")
    
    from error_handler import validate_ticker, validate_period, DataValidationError
    
    # Test valid cases
    try:
        ticker = validate_ticker("AAPL")
        assert ticker == "AAPL", f"Expected 'AAPL', got '{ticker}'"
        print("✓ Valid ticker validation passed")
        
        period = validate_period("12mo")
        assert period == "12mo", f"Expected '12mo', got '{period}'"
        print("✓ Valid period validation passed")
        
    except Exception as e:
        print(f"✗ Valid validation failed: {e}")
        return False
    
    # Test invalid cases
    try:
        validate_ticker("")
        print("✗ Empty ticker should have failed")
        return False
    except DataValidationError:
        print("✓ Empty ticker validation correctly failed")
    
    try:
        validate_period("invalid")
        print("✗ Invalid period should have failed")
        return False
    except DataValidationError:
        print("✓ Invalid period validation correctly failed")
    
    return True

def test_error_context():
    """Test the ErrorContext manager."""
    print("\nTesting ErrorContext manager...")
    
    from error_handler import ErrorContext, VolumeAnalysisError
    
    try:
        # Test successful operation
        with ErrorContext("test operation", ticker="AAPL"):
            pass
        print("✓ ErrorContext successful operation handled correctly")
        
        # Test error operation
        try:
            with ErrorContext("test error", ticker="TEST"):
                raise VolumeAnalysisError("Test error")
        except VolumeAnalysisError:
            print("✓ ErrorContext error handling worked correctly")
        
        return True
    except Exception as e:
        print(f"✗ ErrorContext test failed: {e}")
        return False

def test_module_imports():
    """Test that all updated modules can import the error handler correctly."""
    print("\nTesting module imports...")
    
    modules_to_test = [
        'vol_analysis',
        'data_manager', 
        'batch_backtest'
    ]
    
    for module_name in modules_to_test:
        try:
            module = __import__(module_name)
            print(f"✓ {module_name} imported successfully")
        except Exception as e:
            print(f"✗ {module_name} import failed: {e}")
            return False
    
    return True

def test_basic_functionality():
    """Test basic functionality of key functions with error handling."""
    print("\nTesting basic functionality...")
    
    try:
        # Test vol_analysis functions
        from vol_analysis import read_ticker_file
        
        # Create a temporary ticker file for testing
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("AAPL\nMSFT\nGOOGL\n")
            temp_file = f.name
        
        try:
            tickers = read_ticker_file(temp_file)
            assert len(tickers) == 3, f"Expected 3 tickers, got {len(tickers)}"
            assert "AAPL" in tickers, "AAPL not found in tickers"
            print("✓ read_ticker_file works with error handling")
        finally:
            os.unlink(temp_file)
        
        # Test data_manager functions
        from data_manager import get_cache_directory
        cache_dir = get_cache_directory()
        assert isinstance(cache_dir, Path), "Cache directory should be a Path object"
        print("✓ get_cache_directory works with error handling")
        
        return True
    except Exception as e:
        print(f"✗ Basic functionality test failed: {e}")
        return False

def test_logging():
    """Test that logging is working correctly."""
    print("\nTesting logging functionality...")
    
    try:
        from error_handler import logger, setup_logging
        
        # Test that we can log messages
        logger.info("Test info message")
        logger.warning("Test warning message")
        logger.error("Test error message")
        
        print("✓ Logging functionality works")
        return True
    except Exception as e:
        print(f"✗ Logging test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("WEEK 1 ERROR HANDLING FRAMEWORK TEST")
    print("=" * 60)
    
    tests = [
        test_error_handler_imports,
        test_validation_functions,
        test_error_context,
        test_module_imports,
        test_basic_functionality,
        test_logging
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                print(f"Test {test.__name__} failed")
        except Exception as e:
            print(f"Test {test.__name__} crashed: {e}")
    
    print("\n" + "=" * 60)
    print(f"TEST RESULTS: {passed}/{total} tests passed")
    print("=" * 60)
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Week 1 Error Handling Framework is working correctly.")
        return True
    else:
        print("❌ SOME TESTS FAILED! Please check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
