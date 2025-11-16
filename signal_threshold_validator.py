"""
Signal Threshold Validator and Comparison Tool

This module provides utilities to:
1. Compare raw signals vs empirically-filtered signals
2. Validate that backtests use correct thresholds
3. Generate comparison reports showing performance differences

Part of fixing the threshold disconnect between batch_summary and risk_managed backtest.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime

from threshold_config import OPTIMAL_THRESHOLDS
import signal_generator


def apply_empirical_thresholds(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply empirically validated thresholds to filter signals.
    
    Creates new columns with '_filtered' suffix that respect optimal thresholds:
    - Moderate_Buy_filtered: Uses score ≥6.5 (not ≥5)
    - Profit_Taking_filtered: Uses score ≥7.0
    - Stealth_Accumulation_filtered: Uses score ≥4.5
    
    Args:
        df: DataFrame with raw signals and score columns
        
    Returns:
        DataFrame with filtered signal columns added
    """
    df = df.copy()
    
    # Get optimal thresholds
    moderate_threshold = OPTIMAL_THRESHOLDS['moderate_buy']['threshold']
    profit_threshold = OPTIMAL_THRESHOLDS['profit_taking']['threshold']
    stealth_threshold = OPTIMAL_THRESHOLDS['stealth_accumulation']['threshold']
    
    # Calculate scores if not already present
    if 'Moderate_Buy_Score' not in df.columns:
        df['Moderate_Buy_Score'] = signal_generator.calculate_moderate_buy_score(df)
    
    if 'Profit_Taking_Score' not in df.columns:
        df['Profit_Taking_Score'] = signal_generator.calculate_profit_taking_score(df)
    
    if 'Stealth_Accumulation_Score' not in df.columns:
        df['Stealth_Accumulation_Score'] = signal_generator.calculate_stealth_accumulation_score(df)
    
    # Apply empirical thresholds with NaN handling
    # Fix for: "Cannot perform 'rand_' with a dtyped [bool] array and scalar of type [bool]"
    df['Moderate_Buy_filtered'] = (
        df['Moderate_Buy'].fillna(False) & 
        (df['Moderate_Buy_Score'] >= moderate_threshold).fillna(False)
    )
    
    df['Profit_Taking_filtered'] = (
        df['Profit_Taking'].fillna(False) & 
        (df['Profit_Taking_Score'] >= profit_threshold).fillna(False)
    )
    
    df['Stealth_Accumulation_filtered'] = (
        df['Stealth_Accumulation'].fillna(False) & 
        (df['Stealth_Accumulation_Score'] >= stealth_threshold).fillna(False)
    )
    
    return df


def compare_signal_counts(df: pd.DataFrame) -> Dict[str, Dict]:
    """
    Compare raw vs filtered signal counts.
    
    Args:
        df: DataFrame with both raw and filtered signals
        
    Returns:
        Dict with comparison metrics for each signal type
    """
    results = {}
    
    signal_pairs = [
        ('Moderate_Buy', 'Moderate_Buy_filtered', 'moderate_buy'),
        ('Profit_Taking', 'Profit_Taking_filtered', 'profit_taking'),
        ('Stealth_Accumulation', 'Stealth_Accumulation_filtered', 'stealth_accumulation')
    ]
    
    for raw_col, filtered_col, config_key in signal_pairs:
        if raw_col not in df.columns or filtered_col not in df.columns:
            continue
        
        raw_count = df[raw_col].sum()
        filtered_count = df[filtered_col].sum()
        reduction_pct = ((raw_count - filtered_count) / raw_count * 100) if raw_count > 0 else 0
        
        threshold = OPTIMAL_THRESHOLDS[config_key]['threshold']
        expected_win_rate = OPTIMAL_THRESHOLDS[config_key]['backtest_results']['win_rate']
        expectancy = OPTIMAL_THRESHOLDS[config_key]['backtest_results']['expectancy']
        
        results[config_key] = {
            'raw_signals': raw_count,
            'filtered_signals': filtered_count,
            'signals_removed': raw_count - filtered_count,
            'reduction_pct': reduction_pct,
            'threshold': threshold,
            'expected_win_rate': expected_win_rate,
            'expected_expectancy': expectancy,
            'config': OPTIMAL_THRESHOLDS[config_key]
        }
    
    return results


