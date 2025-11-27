"""
Configuration Loader for Volume Analysis Trading System

Loads and validates YAML configuration files for backtesting.
Provides schema validation, type checking, and clear error messages.

Part of Configuration-Based Testing Framework (Phase 1)
"""

import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
import sys


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""
    pass


class ConfigLoader:
    """
    Load and validate YAML configuration files.
    
    Validates against expected schema and provides helpful error messages
    for configuration issues.
    """
    
    REQUIRED_SECTIONS = [
        'config_name',
        'risk_management',
        'signal_thresholds',
        'regime_filters',
        'profit_management',
        'backtest'
    ]
    
    VALID_STOP_STRATEGIES = {
        'static', 'vol_regime', 'atr_dynamic', 'pct_trail', 'time_decay'
    }
    
    def __init__(self, config_path: str):
        """
        Initialize config loader.
        
        Args:
            config_path: Path to YAML config file
        """
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        
    def load(self) -> Dict[str, Any]:
        """
        Load and validate configuration file.
        
        Returns:
            Validated configuration dictionary
            
        Raises:
            ConfigValidationError: If configuration is invalid
            FileNotFoundError: If config file doesn't exist
        """
        # Check file exists
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        # Load YAML
        try:
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigValidationError(f"Failed to parse YAML: {e}")
        
        # Validate structure
        self._validate_structure()
        self._validate_risk_management()
        self._validate_signal_thresholds()
        self._validate_regime_filters()
        self._validate_profit_management()
        self._validate_backtest()
        
        return self.config
    
    def _validate_structure(self):
        """Validate top-level structure."""
        if not isinstance(self.config, dict):
            raise ConfigValidationError("Config must be a dictionary")
        
        # Check required sections
        missing = [s for s in self.REQUIRED_SECTIONS if s not in self.config]
        if missing:
            raise ConfigValidationError(f"Missing required sections: {missing}")
    
    def _validate_risk_management(self):
        """Validate risk_management section."""
        rm = self.config['risk_management']
        
        # Required fields
        required = ['account_value', 'risk_pct_per_trade', 'stop_strategy', 
                   'time_stop_bars', 'stop_params']
        missing = [f for f in required if f not in rm]
        if missing:
            raise ConfigValidationError(f"risk_management missing fields: {missing}")
        
        # Type validation
        if not isinstance(rm['account_value'], (int, float)):
            raise ConfigValidationError("account_value must be numeric")
        if rm['account_value'] <= 0:
            raise ConfigValidationError("account_value must be positive")
        
        if not isinstance(rm['risk_pct_per_trade'], (int, float)):
            raise ConfigValidationError("risk_pct_per_trade must be numeric")
        if not 0.1 <= rm['risk_pct_per_trade'] <= 5.0:
            raise ConfigValidationError("risk_pct_per_trade must be between 0.1 and 5.0")
        
        # Stop strategy validation
        if rm['stop_strategy'] not in self.VALID_STOP_STRATEGIES:
            raise ConfigValidationError(
                f"Invalid stop_strategy '{rm['stop_strategy']}'. "
                f"Must be one of: {sorted(self.VALID_STOP_STRATEGIES)}"
            )
        
        # Time stop validation
        if not isinstance(rm['time_stop_bars'], int):
            raise ConfigValidationError("time_stop_bars must be an integer")
        
        # Validate stop_params structure
        if not isinstance(rm['stop_params'], dict):
            raise ConfigValidationError("stop_params must be a dictionary")
        
        # Validate each stop strategy has its parameters
        for strategy in self.VALID_STOP_STRATEGIES:
            if strategy not in rm['stop_params']:
                raise ConfigValidationError(f"stop_params missing '{strategy}' section")
    
    def _validate_signal_thresholds(self):
        """Validate signal_thresholds section."""
        st = self.config['signal_thresholds']
        
        # Required fields
        required = ['entry', 'exit', 'enabled_entry_signals', 'enabled_exit_signals']
        missing = [f for f in required if f not in st]
        if missing:
            raise ConfigValidationError(f"signal_thresholds missing fields: {missing}")
        
        # Validate entry thresholds
        if not isinstance(st['entry'], dict):
            raise ConfigValidationError("signal_thresholds.entry must be a dictionary")
        
        for signal, threshold in st['entry'].items():
            if not isinstance(threshold, (int, float)):
                raise ConfigValidationError(f"Entry threshold '{signal}' must be numeric")
            if not 0 <= threshold <= 10:
                raise ConfigValidationError(f"Entry threshold '{signal}' must be between 0 and 10")
        
        # Validate exit thresholds
        if not isinstance(st['exit'], dict):
            raise ConfigValidationError("signal_thresholds.exit must be a dictionary")
        
        for signal, threshold in st['exit'].items():
            if not isinstance(threshold, (int, float)):
                raise ConfigValidationError(f"Exit threshold '{signal}' must be numeric")
            if not 0 <= threshold <= 10:
                raise ConfigValidationError(f"Exit threshold '{signal}' must be between 0 and 10")
        
        # Validate enabled signals are lists
        if not isinstance(st['enabled_entry_signals'], list):
            raise ConfigValidationError("enabled_entry_signals must be a list")
        if not isinstance(st['enabled_exit_signals'], list):
            raise ConfigValidationError("enabled_exit_signals must be a list")
    
    def _validate_regime_filters(self):
        """Validate regime_filters section."""
        rf = self.config['regime_filters']
        
        # Required fields
        required = ['enable_spy_regime', 'enable_sector_regime', 
                   'require_both_regimes', 'sector_mapping_file']
        missing = [f for f in required if f not in rf]
        if missing:
            raise ConfigValidationError(f"regime_filters missing fields: {missing}")
        
        # Type validation
        if not isinstance(rf['enable_spy_regime'], bool):
            raise ConfigValidationError("enable_spy_regime must be boolean")
        if not isinstance(rf['enable_sector_regime'], bool):
            raise ConfigValidationError("enable_sector_regime must be boolean")
        if not isinstance(rf['require_both_regimes'], bool):
            raise ConfigValidationError("require_both_regimes must be boolean")
        if not isinstance(rf['sector_mapping_file'], str):
            raise ConfigValidationError("sector_mapping_file must be a string")
    
    def _validate_profit_management(self):
        """Validate profit_management section."""
        pm = self.config['profit_management']
        
        # Required fields
        required = ['enable_profit_scaling', 'profit_target_r', 'profit_exit_pct',
                   'enable_trailing_stop', 'trail_lookback_bars']
        missing = [f for f in required if f not in pm]
        if missing:
            raise ConfigValidationError(f"profit_management missing fields: {missing}")
        
        # Type validation
        if not isinstance(pm['enable_profit_scaling'], bool):
            raise ConfigValidationError("enable_profit_scaling must be boolean")
        if not isinstance(pm['enable_trailing_stop'], bool):
            raise ConfigValidationError("enable_trailing_stop must be boolean")
        
        if not isinstance(pm['profit_target_r'], (int, float)):
            raise ConfigValidationError("profit_target_r must be numeric")
        if pm['profit_target_r'] <= 0:
            raise ConfigValidationError("profit_target_r must be positive")
        
        if not isinstance(pm['profit_exit_pct'], (int, float)):
            raise ConfigValidationError("profit_exit_pct must be numeric")
        if not 0 < pm['profit_exit_pct'] <= 1.0:
            raise ConfigValidationError("profit_exit_pct must be between 0 and 1.0")
        
        if not isinstance(pm['trail_lookback_bars'], int):
            raise ConfigValidationError("trail_lookback_bars must be an integer")
        if pm['trail_lookback_bars'] <= 0:
            raise ConfigValidationError("trail_lookback_bars must be positive")
    
    def _validate_backtest(self):
        """Validate backtest section."""
        bt = self.config['backtest']
        
        # Required fields
        required = ['start_date', 'end_date', 'lookback_months', 
                   'generate_charts', 'chart_save_dir', 'generate_trade_log']
        missing = [f for f in required if f not in bt]
        if missing:
            raise ConfigValidationError(f"backtest missing fields: {missing}")
        
        # Type validation (dates can be None/null)
        if bt['start_date'] is not None and not isinstance(bt['start_date'], str):
            raise ConfigValidationError("start_date must be a string or null")
        if bt['end_date'] is not None and not isinstance(bt['end_date'], str):
            raise ConfigValidationError("end_date must be a string or null")
        
        if not isinstance(bt['lookback_months'], int):
            raise ConfigValidationError("lookback_months must be an integer")
        if bt['lookback_months'] <= 0:
            raise ConfigValidationError("lookback_months must be positive")
        
        if not isinstance(bt['generate_charts'], bool):
            raise ConfigValidationError("generate_charts must be boolean")
        if not isinstance(bt['generate_trade_log'], bool):
            raise ConfigValidationError("generate_trade_log must be boolean")
        if not isinstance(bt['chart_save_dir'], str):
            raise ConfigValidationError("chart_save_dir must be a string")
    
    def get_risk_manager_params(self) -> Dict[str, Any]:
        """
        Extract parameters for RiskManager initialization.
        
        Returns:
            Dict with account_value, risk_pct_per_trade, stop_strategy, time_stop_bars
        """
        rm = self.config['risk_management']
        return {
            'account_value': rm['account_value'],
            'risk_pct_per_trade': rm['risk_pct_per_trade'],
            'stop_strategy': rm['stop_strategy'],
            'time_stop_bars': rm['time_stop_bars']
        }
    
    def get_stop_params(self) -> Dict[str, Any]:
        """
        Extract stop strategy parameters.
        
        Returns:
            Dict with all stop strategy parameters
        """
        return self.config['risk_management']['stop_params']
    
    def get_signal_config(self) -> Dict[str, Any]:
        """
        Extract signal configuration.
        
        Returns:
            Dict with entry/exit thresholds and enabled signals
        """
        return self.config['signal_thresholds']
    
    def get_regime_config(self) -> Dict[str, Any]:
        """
        Extract regime filter configuration.
        
        Returns:
            Dict with regime filter settings
        """
        return self.config['regime_filters']
    
    def get_backtest_config(self) -> Dict[str, Any]:
        """
        Extract backtest configuration.
        
        Returns:
            Dict with backtest settings
        """
        return self.config['backtest']
    
    def print_summary(self):
        """Print configuration summary for verification."""
        print(f"\n{'='*60}")
        print(f"Configuration: {self.config.get('config_name', 'Unknown')}")
        print(f"Description: {self.config.get('description', 'N/A')}")
        print(f"{'='*60}")
        
        rm = self.config['risk_management']
        print(f"\nRisk Management:")
        print(f"  Account Value: ${rm['account_value']:,}")
        print(f"  Risk per Trade: {rm['risk_pct_per_trade']}%")
        print(f"  Stop Strategy: {rm['stop_strategy']}")
        print(f"  Time Stop: {rm['time_stop_bars']} bars")
        
        st = self.config['signal_thresholds']
        print(f"\nEnabled Entry Signals:")
        for signal in st['enabled_entry_signals']:
            threshold = st['entry'].get(signal, 'N/A')
            print(f"  - {signal}: threshold >= {threshold}")
        
        print(f"\nEnabled Exit Signals:")
        for signal in st['enabled_exit_signals']:
            threshold = st['exit'].get(signal, 'N/A')
            print(f"  - {signal}: threshold >= {threshold}")
        
        rf = self.config['regime_filters']
        print(f"\nRegime Filters:")
        print(f"  SPY Regime: {rf['enable_spy_regime']}")
        print(f"  Sector Regime: {rf['enable_sector_regime']}")
        print(f"  Require Both: {rf['require_both_regimes']}")
        
        print(f"\n{'='*60}\n")


def load_config(config_path: str) -> ConfigLoader:
    """
    Load and validate configuration file.
    
    Convenience function for loading configs.
    
    Args:
        config_path: Path to YAML config file
        
    Returns:
        ConfigLoader instance with loaded config
        
    Raises:
        ConfigValidationError: If configuration is invalid
        FileNotFoundError: If config file doesn't exist
    """
    loader = ConfigLoader(config_path)
    loader.load()
    return loader


if __name__ == '__main__':
    """Test configuration loading."""
    if len(sys.argv) != 2:
        print("Usage: python config_loader.py <config_file.yaml>")
        sys.exit(1)
    
    try:
        loader = load_config(sys.argv[1])
        loader.print_summary()
        print("✅ Configuration is valid!")
    except (ConfigValidationError, FileNotFoundError) as e:
        print(f"❌ Configuration error: {e}")
        sys.exit(1)
