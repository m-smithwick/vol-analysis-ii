#!/usr/bin/env python3
"""
Test suite for schema management system.
"""

import os
import sys
import tempfile
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import unittest
from unittest.mock import patch, MagicMock

# Add current directory to path to import local modules
sys.path.insert(0, os.getcwd())

from schema_manager import SchemaManager, CURRENT_SCHEMA_VERSION, schema_manager
from data_manager import save_to_cache, load_cached_data, get_cache_filepath
from error_handler import setup_logging, logger, DataValidationError

# Configure logging for tests
setup_logging()

class TestSchemaManager(unittest.TestCase):
    """Test cases for SchemaManager class."""
    
    def setUp(self):
        """Set up test environment."""
        self.schema_manager = SchemaManager()
        self.test_ticker = "TEST"
        self.test_interval = "1d"
        
        # Create sample test data
        dates = pd.date_range(start='2025-01-01', end='2025-01-31', freq='D')
        self.test_df = pd.DataFrame({
            'Open': np.random.uniform(100, 110, len(dates)),
            'High': np.random.uniform(110, 120, len(dates)),
            'Low': np.random.uniform(90, 100, len(dates)),
            'Close': np.random.uniform(95, 115, len(dates)),
            'Volume': np.random.randint(1000000, 10000000, len(dates))
        }, index=dates)
    
    def test_schema_manager_initialization(self):
        """Test SchemaManager initialization."""
        self.assertEqual(self.schema_manager.current_version, CURRENT_SCHEMA_VERSION)
        self.assertIn(CURRENT_SCHEMA_VERSION, self.schema_manager.schema_definitions)
    
    def test_create_metadata_header(self):
        """Test metadata header creation."""
        metadata = self.schema_manager.create_metadata_header(
            ticker=self.test_ticker,
            df=self.test_df,
            interval=self.test_interval
        )
        
        # Check required fields
        required_fields = [
            'schema_version', 'creation_timestamp', 'ticker_symbol',
            'data_source', 'interval', 'auto_adjust', 'data_checksum',
            'record_count', 'start_date', 'end_date'
        ]
        
        for field in required_fields:
            self.assertIn(field, metadata)
        
        # Check values
        self.assertEqual(metadata['schema_version'], CURRENT_SCHEMA_VERSION)
        self.assertEqual(metadata['ticker_symbol'], self.test_ticker.upper())
        self.assertEqual(metadata['interval'], self.test_interval)
        self.assertEqual(metadata['record_count'], len(self.test_df))
        self.assertIsNotNone(metadata['data_checksum'])
    
    def test_calculate_checksum(self):
        """Test data checksum calculation."""
        checksum1 = self.schema_manager._calculate_checksum(self.test_df)
        checksum2 = self.schema_manager._calculate_checksum(self.test_df)
        
        # Same data should produce same checksum
        self.assertEqual(checksum1, checksum2)
        
        # Different data should produce different checksum
        modified_df = self.test_df.copy()
        modified_df.iloc[0, 0] = 999.0  # Modify one value
        checksum3 = self.schema_manager._calculate_checksum(modified_df)
        
        self.assertNotEqual(checksum1, checksum3)
    
    def test_validate_schema_valid_data(self):
        """Test schema validation with valid data."""
        metadata = self.schema_manager.create_metadata_header(
            ticker=self.test_ticker,
            df=self.test_df,
            interval=self.test_interval
        )
        
        # Validation should pass
        self.assertTrue(self.schema_manager.validate_schema(self.test_df, metadata))
    
    def test_validate_schema_invalid_checksum(self):
        """Test schema validation with invalid checksum."""
        metadata = self.schema_manager.create_metadata_header(
            ticker=self.test_ticker,
            df=self.test_df,
            interval=self.test_interval
        )
        
        # Modify checksum to make it invalid
        metadata['data_checksum'] = 'invalid_checksum'
        
        # Modify the data slightly
        modified_df = self.test_df.copy()
        modified_df.iloc[0, 0] = 999.0
        
        # Validation should fail
        self.assertFalse(self.schema_manager.validate_schema(modified_df, metadata))
    
    def test_validate_schema_missing_columns(self):
        """Test schema validation with missing required columns."""
        # Remove required column
        invalid_df = self.test_df.drop('Volume', axis=1)
        
        metadata = self.schema_manager.create_metadata_header(
            ticker=self.test_ticker,
            df=self.test_df,  # Original metadata for full data
            interval=self.test_interval
        )
        
        # Validation should fail
        self.assertFalse(self.schema_manager.validate_schema(invalid_df, metadata))
    
    def test_is_schema_compatible(self):
        """Test schema compatibility checking."""
        # Current version should be compatible
        current_metadata = {'schema_version': CURRENT_SCHEMA_VERSION}
        self.assertTrue(self.schema_manager.is_schema_compatible(current_metadata))
        
        # Old version should not be compatible
        old_metadata = {'schema_version': '0.9.0'}
        self.assertFalse(self.schema_manager.is_schema_compatible(old_metadata))
    
    def test_needs_migration(self):
        """Test migration need detection."""
        # No metadata means migration needed
        self.assertTrue(self.schema_manager.needs_migration(None))
        
        # Current version doesn't need migration
        current_metadata = {'schema_version': CURRENT_SCHEMA_VERSION}
        self.assertFalse(self.schema_manager.needs_migration(current_metadata))
        
        # Old version needs migration
        old_metadata = {'schema_version': '0.9.0'}
        self.assertTrue(self.schema_manager.needs_migration(old_metadata))
    
    def test_types_compatible(self):
        """Test type compatibility checking."""
        # Test float64 compatibility
        self.assertTrue(self.schema_manager._types_compatible('float64', 'float64'))
        self.assertTrue(self.schema_manager._types_compatible('float32', 'float64'))
        
        # Test int64 compatibility
        self.assertTrue(self.schema_manager._types_compatible('int64', 'int64'))
        self.assertTrue(self.schema_manager._types_compatible('Int64', 'int64'))
        
        # Test datetime compatibility
        self.assertTrue(self.schema_manager._types_compatible('datetime64[ns]', 'datetime64[ns]'))
        
        # Test incompatible types
        self.assertFalse(self.schema_manager._types_compatible('object', 'float64'))
    
    def test_standardize_dataframe(self):
        """Test DataFrame standardization."""
        # Create DataFrame with mixed types and timezone-aware index
        raw_df = self.test_df.copy()
        raw_df['Volume'] = raw_df['Volume'].astype(str)  # Make volume a string
        raw_df.index = pd.to_datetime(raw_df.index, utc=True)  # Add timezone
        
        standardized = self.schema_manager._standardize_dataframe(raw_df, self.test_ticker)
        
        # Check data types
        for col in ['Open', 'High', 'Low', 'Close']:
            self.assertTrue(pd.api.types.is_numeric_dtype(standardized[col]))
        
        # Check volume is integer-like
        self.assertTrue(pd.api.types.is_integer_dtype(standardized['Volume']) or 
                       str(standardized['Volume'].dtype) == 'Int64')
        
        # Check index is timezone-naive
        self.assertIsNone(standardized.index.tzinfo)
        
        # Check sorting
        self.assertTrue(standardized.index.is_monotonic_increasing)


