"""
Schema management module for cache data versioning and validation.
"""

import json
import hashlib
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import csv
import os

# Import error handling framework
from error_handler import (
    ErrorContext, VolumeAnalysisError, DataValidationError, CacheError,
    validate_ticker, validate_dataframe, safe_operation, logger
)

# Current schema version
CURRENT_SCHEMA_VERSION = "1.0.0"

# Schema definitions
SCHEMA_DEFINITIONS = {
    "1.0.0": {
        "required_columns": ["Close", "High", "Low", "Open", "Volume"],
        "column_types": {
            "Close": "float64",
            "High": "float64", 
            "Low": "float64",
            "Open": "float64",
            "Volume": "int64"
        },
        "index_type": "datetime64[ns]",
        "index_name": "Date",
        "metadata_fields": [
            "schema_version",
            "creation_timestamp", 
            "ticker_symbol",
            "data_source",
            "interval",
            "auto_adjust",
            "data_checksum",
            "record_count",
            "start_date",
            "end_date"
        ]
    }
}

class SchemaManager:
    """Manages cache schema versions and validation."""
    
    def __init__(self):
        self.current_version = CURRENT_SCHEMA_VERSION
        self.schema_definitions = SCHEMA_DEFINITIONS
    
    def create_metadata_header(self, ticker: str, df: pd.DataFrame, 
                             interval: str = "1d", auto_adjust: bool = True,
                             data_source: str = "yfinance") -> Dict[str, Any]:
        """
        Create metadata header for cache file.
        
        Args:
            ticker (str): Stock symbol
            df (pd.DataFrame): Data to create metadata for
            interval (str): Data interval
            auto_adjust (bool): Whether auto-adjust was used
            data_source (str): Data source provider
            
        Returns:
            Dict[str, Any]: Metadata dictionary
        """
        with ErrorContext("creating metadata header", ticker=ticker):
            validate_ticker(ticker)
            validate_dataframe(df, self.schema_definitions[self.current_version]["required_columns"])
            
            # Calculate data checksum for integrity verification
            data_checksum = self._calculate_checksum(df)
            
            metadata = {
                "schema_version": self.current_version,
                "creation_timestamp": datetime.now().isoformat(),
                "ticker_symbol": ticker.upper(),
                "data_source": data_source,
                "interval": interval,
                "auto_adjust": auto_adjust,
                "data_checksum": data_checksum,
                "record_count": len(df),
                "start_date": df.index[0].isoformat() if not df.empty else None,
                "end_date": df.index[-1].isoformat() if not df.empty else None
            }
            
            return metadata
    
    def _calculate_checksum(self, df: pd.DataFrame) -> str:
        """Calculate SHA-256 checksum of DataFrame data for integrity verification."""
        with ErrorContext("calculating data checksum"):
            # Create a consistent string representation of the data
            data_str = df.to_csv(index=True, float_format='%.10f')
            return hashlib.sha256(data_str.encode()).hexdigest()[:16]  # First 16 chars
    
    def validate_schema(self, df: pd.DataFrame, metadata: Dict[str, Any]) -> bool:
        """
        Validate DataFrame against schema version.
        
        Args:
            df (pd.DataFrame): DataFrame to validate
            metadata (Dict[str, Any]): Metadata with schema information
            
        Returns:
            bool: True if schema is valid
        """
        with ErrorContext("validating schema"):
            schema_version = metadata.get("schema_version", "unknown")
            
            if schema_version not in self.schema_definitions:
                logger.warning(f"Unknown schema version: {schema_version}")
                return False
            
            schema = self.schema_definitions[schema_version]
            
            # Check required columns
            required_columns = schema["required_columns"]
            missing_columns = set(required_columns) - set(df.columns)
            if missing_columns:
                logger.warning(f"Missing required columns: {missing_columns}")
                return False
            
            # Check column types (basic validation)
            for col, expected_type in schema["column_types"].items():
                if col in df.columns:
                    actual_type = str(df[col].dtype)
                    # Allow some flexibility in type matching
                    if not self._types_compatible(actual_type, expected_type):
                        logger.warning(f"Column {col} has type {actual_type}, expected {expected_type}")
                        return False
            
            # Check index type
            expected_index_type = schema["index_type"]
            actual_index_type = str(df.index.dtype)
            if not self._types_compatible(actual_index_type, expected_index_type):
                logger.warning(f"Index has type {actual_index_type}, expected {expected_index_type}")
                return False
            
            # Validate data integrity with checksum if available
            if "data_checksum" in metadata:
                expected_checksum = metadata["data_checksum"]
                actual_checksum = self._calculate_checksum(df)
                if actual_checksum != expected_checksum:
                    logger.warning(f"Data integrity check failed: checksum mismatch")
                    return False
            
            return True
    
    def _types_compatible(self, actual: str, expected: str) -> bool:
        """Check if data types are compatible."""
        # Handle common type variations
        type_mappings = {
            "float64": ["float64", "float32", "float"],
            "int64": ["int64", "int32", "int", "Int64"],
            "datetime64[ns]": ["datetime64[ns]", "datetime64", "object"]
        }
        
        compatible_types = type_mappings.get(expected, [expected])
        return any(actual.startswith(t) for t in compatible_types)
    
    def is_schema_compatible(self, metadata: Dict[str, Any]) -> bool:
        """
        Check if cached data schema is compatible with current version.
        
        Args:
            metadata (Dict[str, Any]): Metadata from cached file
            
        Returns:
            bool: True if compatible
        """
        with ErrorContext("checking schema compatibility"):
            cached_version = metadata.get("schema_version", "unknown")
            
            # For now, we only support the current version
            # Future versions could implement backward compatibility rules
            return cached_version == self.current_version
    
    def is_valid_schema_version(self, version: str) -> bool:
        """
        Check if schema version is valid (known/supported).
        
        Args:
            version (str): Schema version to check
            
        Returns:
            bool: True if version is valid
        """
        # Consider a version valid if it's in our known schema definitions
        if version in self.schema_definitions:
            return True
        
        # Allow legacy files with no version (represented as None or empty)
        if not version or version == "unknown":
            return True
        
        # Allow semantic version patterns (e.g., "0.9.0", "1.1.0") for potential legacy migration
        import re
        if re.match(r'^\d+\.\d+\.\d+$', version):
            return True
        
        # Reject obviously invalid versions (non-semantic version strings)
        return False
    
    def needs_migration(self, metadata: Optional[Dict[str, Any]]) -> bool:
        """
        Check if cached data needs migration to current schema.
        
        Args:
            metadata (Optional[Dict[str, Any]]): Metadata from cached file
            
        Returns:
            bool: True if migration is needed (and possible)
        """
        if metadata is None:
            return True  # No metadata = legacy file, needs migration
        
        cached_version = metadata.get("schema_version")
        
        # If the version is invalid, don't attempt migration
        if not self.is_valid_schema_version(cached_version):
            return False
        
        return cached_version != self.current_version
    
    def write_metadata_to_csv(self, filepath: str, metadata: Dict[str, Any]) -> None:
        """
        Write metadata as comment lines at the top of CSV file.
        
        Args:
            filepath (str): Path to CSV file
            metadata (Dict[str, Any]): Metadata to write
        """
        with ErrorContext("writing metadata to CSV", filepath=filepath):
            # Read existing CSV data if file exists
            df = None
            if os.path.exists(filepath):
                try:
                    df = pd.read_csv(filepath, index_col=0, parse_dates=True, comment='#')
                except Exception as e:
                    logger.warning(f"Could not read existing CSV data: {e}")
            
            if df is not None:
                # Write file with metadata header
                with open(filepath, 'w', newline='') as f:
                    # Write metadata as comments
                    f.write("# Volume Analysis System - Cache File\n")
                    f.write(f"# Generated: {datetime.now().isoformat()}\n")
                    f.write("# Metadata (JSON format):\n")
                    
                    metadata_json = json.dumps(metadata, indent=2)
                    for line in metadata_json.split('\n'):
                        f.write(f"# {line}\n")
                    f.write("#\n")
                    
                    # Write CSV data
                    df.to_csv(f, index=True)
                    
                logger.info(f"Updated CSV file with metadata: {filepath}")
    
    def read_metadata_from_csv(self, filepath: str) -> Optional[Dict[str, Any]]:
        """
        Read metadata from CSV file header comments.
        
        Args:
            filepath (str): Path to CSV file
            
        Returns:
            Optional[Dict[str, Any]]: Metadata dictionary or None if not found
        """
        with ErrorContext("reading metadata from CSV", filepath=filepath):
            if not os.path.exists(filepath):
                return None
            
            try:
                with open(filepath, 'r') as f:
                    lines = []
                    metadata_started = False
                    
                    for line in f:
                        if line.startswith('# Metadata (JSON format):'):
                            metadata_started = True
                            continue
                        elif line.startswith('#') and metadata_started:
                            if line.strip() == '#':
                                break  # End of metadata
                            # Remove '# ' prefix
                            clean_line = line[2:].rstrip('\n')
                            lines.append(clean_line)
                        elif not line.startswith('#'):
                            break  # Reached CSV data
                    
                    if lines:
                        metadata_json = '\n'.join(lines)
                        metadata = json.loads(metadata_json)
                        logger.debug(f"Read metadata from {filepath}: version {metadata.get('schema_version', 'unknown')}")
                        return metadata
                    else:
                        logger.debug(f"No metadata found in {filepath}")
                        return None
                        
            except Exception as e:
                logger.warning(f"Error reading metadata from {filepath}: {e}")
                return None
    
    def migrate_legacy_file(self, filepath: str, ticker: str, interval: str = "1d") -> bool:
        """
        Migrate legacy cache file to current schema.
        
        Args:
            filepath (str): Path to legacy cache file
            ticker (str): Stock symbol
            interval (str): Data interval
            
        Returns:
            bool: True if migration successful
        """
        with ErrorContext("migrating legacy file", filepath=filepath, ticker=ticker):
            try:
                # Read legacy CSV data
                df = pd.read_csv(filepath, index_col=0, parse_dates=True, comment='#')
                
                if df.empty:
                    logger.warning(f"Legacy file {filepath} is empty - skipping migration")
                    return False
                
                # Validate and standardize data
                df = self._standardize_dataframe(df, ticker)
                
                # Create metadata for migrated file
                metadata = self.create_metadata_header(
                    ticker=ticker,
                    df=df,
                    interval=interval,
                    data_source="yfinance_legacy"
                )
                
                # Create backup of original file
                backup_path = f"{filepath}.backup"
                safe_operation(f"backing up {filepath}", lambda: os.rename(filepath, backup_path))
                
                # Write migrated file with metadata and data
                with open(filepath, 'w', newline='') as f:
                    # Write metadata as comments
                    f.write("# Volume Analysis System - Cache File\n")
                    f.write(f"# Generated: {datetime.now().isoformat()}\n")
                    f.write("# Metadata (JSON format):\n")
                    
                    metadata_json = json.dumps(metadata, indent=2)
                    for line in metadata_json.split('\n'):
                        f.write(f"# {line}\n")
                    f.write("#\n")
                    
                    # Write CSV data
                    df.to_csv(f, index=True)
                
                logger.info(f"Successfully migrated {filepath} to schema version {self.current_version}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to migrate {filepath}: {e}")
                return False
    
    def _standardize_dataframe(self, df: pd.DataFrame, ticker: str) -> pd.DataFrame:
        """Standardize DataFrame structure and data types."""
        with ErrorContext("standardizing dataframe", ticker=ticker):
            # Ensure required columns exist
            required_cols = self.schema_definitions[self.current_version]["required_columns"]
            validate_dataframe(df, required_cols)
            
            missing_cols = set(required_cols) - set(df.columns)
            
            if missing_cols:
                raise DataValidationError(f"Missing required columns for {ticker}: {missing_cols}")
            
            # Standardize data types
            for col in ["Close", "High", "Low", "Open"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            if "Volume" in df.columns:
                df["Volume"] = pd.to_numeric(df["Volume"], errors='coerce').astype('Int64')
            
            # Ensure datetime index
            if not pd.api.types.is_datetime64_any_dtype(df.index):
                df.index = pd.to_datetime(df.index)
            
            # Remove timezone info for consistency
            if df.index.tzinfo is not None:
                df.index = df.index.tz_localize(None)
            
            # Sort by date and remove duplicates
            df.sort_index(inplace=True)
            df = df[~df.index.duplicated(keep='last')]
            
            # Remove rows with all NaN values
            df.dropna(how='all', inplace=True)
            
            return df
    
    def get_schema_info(self, version: str = None) -> Dict[str, Any]:
        """Get schema information for specified version."""
        version = version or self.current_version
        return self.schema_definitions.get(version, {})

# Global schema manager instance
schema_manager = SchemaManager()
