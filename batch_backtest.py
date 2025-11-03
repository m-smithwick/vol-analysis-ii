"""
Batch backtesting module for volume analysis signals.

This module runs backtests across multiple tickers and aggregates results
to determine optimal trading strategies.
"""

import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime
from typing import Dict, List, Tuple
import vol_analysis
import backtest


def run_batch_backtest(ticker_file: str, period: str = '12mo', 
                      output_dir: str = 'backtest_results') -> Dict:
    """
    Run backtests on all tickers in a file and aggregate results.
    
    Args:
        ticker_file (str): Path to file containing ticker symbols
        period (str): Analysis period (default: 12mo)
        output_dir (str): Directory to save backtest reports
        
    Returns:
        Dict: Aggregated backtest results across all tickers
    """
    # Read tickers from file
    tickers = vol_analysis.read_ticker_file(ticker_file)
    
    if not tickers:
        print("❌ No valid tickers found in file.")
        return {}
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\n🚀 BATCH BACKTESTING: {len(tickers)} TICKERS")
    print("="*70)
    print(f"📁 Output directory: {output_dir}")
    print(f"📅 Period: {period}")
    print("="*70)
    
    # Aggregate results storage
    aggregated_results = {
        'tickers_processed': [],
        'tickers_failed': [],
        'entry_signal_stats': {},
        'exit_signal_stats': {},
        'all_paired_trades': [],
        'ticker_specific_results': {}
    }
    
    # Signal definitions
    entry_signals = {
        'Strong_Buy': '🟢 Strong Buy',
        'Moderate_Buy': '🟡 Moderate Buy',
        'Stealth_Accumulation': '💎 Stealth Accumulation',
        'Confluence_Signal': '⭐ Multi-Signal Confluence',
        'Volume_Breakout': '🔥 Volume Breakout'
    }
    
    exit_signals = {
        'Profit_Taking': '🟠 Profit Taking',
        'Distribution_Warning': '⚠️ Distribution Warning',
        'Sell_Signal': '🔴 Sell Signal',
        'Momentum_Exhaustion': '💜 Momentum Exhaustion',
        'Stop_Loss': '🛑 Stop Loss'
    }
    
    # Process each ticker
    for i, ticker in enumerate(tickers, 1):
        print(f"\n[{i}/{len(tickers)}] Processing {ticker}...")
        
        try:
            # Run analysis without chart display
            df = vol_analysis.analyze_ticker(
                ticker=ticker,
                period=period,
                save_to_file=False,
                save_chart=False,
                force_refresh=False,
                show_chart=False,
                show_summary=False
            )
            
            # Generate paired trades for this ticker
            paired_trades = backtest.pair_entry_exit_signals(
                df, 
                list(entry_signals.keys()), 
                list(exit_signals.keys())
            )
            
            # Add ticker identifier to each trade
            for trade in paired_trades:
                trade['ticker'] = ticker
            
            # Aggregate all trades
            aggregated_results['all_paired_trades'].extend(paired_trades)
            
            # Analyze this ticker's performance
            entry_comparison = backtest.compare_entry_strategies(paired_trades, entry_signals)
            exit_comparison = backtest.compare_exit_strategies(paired_trades, exit_signals)
            
            # Store ticker-specific results
            aggregated_results['ticker_specific_results'][ticker] = {
                'total_trades': len(paired_trades),
                'closed_trades': len([t for t in paired_trades if not t.get('is_open', False)]),
                'entry_performance': entry_comparison,
                'exit_performance': exit_comparison
            }
            
            # Generate and save individual backtest report
            strategy_report = backtest.generate_strategy_comparison_report(
                paired_trades, 
                entry_signals, 
                exit_signals
            )
            
            # Save individual report
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{ticker}_{period}_backtest_{timestamp}.txt"
            filepath = os.path.join(output_dir, filename)
            
            with open(filepath, 'w') as f:
                f.write(f"📊 BACKTEST REPORT: {ticker} ({period})\n")
                f.write("="*70 + "\n\n")
                f.write(strategy_report)
            
            aggregated_results['tickers_processed'].append(ticker)
            print(f"✅ {ticker}: Backtest complete ({len(paired_trades)} trades generated)")
            
        except Exception as e:
            print(f"❌ {ticker}: Error - {str(e)}")
            aggregated_results['tickers_failed'].append({
                'ticker': ticker,
                'error': str(e)
            })
            continue
    
    # Aggregate statistics across all tickers
    if aggregated_results['all_paired_trades']:
        print(f"\n📊 Aggregating results across {len(aggregated_results['tickers_processed'])} tickers...")
        
        # Aggregate entry signal performance
        for signal_col, signal_name in entry_signals.items():
            metrics = backtest.analyze_strategy_performance(
                aggregated_results['all_paired_trades'],
                entry_filter=signal_col
            )
            
            if metrics['closed_trades'] > 0:
                aggregated_results['entry_signal_stats'][signal_col] = {
                    'name': signal_name,
                    **metrics
                }
        
        # Aggregate exit signal performance
        for signal_col, signal_name in exit_signals.items():
            metrics = backtest.analyze_strategy_performance(
                aggregated_results['all_paired_trades'],
                exit_filter=signal_col
            )
            
            if metrics['closed_trades'] > 0:
                aggregated_results['exit_signal_stats'][signal_col] = {
                    'name': signal_name,
                    **metrics
                }
    
    return aggregated_results


