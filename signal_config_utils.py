"""
Signal Configuration Utilities

Maps between configuration signal names and DataFrame column names.
Provides utilities for config-driven signal filtering.
"""

from typing import List, Dict

# Mapping from config signal names to DataFrame column names
CONFIG_TO_DATAFRAME_SIGNAL_MAP = {
    # Entry Signals
    'moderate_buy_pullback': 'Moderate_Buy',
    'stealth_accumulation': 'Stealth_Accumulation',
    'strong_buy': 'Strong_Buy',
    'volume_breakout': 'Volume_Breakout',
    'confluence_signal': 'Confluence_Signal',
    
    # Exit Signals  
    'momentum_exhaustion': 'Momentum_Exhaustion',
    'profit_taking': 'Profit_Taking',
    'distribution_warning': 'Distribution_Warning',
    'sell_signal': 'Sell_Signal',
    'stop_loss': 'Stop_Loss',
    'ma_crossdown': 'MA_Crossdown'
}

# Reverse mapping (DataFrame column names to config names)
DATAFRAME_TO_CONFIG_SIGNAL_MAP = {v: k for k, v in CONFIG_TO_DATAFRAME_SIGNAL_MAP.items()}


def get_dataframe_signal_names(config_signal_names: List[str]) -> List[str]:
    """
    Convert config signal names to DataFrame column names.
    
    Args:
        config_signal_names: List of signal names from config (e.g., ['moderate_buy_pullback'])
        
    Returns:
        List of DataFrame column names (e.g., ['Moderate_Buy'])
        
    Raises:
        ValueError: If config signal name not recognized
        
    Example:
        >>> get_dataframe_signal_names(['moderate_buy_pullback', 'profit_taking'])
        ['Moderate_Buy', 'Profit_Taking']
    """
    df_names = []
    for config_name in config_signal_names:
        if config_name not in CONFIG_TO_DATAFRAME_SIGNAL_MAP:
            raise ValueError(
                f"Unknown signal name in config: '{config_name}'. "
                f"Valid names: {sorted(CONFIG_TO_DATAFRAME_SIGNAL_MAP.keys())}"
            )
        df_names.append(CONFIG_TO_DATAFRAME_SIGNAL_MAP[config_name])
    return df_names


def get_config_signal_name(df_column_name: str) -> str:
    """
    Convert DataFrame column name to config signal name.
    
    Args:
        df_column_name: DataFrame column name (e.g., 'Moderate_Buy')
        
    Returns:
        Config signal name (e.g., 'moderate_buy_pullback')
        
    Raises:
        ValueError: If DataFrame column name not recognized
    """
    if df_column_name not in DATAFRAME_TO_CONFIG_SIGNAL_MAP:
        raise ValueError(
            f"Unknown DataFrame signal column: '{df_column_name}'. "
            f"Valid columns: {sorted(DATAFRAME_TO_CONFIG_SIGNAL_MAP.keys())}"
        )
    return DATAFRAME_TO_CONFIG_SIGNAL_MAP[df_column_name]


def validate_enabled_signals(
    enabled_signals: List[str],
    available_columns: List[str],
    signal_type: str = "entry"
) -> None:
    """
    Validate that enabled signals exist in DataFrame.
    
    Args:
        enabled_signals: List of DataFrame column names from config
        available_columns: List of actual DataFrame columns
        signal_type: 'entry' or 'exit' for error messages
        
    Raises:
        ValueError: If enabled signal not found in DataFrame
    """
    missing = [sig for sig in enabled_signals if sig not in available_columns]
    if missing:
        raise ValueError(
            f"Enabled {signal_type} signals not found in DataFrame: {missing}\n"
            f"Available columns: {sorted(available_columns)}\n"
            f"This likely means the signal generation step failed or "
            f"the signal name mapping is incorrect."
        )


def get_enabled_signals_from_config(config: Dict) -> Dict[str, List[str]]:
    """
    Extract and convert enabled signals from config to DataFrame column names.
    
    Args:
        config: Configuration dictionary (from ConfigLoader)
        
    Returns:
        Dict with 'entry' and 'exit' keys mapping to lists of DataFrame column names
        
    Example:
        >>> config = {'signal_thresholds': {
        ...     'enabled_entry_signals': ['moderate_buy_pullback'],
        ...     'enabled_exit_signals': ['profit_taking', 'momentum_exhaustion']
        ... }}
        >>> get_enabled_signals_from_config(config)
        {'entry': ['Moderate_Buy'], 'exit': ['Profit_Taking', 'Momentum_Exhaustion']}
    """
    st = config.get('signal_thresholds', {})
    
    # Get config signal names
    config_entry_signals = st.get('enabled_entry_signals', [])
    config_exit_signals = st.get('enabled_exit_signals', [])
    
    # Convert to DataFrame column names
    entry_signals = get_dataframe_signal_names(config_entry_signals)
    exit_signals = get_dataframe_signal_names(config_exit_signals)
    
    return {
        'entry': entry_signals,
        'exit': exit_signals
    }


def print_signal_mapping_info():
    """Print signal name mapping for debugging."""
    print("\n" + "="*60)
    print("SIGNAL NAME MAPPING")
    print("="*60)
    
    print("\nEntry Signals:")
    print(f"  {'Config Name':<25} → DataFrame Column")
    print("  " + "-"*50)
    for config_name, df_name in sorted(CONFIG_TO_DATAFRAME_SIGNAL_MAP.items()):
        if config_name in ['moderate_buy_pullback', 'stealth_accumulation', 
                          'strong_buy', 'volume_breakout', 'confluence_signal']:
            print(f"  {config_name:<25} → {df_name}")
    
    print("\nExit Signals:")
    print(f"  {'Config Name':<25} → DataFrame Column")
    print("  " + "-"*50)
    for config_name, df_name in sorted(CONFIG_TO_DATAFRAME_SIGNAL_MAP.items()):
        if config_name in ['momentum_exhaustion', 'profit_taking', 
                          'distribution_warning', 'sell_signal', 'stop_loss', 'ma_crossdown']:
            print(f"  {config_name:<25} → {df_name}")
    
    print("\n" + "="*60 + "\n")


if __name__ == '__main__':
    """Test signal mapping utilities."""
    print_signal_mapping_info()
    
    # Test conversions
    test_config = {
        'signal_thresholds': {
            'enabled_entry_signals': ['moderate_buy_pullback'],
            'enabled_exit_signals': ['profit_taking', 'momentum_exhaustion', 'distribution_warning']
        }
    }
    
    print("Test Config:")
    print(f"  Entry: {test_config['signal_thresholds']['enabled_entry_signals']}")
    print(f"  Exit: {test_config['signal_thresholds']['enabled_exit_signals']}")
    
    result = get_enabled_signals_from_config(test_config)
    print("\nConverted to DataFrame columns:")
    print(f"  Entry: {result['entry']}")
    print(f"  Exit: {result['exit']}")