def generate_threshold_comparison_report(
    ticker: str,
    df: pd.DataFrame,
    comparison: Dict[str, Dict],
    save_to_file: bool = True,
    output_dir: str = 'backtest_results'
) -> str:
    """
    Generate detailed comparison report showing impact of empirical thresholds.
    
    Args:
        ticker: Stock symbol
        df: DataFrame with signals
        comparison: Results from compare_signal_counts()
        save_to_file: Whether to save report
        output_dir: Output directory
        
    Returns:
        str: Formatted report
    """
    report_lines = []
    
    report_lines.append("=" * 80)
    report_lines.append(f"🔍 SIGNAL THRESHOLD VALIDATION REPORT: {ticker.upper()}")
    report_lines.append("Comparing Raw Signals vs Empirically-Filtered Signals")
    report_lines.append("=" * 80)
    report_lines.append("")
    
    report_lines.append("📊 SIGNAL FILTERING IMPACT:")
    report_lines.append("")
    
    # Moderate Buy
    if 'moderate_buy' in comparison:
        mb = comparison['moderate_buy']
        report_lines.append(f"🟡 MODERATE BUY:")
        report_lines.append(f"   Raw Signals (≥5.0 threshold): {mb['raw_signals']} signals")
        report_lines.append(f"   Filtered Signals (≥{mb['threshold']} threshold): {mb['filtered_signals']} signals")
        report_lines.append(f"   Signals Removed: {mb['signals_removed']} ({mb['reduction_pct']:.1f}% reduction)")
        report_lines.append(f"   Expected Performance at ≥{mb['threshold']}:")
        report_lines.append(f"     • Win Rate: {mb['expected_win_rate']:.1f}%")
        report_lines.append(f"     • Expectancy: {mb['expected_expectancy']:+.2f}%")
        report_lines.append("")
    
    # Profit Taking
    if 'profit_taking' in comparison:
        pt = comparison['profit_taking']
        report_lines.append(f"🟠 PROFIT TAKING:")
        report_lines.append(f"   Raw Signals: {pt['raw_signals']} signals")
        report_lines.append(f"   Filtered Signals (≥{pt['threshold']} threshold): {pt['filtered_signals']} signals")
        report_lines.append(f"   Signals Removed: {pt['signals_removed']} ({pt['reduction_pct']:.1f}% reduction)")
        report_lines.append(f"   Expected Performance at ≥{pt['threshold']}:")
        report_lines.append(f"     • Win Rate: {pt['expected_win_rate']:.1f}%")
        report_lines.append(f"     • Avg Return: {pt['expected_expectancy']:+.2f}%")
        report_lines.append("")
    
    # Stealth Accumulation
    if 'stealth_accumulation' in comparison:
        sa = comparison['stealth_accumulation']
        report_lines.append(f"💎 STEALTH ACCUMULATION:")
        report_lines.append(f"   Raw Signals (≥6.0 threshold): {sa['raw_signals']} signals")
        report_lines.append(f"   Filtered Signals (≥{sa['threshold']} threshold): {sa['filtered_signals']} signals")
        report_lines.append(f"   Signals Removed: {sa['signals_removed']} ({sa['reduction_pct']:.1f}% reduction)")
        report_lines.append(f"   Expected Performance at ≥{sa['threshold']}:")
        report_lines.append(f"     • Win Rate: {sa['expected_win_rate']:.1f}%")
        report_lines.append(f"     • Expectancy: {sa['expected_expectancy']:+.2f}%")
        report_lines.append("")
    
    report_lines.append("=" * 80)
    report_lines.append("")
    report_lines.append("⚠️  CRITICAL FINDINGS:")
    report_lines.append("")
    
    if 'moderate_buy' in comparison:
        mb = comparison['moderate_buy']
        if mb['reduction_pct'] > 30:
            report_lines.append(f"❌ MAJOR DISCONNECT: Moderate Buy signals reduced by {mb['reduction_pct']:.0f}%")
            report_lines.append(f"   • Risk-managed backtest using raw signals (≥5.0) would trade {mb['raw_signals']} times")
            report_lines.append(f"   • Batch summary recommends filtered signals (≥{mb['threshold']}) = {mb['filtered_signals']} times")
            report_lines.append(f"   • Expected win rate at ≥{mb['threshold']}: {mb['expected_win_rate']:.1f}%")
            report_lines.append(f"   • Expected win rate at ≥5.0: UNKNOWN (not validated)")
            report_lines.append("")
    
    report_lines.append("💡 RECOMMENDATIONS:")
    report_lines.append("")
    report_lines.append("1. Use apply_empirical_thresholds() before running risk-managed backtest")
    report_lines.append("2. Trade only *_filtered signals to match empirically validated performance")
    report_lines.append("3. Update signal_generator.py to use configurable thresholds")
    report_lines.append("4. Verify backtest results match expected win rates from threshold_config.py")
    report_lines.append("")
    
    report_lines.append("📝 USAGE:")
    report_lines.append("```python")
    report_lines.append("from signal_threshold_validator import apply_empirical_thresholds")
    report_lines.append("")
    report_lines.append("# Apply empirical thresholds")
    report_lines.append("df = apply_empirical_thresholds(df)")
    report_lines.append("")
    report_lines.append("# Use filtered signals in backtest")
    report_lines.append("entry_signals = ['Moderate_Buy_filtered', 'Stealth_Accumulation_filtered']")
    report_lines.append("exit_signals = ['Profit_Taking_filtered', ...]")
    report_lines.append("```")
    report_lines.append("")
    
    report = "\n".join(report_lines)
    
    if save_to_file:
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{ticker}_threshold_validation_{timestamp}.txt"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w') as f:
            f.write(report)
        
        print(f"\n💾 Threshold validation report saved: {filename}")
    
    return report