def generate_aggregate_report(results: Dict, period: str, output_dir: str) -> str:
    """
    Generate comprehensive aggregate backtest report.
    
    Args:
        results (Dict): Aggregated backtest results
        period (str): Analysis period
        output_dir (str): Output directory
        
    Returns:
        str: Formatted aggregate report
    """
    report_lines = []
    
    # Header
    report_lines.append("="*80)
    report_lines.append("🎯 COLLECTIVE STRATEGY OPTIMIZATION REPORT")
    report_lines.append("="*80)
    report_lines.append("")
    report_lines.append(f"Analysis Period: {period}")
    report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("")
    
    # Summary statistics
    report_lines.append("📊 BATCH PROCESSING SUMMARY:")
    report_lines.append(f"  Tickers Analyzed: {len(results['tickers_processed'])}")
    report_lines.append(f"  Tickers Failed: {len(results['tickers_failed'])}")
    report_lines.append(f"  Total Trades Generated: {len(results['all_paired_trades'])}")
    
    closed_trades = [t for t in results['all_paired_trades'] if not t.get('is_open', False)]
    open_trades = len(results['all_paired_trades']) - len(closed_trades)
    
    report_lines.append(f"  Closed Trades: {len(closed_trades)}")
    report_lines.append(f"  Open Positions: {open_trades}")
    report_lines.append("")
    
    if results['tickers_failed']:
        report_lines.append("⚠️  FAILED TICKERS:")
        for failure in results['tickers_failed']:
            report_lines.append(f"  • {failure['ticker']}: {failure['error']}")
        report_lines.append("")
    
    report_lines.append("✅ Successfully Analyzed:")
    report_lines.append(f"  {', '.join(results['tickers_processed'])}")
    report_lines.append("")
    
    if len(closed_trades) == 0:
        report_lines.append("⚠️  No closed trades available for analysis.")
        report_lines.append("   Try a longer time period to generate more signals.")
        return "\n".join(report_lines)
    
    # Aggregate entry strategy analysis
    report_lines.append("="*80)
    report_lines.append("🚀 COLLECTIVE ENTRY STRATEGY ANALYSIS")
    report_lines.append("="*80)
    report_lines.append("")
    
    if results['entry_signal_stats']:
        # Sort by expectancy (most important metric)
        sorted_entries = sorted(
            results['entry_signal_stats'].items(),
            key=lambda x: (x[1]['expectancy'], x[1]['win_rate']),
            reverse=True
        )
        
        report_lines.append("Ranked by Expected Value per Trade:")
        report_lines.append("")
        
        for rank, (signal_col, metrics) in enumerate(sorted_entries, 1):
            report_lines.append(f"{rank}. {metrics['name']}")
            report_lines.append(f"   {'─'*70}")
            report_lines.append(f"   Total Trades: {metrics['total_trades']} ({metrics['closed_trades']} closed, {metrics['open_trades']} open)")
            report_lines.append(f"   Win Rate: {metrics['win_rate']:.1f}% ({metrics['wins']} wins, {metrics['losses']} losses)")
            report_lines.append(f"   Average Return: {metrics['avg_return']:+.2f}%")
            report_lines.append(f"   Median Return: {metrics['median_return']:+.2f}%")
            report_lines.append(f"   Avg Win: {metrics['avg_win']:+.2f}% | Avg Loss: {metrics['avg_loss']:+.2f}%")
            report_lines.append(f"   Best Trade: {metrics['best_trade_date']} ({metrics['best_return']:+.2f}%)")
            report_lines.append(f"   Worst Trade: {metrics['worst_trade_date']} ({metrics['worst_return']:+.2f}%)")
            report_lines.append(f"   Avg Holding: {metrics['avg_holding_days']:.1f} days")
            report_lines.append(f"   Profit Factor: {metrics['profit_factor']:.2f}")
            report_lines.append(f"   Expectancy: {metrics['expectancy']:+.2f}%")
            
            # Quality rating
            if metrics['expectancy'] >= 2.0 and metrics['win_rate'] >= 65:
                rating = "⭐⭐⭐ EXCELLENT - Top tier strategy"
            elif metrics['expectancy'] >= 1.0 and metrics['win_rate'] >= 55:
                rating = "⭐⭐ GOOD - Strong positive edge"
            elif metrics['expectancy'] >= 0.5 and metrics['win_rate'] >= 50:
                rating = "⭐ FAIR - Marginal profitability"
            else:
                rating = "❌ POOR - Avoid this strategy"
            
            report_lines.append(f"   Rating: {rating}")
            report_lines.append("")
    
    # Aggregate exit strategy analysis
    report_lines.append("="*80)
    report_lines.append("🚪 COLLECTIVE EXIT STRATEGY ANALYSIS")
    report_lines.append("="*80)
    report_lines.append("")
    
    if results['exit_signal_stats']:
        # Sort by win rate
        sorted_exits = sorted(
            results['exit_signal_stats'].items(),
            key=lambda x: (x[1]['win_rate'], x[1]['avg_return']),
            reverse=True
        )
        
        report_lines.append("Ranked by Win Rate:")
        report_lines.append("")
        
        for rank, (signal_col, metrics) in enumerate(sorted_exits, 1):
            report_lines.append(f"{rank}. {metrics['name']}")
            report_lines.append(f"   {'─'*70}")
            report_lines.append(f"   Times Used: {metrics['closed_trades']} (across {metrics['total_trades']} total)")
            report_lines.append(f"   Win Rate: {metrics['win_rate']:.1f}% ({metrics['wins']} wins, {metrics['losses']} losses)")
            report_lines.append(f"   Average Return: {metrics['avg_return']:+.2f}%")
            report_lines.append(f"   Median Return: {metrics['median_return']:+.2f}%")
            report_lines.append(f"   Avg Holding: {metrics['avg_holding_days']:.1f} days")
            report_lines.append(f"   Profit Factor: {metrics['profit_factor']:.2f}")
            
            # Exit quality rating
            if metrics['win_rate'] >= 70 and metrics['profit_factor'] >= 2.0:
                rating = "⭐⭐⭐ EXCELLENT - Highly reliable exit"
            elif metrics['win_rate'] >= 60 and metrics['profit_factor'] >= 1.5:
                rating = "⭐⭐ GOOD - Reliable exit timing"
            elif metrics['win_rate'] >= 50:
                rating = "⭐ FAIR - Use with caution"
            else:
                rating = "❌ POOR - Unreliable exit signal"
            
            report_lines.append(f"   Rating: {rating}")
            report_lines.append("")
    
    # Optimal strategy recommendation
    report_lines.append("="*80)
    report_lines.append("💡 OPTIMAL STRATEGY RECOMMENDATION")
    report_lines.append("="*80)
    report_lines.append("")
    
    if results['entry_signal_stats'] and results['exit_signal_stats']:
        # Best entry by expectancy
        best_entry = max(results['entry_signal_stats'].items(),
                        key=lambda x: (x[1]['expectancy'], x[1]['win_rate']))
        
        # Best exit by win rate
        best_exit = max(results['exit_signal_stats'].items(),
                       key=lambda x: (x[1]['win_rate'], x[1]['avg_return']))
        
        report_lines.append("🎯 RECOMMENDED ENTRY SIGNAL:")
        report_lines.append(f"   {best_entry[1]['name']}")
        report_lines.append(f"   • Win Rate: {best_entry[1]['win_rate']:.1f}%")
        report_lines.append(f"   • Expectancy: {best_entry[1]['expectancy']:+.2f}% per trade")
        report_lines.append(f"   • Average Return: {best_entry[1]['avg_return']:+.2f}%")
        report_lines.append(f"   • Profit Factor: {best_entry[1]['profit_factor']:.2f}")
        report_lines.append(f"   • Based on {best_entry[1]['closed_trades']} closed trades")
        report_lines.append("")
        
        report_lines.append("🎯 RECOMMENDED EXIT SIGNAL:")
        report_lines.append(f"   {best_exit[1]['name']}")
        report_lines.append(f"   • Win Rate: {best_exit[1]['win_rate']:.1f}%")
        report_lines.append(f"   • Average Return: {best_exit[1]['avg_return']:+.2f}%")
        report_lines.append(f"   • Profit Factor: {best_exit[1]['profit_factor']:.2f}")
        report_lines.append(f"   • Based on {best_exit[1]['closed_trades']} closed trades")
        report_lines.append("")
        
        # Test combined strategy
        combined_metrics = backtest.analyze_strategy_performance(
            results['all_paired_trades'],
            entry_filter=best_entry[0],
            exit_filter=best_exit[0]
        )
        
        report_lines.append("📊 COMBINED STRATEGY PERFORMANCE:")
        if combined_metrics['closed_trades'] > 0:
            report_lines.append(f"   Trades: {combined_metrics['closed_trades']} closed")
            report_lines.append(f"   Win Rate: {combined_metrics['win_rate']:.1f}%")
            report_lines.append(f"   Average Return: {combined_metrics['avg_return']:+.2f}%")
            report_lines.append(f"   Expectancy: {combined_metrics['expectancy']:+.2f}%")
            report_lines.append(f"   Profit Factor: {combined_metrics['profit_factor']:.2f}")
            report_lines.append(f"   Avg Holding: {combined_metrics['avg_holding_days']:.1f} days")
            
            if combined_metrics['expectancy'] >= 2.0 and combined_metrics['win_rate'] >= 65:
                report_lines.append(f"   ⭐⭐⭐ EXCEPTIONAL combined performance!")
            elif combined_metrics['expectancy'] >= 1.0 and combined_metrics['win_rate'] >= 55:
                report_lines.append(f"   ⭐⭐ STRONG combined performance")
            else:
                report_lines.append(f"   ⭐ Moderate combined performance")
        else:
            report_lines.append(f"   ⚠️  No closed trades with this exact combination")
            report_lines.append(f"   Consider using signals independently")
        
        report_lines.append("")
    
    # Per-ticker breakdown
    report_lines.append("="*80)
    report_lines.append("📋 PER-TICKER PERFORMANCE BREAKDOWN")
    report_lines.append("="*80)
    report_lines.append("")
    
    for ticker in sorted(results['ticker_specific_results'].keys()):
        ticker_data = results['ticker_specific_results'][ticker]
        report_lines.append(f"  {ticker}:")
        report_lines.append(f"    Total Trades: {ticker_data['total_trades']} ({ticker_data['closed_trades']} closed)")
        
        # Show best entry for this ticker
        if ticker_data['entry_performance']:
            best_ticker_entry = max(ticker_data['entry_performance'].items(),
                                   key=lambda x: x[1]['expectancy'])
            report_lines.append(f"    Best Entry: {best_ticker_entry[1]['name']} (Exp: {best_ticker_entry[1]['expectancy']:+.2f}%)")
        
        # Show best exit for this ticker
        if ticker_data['exit_performance']:
            best_ticker_exit = max(ticker_data['exit_performance'].items(),
                                  key=lambda x: x[1]['win_rate'])
            report_lines.append(f"    Best Exit: {best_ticker_exit[1]['name']} (WR: {best_ticker_exit[1]['win_rate']:.1f}%)")
        
        report_lines.append("")
    
    # Statistical significance note
    report_lines.append("="*80)
    report_lines.append("📈 STATISTICAL SIGNIFICANCE")
    report_lines.append("="*80)
    report_lines.append("")
    report_lines.append(f"  Total Sample Size: {len(closed_trades)} closed trades")
    
    if len(closed_trades) >= 100:
        report_lines.append(f"  ✅ Large sample - results are statistically robust")
    elif len(closed_trades) >= 50:
        report_lines.append(f"  ✓ Moderate sample - results are reasonably reliable")
    elif len(closed_trades) >= 20:
        report_lines.append(f"  ⚠️  Small sample - use caution, may not be representative")
    else:
        report_lines.append(f"  ❌ Very small sample - results may not be reliable")
        report_lines.append(f"     Consider longer time period for more data")
    
    report_lines.append("")
    
    # Key insights
    report_lines.append("="*80)
    report_lines.append("💡 KEY INSIGHTS & RECOMMENDATIONS")
    report_lines.append("="*80)
    report_lines.append("")
    
    if results['entry_signal_stats']:
        # Find most consistent entry
        consistent_entries = [(k, v) for k, v in results['entry_signal_stats'].items()
                             if v['closed_trades'] >= 5]
        if consistent_entries:
            most_consistent = max(consistent_entries, key=lambda x: x[1]['win_rate'])
            report_lines.append(f"✓ Most Consistent Entry: {most_consistent[1]['name']}")
            report_lines.append(f"  ({most_consistent[1]['win_rate']:.1f}% win rate over {most_consistent[1]['closed_trades']} trades)")
            report_lines.append("")
        
        # Find highest expectancy
        if sorted_entries:
            highest_exp = sorted_entries[0]
            report_lines.append(f"✓ Highest Expected Value: {highest_exp[1]['name']}")
            report_lines.append(f"  (Expectancy: {highest_exp[1]['expectancy']:+.2f}% per trade)")
            report_lines.append("")
    
    if results['exit_signal_stats']:
        # Find safest exit
        if sorted_exits:
            safest = sorted_exits[0]
            report_lines.append(f"✓ Most Reliable Exit: {safest[1]['name']}")
            report_lines.append(f"  ({safest[1]['win_rate']:.1f}% win rate)")
            report_lines.append("")
    
    report_lines.append("📝 TRADING RECOMMENDATIONS:")
    report_lines.append("")
    report_lines.append("  1. ENTRY STRATEGY:")
    if results['entry_signal_stats']:
        top_3_entries = sorted_entries[:3]
        for i, (_, metrics) in enumerate(top_3_entries, 1):
            report_lines.append(f"     {i}. {metrics['name']} (Exp: {metrics['expectancy']:+.2f}%, WR: {metrics['win_rate']:.1f}%)")
    
    report_lines.append("")
    report_lines.append("  2. EXIT STRATEGY:")
    if results['exit_signal_stats']:
        top_3_exits = sorted_exits[:3]
        for i, (_, metrics) in enumerate(top_3_exits, 1):
            report_lines.append(f"     {i}. {metrics['name']} (WR: {metrics['win_rate']:.1f}%, Ret: {metrics['avg_return']:+.2f}%)")
    
    report_lines.append("")
    report_lines.append("  3. POSITION SIZING:")
    report_lines.append("     • Increase size on highest expectancy signals")
    report_lines.append("     • Reduce size on lower win rate signals")
    report_lines.append("     • Never risk more than 2% of capital per trade")
    report_lines.append("")
    
    report_lines.append("  4. RISK MANAGEMENT:")
    report_lines.append("     • Set stop losses at support levels")
    report_lines.append("     • Take partial profits on profit-taking signals")
    report_lines.append("     • Act immediately on stop loss triggers")
    report_lines.append("")
    
    report_lines.append("="*80)
    report_lines.append("⚠️  DISCLAIMER")
    report_lines.append("="*80)
    report_lines.append("")
    report_lines.append("This analysis is based on historical data and does not guarantee future")
    report_lines.append("performance. Past results are not indicative of future returns. Always")
    report_lines.append("perform your own due diligence and consider your risk tolerance before trading.")
    report_lines.append("")
    report_lines.append("="*80)
    
    return "\n".join(report_lines)