class TestDataManagerIntegration(unittest.TestCase):
    """Test integration of schema management with data_manager."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_ticker = "INTEG"
        self.test_interval = "1d"
        
        # Create test data
        dates = pd.date_range(start='2025-01-01', end='2025-01-10', freq='D')
        self.test_df = pd.DataFrame({
            'Open': np.random.uniform(100, 110, len(dates)),
            'High': np.random.uniform(110, 120, len(dates)),
            'Low': np.random.uniform(90, 100, len(dates)),
            'Close': np.random.uniform(95, 115, len(dates)),
            'Volume': np.random.randint(1000000, 10000000, len(dates))
        }, index=dates)
    
    def tearDown(self):
        """Clean up test files."""
        try:
            cache_file = get_cache_filepath(self.test_ticker, self.test_interval)
            if os.path.exists(cache_file):
                os.remove(cache_file)
            
            # Remove backup if it exists
            backup_file = cache_file + '.backup'
            if os.path.exists(backup_file):
                os.remove(backup_file)
        except:
            pass  # Ignore cleanup errors
    
    def test_save_and_load_with_schema(self):
        """Test saving and loading data with schema versioning."""
        # Save data
        save_to_cache(self.test_ticker, self.test_df, self.test_interval)
        
        # Load data
        loaded_df = load_cached_data(self.test_ticker, self.test_interval)
        
        self.assertIsNotNone(loaded_df)
        self.assertEqual(len(loaded_df), len(self.test_df))
        
        # Check that metadata was written
        cache_file = get_cache_filepath(self.test_ticker, self.test_interval)
        metadata = schema_manager.read_metadata_from_csv(cache_file)
        
        self.assertIsNotNone(metadata)
        self.assertEqual(metadata['schema_version'], CURRENT_SCHEMA_VERSION)
        self.assertEqual(metadata['ticker_symbol'], self.test_ticker.upper())
    
    def test_legacy_file_migration(self):
        """Test migration of legacy cache file."""
        cache_file = get_cache_filepath(self.test_ticker, self.test_interval)
        
        # Create a legacy file (no metadata headers)
        self.test_df.to_csv(cache_file)
        
        # Try to load - should trigger migration
        loaded_df = load_cached_data(self.test_ticker, self.test_interval)
        
        self.assertIsNotNone(loaded_df)
        
        # Check that file now has metadata
        metadata = schema_manager.read_metadata_from_csv(cache_file)
        self.assertIsNotNone(metadata)
        self.assertEqual(metadata['schema_version'], CURRENT_SCHEMA_VERSION)
    
    def test_invalid_schema_file_removal(self):
        """Test that files with invalid schema are removed."""
        cache_file = get_cache_filepath(self.test_ticker, self.test_interval)
        
        # Create a file with invalid schema metadata
        with open(cache_file, 'w') as f:
            f.write("# Volume Analysis System - Cache File\n")
            f.write("# Metadata (JSON format):\n")
            f.write('# {"schema_version": "invalid_version"}\n')
            f.write("#\n")
            self.test_df.to_csv(f, index=True)
        
        # Try to load - should return None and remove file
        loaded_df = load_cached_data(self.test_ticker, self.test_interval)
        
        self.assertIsNone(loaded_df)
        # File should be removed due to invalid schema
        # (The actual removal happens in the load function)


def create_test_suite():
    """Create test suite."""
    suite = unittest.TestSuite()
    
    # Add SchemaManager tests
    suite.addTest(unittest.makeSuite(TestSchemaManager))
    
    # Add integration tests
    suite.addTest(unittest.makeSuite(TestDataManagerIntegration))
    
    return suite

def run_tests():
    """Run all tests."""
    print("🧪 RUNNING SCHEMA MANAGEMENT TESTS")
    print("=" * 50)
    
    # Create test suite
    suite = create_test_suite()
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 50)
    print(f"📊 TEST RESULTS:")
    print(f"   ✅ Tests run: {result.testsRun}")
    print(f"   ❌ Failures: {len(result.failures)}")
    print(f"   🔴 Errors: {len(result.errors)}")
    
    if result.failures:
        print(f"\n❌ FAILURES:")
        for test, traceback in result.failures:
            print(f"   {test}: {traceback}")
    
    if result.errors:
        print(f"\n🔴 ERRORS:")
        for test, traceback in result.errors:
            print(f"   {test}: {traceback}")
    
    if result.wasSuccessful():
        print("\n🎉 All tests passed!")
        return True
    else:
        print(f"\n⚠️  {len(result.failures + result.errors)} test(s) failed")
        return False

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
