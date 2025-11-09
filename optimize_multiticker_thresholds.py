"""
Multi-Ticker Threshold Optimization Script

This script optimizes signal thresholds across multiple tickers to find
thresholds that generalize well across different stocks and market conditions.

Usage:
    python optimize_multiticker_thresholds.py ibd.txt -p 24mo
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from datetime import datetime
import vol_analysis
import backtest
from signal_threshold_validator import apply_empirical_thresholds
import argparse


def optimize_signal_across_tickers(
    tickers: List[str],
    signal_col: str,
    score_col: str,
    period: str,
    thresholds: List[float] = None
) -> Dict[float, Dict]:
    """
    Optimize a signal threshold across multiple tickers.
    
    Args:
        tickers: List of ticker symbols
        signal_col: Signal column name (e.g., 'Moderate_Buy')
        score_col: Score column name (e.g., 'Moderate_Buy_Score')
        period: Analysis period
        thresholds: List of thresholds to test
        
    Returns:
        Dict mapping threshold to aggregate performance metrics
    """
    if thresholds is None:
        thresholds = [4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0]
    
    print(f"\n🔍 Optimizing {signal_col} across {len(tickers)} tickers...")
    print(f"   Testing thresholds: {thresholds}")
    print("="*70)
    
    # Store results for each threshold
    threshold_results = {t: {'trades': [], 'tickers_with_trades': 0} for t in thresholds}
    
    # Process each ticker
    for i, ticker in enumerate(tickers, 1):
        print(f"\nProcessing {ticker} ({i}/{len(tickers)})...")
        
        try:
            # Analyze ticker
            df = vol_analysis.analyze_ticker(
                ticker=ticker,
                period=period,
                save_to_file=False,
                save_chart=False,
                force_refresh=False,
                show_chart=False,
                show_summary=False
            )
            
            # Apply empirical thresholds to get filtered signals
            df = apply_empirical_thresholds(df)
            
            # Test each threshold
            for threshold in thresholds:
                # Create filtered signal at this threshold
                df_test = df.copy()
                df_test[f'{signal_col}_test'] = (
                    (df[signal_col] == True) & 
                    (df[score_col] >= threshold)
                )
                
                # Skip if no signals at this threshold
                if df_test[f'{signal_col}_test'].sum() == 0:
                    continue
                
                # Run backtest with this threshold
                exit_signals = ['Profit_Taking', 'Distribution_Warning', 'Sell_Signal',
                               'Momentum_Exhaustion', 'Stop_Loss']
                
                paired_trades = backtest.pair_entry_exit_signals(
                    df_test,
                    [f'{signal_col}_test'],
                    exit_signals
                )
                
                # Filter to closed trades and add ticker info
                closed_trades = [t for t in paired_trades if not t.get('is_open', False)]
                for trade in closed_trades:
                    trade['ticker'] = ticker
                
                if closed_trades:
                    threshold_results[threshold]['trades'].extend(closed_trades)
                    threshold_results[threshold]['tickers_with_trades'] += 1
                    print(f"  Threshold ≥{threshold}: {len(closed_trades)} trades")
            
        except Exception as e:
            print(f"  ⚠️ Error processing {ticker}: {str(e)}")
            continue
    
    # Aggregate results for each threshold
    print(f"\n📊 Aggregating results across all tickers...")
    
    aggregated_results = {}
    
    for threshold in thresholds:
        trades = threshold_results[threshold]['trades']
        tickers_with_trades = threshold_results[threshold]['tickers_with_trades']
        
        if not trades:
            aggregated_results[threshold] = {
                'threshold': threshold,
                'total_trades': 0,
                'win_rate': 0,
                'avg_return': 0,
                'median_return': 0,
                'expectancy': 0,
                'profit_factor': 0,
                'tickers_with_trades': 0
            }
            continue
        
        # Calculate aggregate metrics
        returns = [t['return_pct'] for t in trades]
        wins = [r for r in returns if r > 0]
        losses = [r for r in returns if r <= 0]
        
        win_rate = (len(wins) / len(returns)) * 100
        avg_return = np.mean(returns)
        median_return = np.median(returns)
        avg_win = np.mean(wins) if wins else 0
        avg_loss = np.mean(losses) if losses else 0
        
        expectancy = (win_rate/100 * avg_win) + ((1-win_rate/100) * avg_loss)
        profit_factor = abs(sum(wins) / sum(losses)) if losses and sum(losses) != 0 else float('inf')
        
        aggregated_results[threshold] = {
            'threshold': threshold,
            'total_trades': len(trades),
            'win_rate': win_rate,
            'avg_return': avg_return,
            'median_return': median_return,
            'expectancy': expectancy,
            'profit_factor': profit_factor,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'tickers_with_trades': tickers_with_trades
        }
    
    return aggregated_results


def generate_optimization_report(
    signal_name: str,
    results: Dict[float, Dict],
    ticker_count: int
) -> str:
    """Generate formatted optimization report."""
    
    report_lines = []
    
    report_lines.append("="*80)
    report_lines.append(f"📊 MULTI-TICKER THRESHOLD OPTIMIZATION: {signal_name.upper()}")
    report_lines.append(f"Tested across {ticker_count} tickers")
    report_lines.append("="*80)
    report_lines.append("")
    
    # Table header
    report_lines.append(f"{'Threshold':<12} {'Trades':<8} {'Tickers':<9} {'Win Rate':<11} {'Median':<12} {'Expectancy':<12} {'P.Factor':<10}")
    report_lines.append("-"*80)
    
    # Sort by threshold
    sorted_results = sorted(results.items(), key=lambda x: x[0])
    
    best_threshold = None
    best_score = -999
    
    for threshold, metrics in sorted_results:
        trades = metrics['total_trades']
        tickers = metrics['tickers_with_trades']
        win_rate = metrics['win_rate']
        median_return = metrics['median_return']
        expectancy = metrics['expectancy']
        profit_factor = metrics['profit_factor']
        
        # Format profit factor
        pf_str = f"{profit_factor:.2f}" if profit_factor != float('inf') else "∞"
        
        report_lines.append(
            f"≥{threshold:<11.1f} {trades:<8} {tickers:<9} "
            f"{win_rate:<11.1f}% {median_return:<+12.2f}% {expectancy:<+12.2f}% {pf_str:<10}"
        )
        
        # Calculate score: balance expectancy, win rate, and sample size
        # Require minimum 30 trades across at least 10 tickers
        if trades >= 30 and tickers >= 10:
            # Score combines expectancy and win rate with slight preference for expectancy
            score = expectancy * 0.6 + (win_rate / 10) * 0.4
            
            if score > best_score:
                best_score = score
                best_threshold = threshold
    
    report_lines.append("")
    
    # Recommendation
    if best_threshold is not None:
        best_metrics = results[best_threshold]
        report_lines.append("💡 RECOMMENDED THRESHOLD:")
        report_lines.append(f"  Use threshold ≥{best_threshold:.1f}")
        report_lines.append(f"  • Total Trades: {best_metrics['total_trades']} across {best_metrics['tickers_with_trades']} tickers")
        report_lines.append(f"  • Win Rate: {best_metrics['win_rate']:.1f}%")
        report_lines.append(f"  • Median Return: {best_metrics['median_return']:+.2f}%")
        report_lines.append(f"  • Expectancy: {best_metrics['expectancy']:+.2f}%")
        report_lines.append(f"  • Profit Factor: {best_metrics['profit_factor']:.2f}")
        report_lines.append("")
        
        # Quality assessment
        if best_metrics['expectancy'] > 2.0 and best_metrics['win_rate'] > 55:
            report_lines.append("✅ EXCELLENT - Strong edge across multiple tickers")
        elif best_metrics['expectancy'] > 1.0 and best_metrics['win_rate'] > 50:
            report_lines.append("✅ GOOD - Solid positive edge")
        elif best_metrics['expectancy'] > 0:
            report_lines.append("✓ FAIR - Marginal positive edge")
        else:
            report_lines.append("⚠️ POOR - Negative expectancy")
    else:
        report_lines.append("⚠️ NO RELIABLE THRESHOLD FOUND")
        report_lines.append("  • All thresholds had insufficient sample size (<30 trades or <10 tickers)")
        report_lines.append("  • Consider:")
        report_lines.append("    - Using longer time period")
        report_lines.append("    - Testing lower thresholds")
        report_lines.append("    - Reviewing signal generation logic")
    
    report_lines.append("")
    
    return "\n".join(report_lines)


def main():
    parser = argparse.ArgumentParser(
        description='Optimize signal thresholds across multiple tickers'
    )
    
    parser.add_argument(
        'ticker_file',
        help='Path to file containing ticker symbols'
    )
    
    parser.add_argument(
        '-p', '--period',
        default='12mo',
        help='Analysis period (default: 12mo)'
    )
    
    parser.add_argument(
        '-o', '--output-dir',
        default='backtest_results',
        help='Output directory for reports'
    )
    
    args = parser.parse_args()
    
    # Read tickers
    tickers = vol_analysis.read_ticker_file(args.ticker_file)
    print(f"\n🎯 MULTI-TICKER THRESHOLD OPTIMIZATION")
    print(f"   Tickers: {len(tickers)}")
    print(f"   Period: {args.period}")
    print("="*70)
    
    # Signals to optimize
    signals_to_optimize = [
        ('Moderate_Buy', 'Moderate_Buy_Score', 'Moderate Buy'),
        ('Stealth_Accumulation', 'Stealth_Accumulation_Score', 'Stealth Accumulation'),
        ('Profit_Taking', 'Profit_Taking_Score', 'Profit Taking')
    ]
    
    all_reports = []
    recommendations = {}
    
    for signal_col, score_col, signal_name in signals_to_optimize:
        # Optimize this signal
        results = optimize_signal_across_tickers(
            tickers=tickers,
            signal_col=signal_col,
            score_col=score_col,
            period=args.period
        )
        
        # Generate report
        report = generate_optimization_report(signal_name, results, len(tickers))
        all_reports.append(report)
        print("\n" + report)
        
        # Extract recommendation
        valid_results = {t: m for t, m in results.items() 
                        if m['total_trades'] >= 30 and m['tickers_with_trades'] >= 10}
        
        if valid_results:
            best_threshold = max(valid_results.items(), 
                               key=lambda x: x[1]['expectancy'] * 0.6 + (x[1]['win_rate']/10) * 0.4)
            recommendations[signal_name] = {
                'threshold': best_threshold[0],
                'metrics': best_threshold[1]
            }
    
    # Summary report
    summary_lines = []
    summary_lines.append("\n" + "="*80)
    summary_lines.append("🎯 MULTI-TICKER THRESHOLD RECOMMENDATIONS SUMMARY")
    summary_lines.append("="*80)
    summary_lines.append("")
    summary_lines.append(f"Analysis Period: {args.period}")
    summary_lines.append(f"Tickers Analyzed: {len(tickers)}")
    summary_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    summary_lines.append("")
    
    if recommendations:
        for signal_name, rec in recommendations.items():
            threshold = rec['threshold']
            metrics = rec['metrics']
            summary_lines.append(f"{signal_name}:")
            summary_lines.append(f"  Recommended Threshold: ≥{threshold:.1f}")
            summary_lines.append(f"  Win Rate: {metrics['win_rate']:.1f}%")
            summary_lines.append(f"  Median Return: {metrics['median_return']:+.2f}%")
            summary_lines.append(f"  Expectancy: {metrics['expectancy']:+.2f}%")
            summary_lines.append(f"  Sample: {metrics['total_trades']} trades across {metrics['tickers_with_trades']} tickers")
            summary_lines.append("")
    else:
        summary_lines.append("⚠️ No reliable thresholds found for any signal.")
        summary_lines.append("Consider using longer time period or reviewing signal logic.")
        summary_lines.append("")
    
    summary_lines.append("📝 NEXT STEPS:")
    summary_lines.append("1. Update threshold_config.py with these validated thresholds")
    summary_lines.append("2. Update batch_backtest.py to use filtered signals")
    summary_lines.append("3. Re-run batch backtest to verify improved performance")
    summary_lines.append("")
    
    summary_report = "\n".join(summary_lines)
    print(summary_report)
    
    # Save complete report
    import os
    os.makedirs(args.output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"MULTITICKER_threshold_optimization_{args.period}_{timestamp}.txt"
    filepath = os.path.join(args.output_dir, filename)
    
    with open(filepath, 'w') as f:
        f.write("\n\n".join(all_reports))
        f.write("\n\n" + summary_report)
    
    print(f"✅ Complete optimization report saved: {filename}")
    print(f"📁 Location: {os.path.abspath(filepath)}")


if __name__ == "__main__":
    main()