def main():
    """
    Main function for batch backtesting.
    """
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Run batch backtesting across multiple tickers'
    )
    
    parser.add_argument(
        'ticker_file',
        help='Path to file containing ticker symbols (one per line)'
    )
    
    parser.add_argument(
        '-p', '--period',
        default='12mo',
        help='Analysis period (default: 12mo)'
    )
    
    parser.add_argument(
        '-o', '--output-dir',
        default='backtest_results',
        help='Output directory for backtest reports (default: backtest_results)'
    )
    
    args = parser.parse_args()
    
    # Run batch backtest
    results = run_batch_backtest(
        ticker_file=args.ticker_file,
        period=args.period,
        output_dir=args.output_dir
    )
    
    if not results or not results['all_paired_trades']:
        print("\n❌ No results generated. Check for errors above.")
        sys.exit(1)
    
    # Generate aggregate report
    print(f"\n📊 Generating aggregate optimization report...")
    aggregate_report = generate_aggregate_report(results, args.period, args.output_dir)
    
    # Save aggregate report
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    agg_filename = f"AGGREGATE_optimization_{args.period}_{timestamp}.txt"
    agg_filepath = os.path.join(args.output_dir, agg_filename)
    
    with open(agg_filepath, 'w') as f:
        f.write(aggregate_report)
    
    print(f"\n✅ Aggregate report saved: {agg_filepath}")
    
    # Print report to console
    print("\n" + aggregate_report)
    
    print(f"\n✅ Batch backtesting complete!")
    print(f"📁 All reports saved to: {os.path.abspath(args.output_dir)}")


if __name__ == "__main__":
    main()
