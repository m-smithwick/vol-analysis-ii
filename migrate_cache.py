#!/usr/bin/env python3
"""
Cache Migration Utility for Volume Analysis System

This script migrates existing cache files to the new schema versioning format.
Run this after implementing the schema management system to upgrade all existing cache files.
"""

import os
import sys
from pathlib import Path
from typing import List, Tuple
import pandas as pd

# Add current directory to path to import local modules
sys.path.insert(0, os.getcwd())

from data_manager import get_cache_directory, get_cache_filepath
from schema_manager import schema_manager
from error_handler import ErrorContext, setup_logging, logger

# Configure logging
setup_logging()

def find_cache_files() -> List[Tuple[str, str, str]]:
    """
    Find all cache files that need migration.
    
    Returns:
        List[Tuple[str, str, str]]: List of (ticker, interval, filepath) tuples
    """
    cache_dir = get_cache_directory()
    cache_files = []
    
    if not os.path.exists(cache_dir):
        logger.info("No cache directory found - nothing to migrate")
        return cache_files
    
    for filename in os.listdir(cache_dir):
        if filename.endswith('_data.csv') and not filename.endswith('.backup'):
            # Parse filename to extract ticker and interval
            parts = filename.replace('_data.csv', '').split('_')
            if len(parts) >= 2:
                ticker = parts[0]
                interval = '_'.join(parts[1:])  # Handle multi-part intervals like '1h'
                filepath = os.path.join(cache_dir, filename)
                cache_files.append((ticker, interval, filepath))
    
    return cache_files

def check_migration_status(filepath: str) -> Tuple[bool, str]:
    """
    Check if a file needs migration.
    
    Args:
        filepath (str): Path to cache file
        
    Returns:
        Tuple[bool, str]: (needs_migration, status_message)
    """
    try:
        metadata = schema_manager.read_metadata_from_csv(filepath)
        
        if metadata is None:
            return True, "No metadata (legacy file)"
        elif schema_manager.needs_migration(metadata):
            version = metadata.get('schema_version', 'unknown')
            return True, f"Outdated schema version: {version}"
        else:
            version = metadata.get('schema_version', 'current')
            return False, f"Already current (v{version})"
            
    except Exception as e:
        return True, f"Error reading file: {str(e)}"

