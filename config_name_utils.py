"""
Configuration Name Utilities

Helper functions for extracting and formatting configuration names
for use in filenames and reports.

Author: Volume Analysis Tool
Date: 2025-12-08
"""

import os
from typing import Optional


def get_config_name_from_dict(config: dict) -> str:
    """
    Extract config name from a config dictionary.
    
    Args:
        config: Configuration dictionary (loaded from YAML)
        
    Returns:
        str: Config name (e.g., 'conservative', 'aggressive', 'balanced')
    """
    if not config:
        return 'default'
    
    # Try to get config_name from the dict
    config_name = config.get('config_name', '')
    
    if config_name:
        # Clean up config name for filename use
        # Remove spaces, convert to lowercase
        return config_name.lower().replace(' ', '_')
    
    # Fallback: try to infer from other fields
    # This handles cases where config_name wasn't set in YAML
    return 'custom'


def get_config_name_from_path(config_path: str) -> str:
    """
    Extract config name from a config file path.
    
    Args:
        config_path: Path to config file (e.g., 'configs/conservative_config.yaml')
        
    Returns:
        str: Config name (e.g., 'conservative')
    """
    if not config_path:
        return 'default'
    
    # Get filename without extension
    basename = os.path.basename(config_path)
    name_without_ext = os.path.splitext(basename)[0]
    
    # Remove '_config' suffix if present
    if name_without_ext.endswith('_config'):
        name_without_ext = name_without_ext[:-7]  # Remove '_config'
    
    return name_without_ext.lower()


def get_config_name(config_dict: Optional[dict] = None, 
                    config_path: Optional[str] = None) -> str:
    """
    Get config name from either dict or path (with fallback logic).
    
    Tries config dict first, then config path, then returns 'default'.
    
    Args:
        config_dict: Optional configuration dictionary
        config_path: Optional path to config file
        
    Returns:
        str: Config name for use in filenames
    """
    # Try dict first (most reliable)
    if config_dict:
        name = get_config_name_from_dict(config_dict)
        if name != 'custom':  # Only use if we got a real name
            return name
    
    # Try path second
    if config_path:
        return get_config_name_from_path(config_path)
    
    # Fallback
    return 'default'