def validate_backtest_signals(
    df: pd.DataFrame,
    entry_signals: List[str],
    exit_signals: List[str]
) -> Dict[str, any]:
    """
    Validate that backtest is using empirically-filtered signals.
    
    Args:
        df: DataFrame with signals
        entry_signals: List of entry signal column names used in backtest
        exit_signals: List of exit signal column names used in backtest
        
    Returns:
        Dict with validation results and warnings
    """
    warnings = []
    recommendations = []
    
    # Check if using filtered signals
    uses_filtered_entry = any('_filtered' in sig for sig in entry_signals)
    uses_filtered_exit = any('_filtered' in sig for sig in exit_signals)
    
    if not uses_filtered_entry:
        warnings.append("⚠️ Entry signals do NOT use empirical thresholds (_filtered suffix)")
        warnings.append("   Backtest results may not match expected win rates from threshold_config.py")
        recommendations.append("Use 'Moderate_Buy_filtered' instead of 'Moderate_Buy'")
    
    if not uses_filtered_exit:
        warnings.append("⚠️ Exit signals do NOT use empirical thresholds (_filtered suffix)")
        recommendations.append("Use 'Profit_Taking_filtered' instead of 'Profit_Taking'")
    
    # Check signal counts
    signal_comparison = {}
    for signal in entry_signals + exit_signals:
        if signal in df.columns:
            count = df[signal].sum()
            signal_comparison[signal] = count
    
    return {
        'uses_filtered_entry': uses_filtered_entry,
        'uses_filtered_exit': uses_filtered_exit,
        'warnings': warnings,
        'recommendations': recommendations,
        'signal_counts': signal_comparison,
        'valid': uses_filtered_entry and uses_filtered_exit
    }


if __name__ == "__main__":
    print("Signal Threshold Validator")
    print("=" * 50)
    print()
    print("This module provides utilities to:")
    print("1. Apply empirical thresholds to signals")
    print("2. Compare raw vs filtered signal performance")
    print("3. Validate backtest signal usage")
    print()
    print("Import and use in your analysis:")
    print("  from signal_threshold_validator import apply_empirical_thresholds")