def migrate_cache_files(dry_run: bool = False) -> None:
    """
    Migrate all cache files to current schema version.
    
    Args:
        dry_run (bool): If True, only show what would be migrated without making changes
    """
    print("🔄 CACHE MIGRATION UTILITY")
    print("=" * 50)
    
    cache_files = find_cache_files()
    
    if not cache_files:
        print("ℹ️  No cache files found to migrate")
        return
    
    print(f"📁 Found {len(cache_files)} cache files")
    print(f"📋 Current schema version: {schema_manager.current_version}")
    
    if dry_run:
        print("🔍 DRY RUN MODE - No files will be modified")
    
    print("\n" + "=" * 80)
    
    # Analyze migration needs
    needs_migration = []
    already_current = []
    errors = []
    
    for ticker, interval, filepath in cache_files:
        needs_mig, status = check_migration_status(filepath)
        
        if "Error" in status:
            errors.append((ticker, interval, filepath, status))
        elif needs_mig:
            needs_migration.append((ticker, interval, filepath, status))
        else:
            already_current.append((ticker, interval, filepath, status))
    
    # Print summary
    print(f"\n📊 MIGRATION SUMMARY:")
    print(f"   🟢 Already current: {len(already_current)} files")
    print(f"   🟡 Needs migration: {len(needs_migration)} files")
    print(f"   🔴 Errors found: {len(errors)} files")
    
    # Show files that need migration
    if needs_migration:
        print(f"\n🟡 FILES NEEDING MIGRATION ({len(needs_migration)}):")
        for ticker, interval, filepath, status in needs_migration:
            print(f"   {ticker:6s} ({interval:4s}): {status}")
    
    # Show files with errors
    if errors:
        print(f"\n🔴 FILES WITH ERRORS ({len(errors)}):")
        for ticker, interval, filepath, status in errors:
            print(f"   {ticker:6s} ({interval:4s}): {status}")
    
    # Show files already current
    if already_current:
        print(f"\n🟢 FILES ALREADY CURRENT ({len(already_current)}):")
        for ticker, interval, filepath, status in already_current[:10]:  # Show first 10
            print(f"   {ticker:6s} ({interval:4s}): {status}")
        
        if len(already_current) > 10:
            print(f"   ... and {len(already_current) - 10} more files")
    
    # Perform migrations if not dry run
    if not dry_run and needs_migration:
        print(f"\n🚀 STARTING MIGRATION of {len(needs_migration)} files...")
        print("=" * 50)
        
        successful_migrations = 0
        failed_migrations = 0
        
        for i, (ticker, interval, filepath, status) in enumerate(needs_migration, 1):
            print(f"\n[{i:2d}/{len(needs_migration)}] Migrating {ticker} ({interval})...")
            
            try:
                with ErrorContext("migrating cache file", ticker=ticker, interval=interval):
                    if schema_manager.migrate_legacy_file(filepath, ticker, interval):
                        print(f"   ✅ Successfully migrated {ticker} ({interval})")
                        successful_migrations += 1
                    else:
                        print(f"   ❌ Migration failed for {ticker} ({interval})")
                        failed_migrations += 1
                        
            except Exception as e:
                print(f"   ❌ Error migrating {ticker} ({interval}): {str(e)}")
                failed_migrations += 1
        
        # Migration summary
        print(f"\n📈 MIGRATION RESULTS:")
        print(f"   ✅ Successful: {successful_migrations} files")
        print(f"   ❌ Failed: {failed_migrations} files")
        
        if successful_migrations > 0:
            print(f"\n🎉 Migration completed! {successful_migrations} files upgraded to schema v{schema_manager.current_version}")
        
        if failed_migrations > 0:
            print(f"\n⚠️  {failed_migrations} files failed to migrate. Check logs for details.")
            print("   Failed files will be automatically redownloaded when accessed.")
    
    elif dry_run and needs_migration:
        print(f"\n🔍 DRY RUN COMPLETE - Would migrate {len(needs_migration)} files")
        print("   Run without --dry-run flag to perform actual migration")
    
    print("\n" + "=" * 50)
    print("✨ Cache migration utility completed")

def validate_migrated_files() -> None:
    """Validate that migrated files have correct schema."""
    print("🔍 VALIDATING MIGRATED FILES")
    print("=" * 40)
    
    cache_files = find_cache_files()
    
    if not cache_files:
        print("ℹ️  No cache files found to validate")
        return
    
    valid_files = 0
    invalid_files = 0
    
    for ticker, interval, filepath in cache_files:
        try:
            # Read metadata
            metadata = schema_manager.read_metadata_from_csv(filepath)
            
            # Read data
            df = pd.read_csv(filepath, index_col=0, parse_dates=True, comment='#')
            
            # Validate schema
            if metadata and schema_manager.validate_schema(df, metadata):
                valid_files += 1
                print(f"   ✅ {ticker:6s} ({interval:4s}): Valid schema v{metadata.get('schema_version', 'unknown')}")
            else:
                invalid_files += 1
                print(f"   ❌ {ticker:6s} ({interval:4s}): Invalid schema")
                
        except Exception as e:
            invalid_files += 1
            print(f"   ❌ {ticker:6s} ({interval:4s}): Validation error - {str(e)}")
    
    print(f"\n📊 VALIDATION RESULTS:")
    print(f"   ✅ Valid files: {valid_files}")
    print(f"   ❌ Invalid files: {invalid_files}")
    
    if invalid_files == 0:
        print("\n🎉 All files passed validation!")
    else:
        print(f"\n⚠️  {invalid_files} files failed validation")

def main():
    """Main entry point for the migration utility."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate cache files to new schema version')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show what would be migrated without making changes')
    parser.add_argument('--validate', action='store_true',
                       help='Validate migrated files have correct schema')
    parser.add_argument('--force', action='store_true',
                       help='Force migration even if files appear current')
    
    args = parser.parse_args()
    
    try:
        if args.validate:
            validate_migrated_files()
        else:
            migrate_cache_files(dry_run=args.dry_run)
            
    except KeyboardInterrupt:
        print("\n⚠️  Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Migration failed with error: {str(e)}")
        logger.error(f"Migration utility error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
