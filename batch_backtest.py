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
import backtest

# Import error handling framework
from error_handler import (
    ErrorContext, VolumeAnalysisError, DataValidationError, FileOperationError,
    validate_ticker, validate_file_path, safe_operation, 
    setup_logging, logger
)

# Import empirical threshold filtering
from signal_threshold_validator import apply_empirical_thresholds
from analysis_service import prepare_analysis_dataframe
from data_manager import read_ticker_file

# Configure logging for this module
setup_logging()


def run_batch_backtest(ticker_file: str, period: str = '12mo',
                      start_date: str = None, end_date: str = None,
                      output_dir: str = 'backtest_results',
                      risk_managed: bool = False,
                      account_value: float = 100000,
                      risk_pct: float = 0.75,
                      stop_strategy: str = 'time_decay') -> Dict:
    """
    Run backtests on all tickers in a file and aggregate results.
    
    Args:
        ticker_file (str): Path to file containing ticker symbols
        period (str): Analysis period (default: 12mo) - ignored if start_date/end_date provided
        start_date (str): Start date for analysis (YYYY-MM-DD format, optional)
        end_date (str): End date for analysis (YYYY-MM-DD format, optional)
        output_dir (str): Directory to save backtest reports
        risk_managed (bool): Use RiskManager for P&L-aware exits (default: False)
        account_value (float): Account value for position sizing (risk-managed only)
        risk_pct (float): Risk percentage per trade (risk-managed only)
        stop_strategy (str): Stop strategy when using risk-managed mode
        
    Returns:
        Dict: Aggregated backtest results across all tickers
    """
    with ErrorContext("batch backtesting", ticker_file=ticker_file, period=period, output_dir=output_dir):
        # Validate inputs
        validate_file_path(ticker_file, check_exists=True, check_readable=True)
        
        # Read tickers from file
        tickers = read_ticker_file(ticker_file)
        
        if not tickers:
            raise DataValidationError("No valid tickers found in file")
        
        # Create output directory safely
        def _create_output_dir():
            os.makedirs(output_dir, exist_ok=True)
            
        safe_operation(f"creating output directory {output_dir}", _create_output_dir)
        
        # Determine analysis period display
        if start_date and end_date:
            period_display = f"{start_date} to {end_date}"
            logger.info(f"Starting batch backtesting: {len(tickers)} tickers, date range: {period_display}")
        else:
            period_display = period
            logger.info(f"Starting batch backtesting: {len(tickers)} tickers, period: {period}")
        
        logger.info(f"Output directory: {output_dir}")
        
        # Aggregate results storage
        aggregated_results = {
            'tickers_processed': [],
            'tickers_failed': [],
            'entry_signal_stats': {},
            'exit_signal_stats': {},
            'all_paired_trades': [],
            'ticker_specific_results': {},
            'account_value': account_value
        }
        
        # Signal definitions - Using MULTI-TICKER VALIDATED filtered signals
        # Thresholds validated on 24 tickers, 24-month period (Nov 2025)
        entry_signals = {
            'Strong_Buy': '🟢 Strong Buy',
            'Moderate_Buy_filtered': '🟡 Moderate Buy Pullback (≥6.0)',  # Redesigned pullback strategy
            'Stealth_Accumulation_filtered': '💎 Stealth Accumulation (≥4.0)',  # Multi-ticker validated
            'Confluence_Signal': '⭐ Multi-Signal Confluence',
            'Volume_Breakout': '🔥 Volume Breakout'
        }
        
        exit_signals = {
            'Profit_Taking': '🟠 Profit Taking',  # Exit signal - no filtering needed
            'Distribution_Warning': '⚠️ Distribution Warning',
            'Sell_Signal': '🔴 Sell Signal',
            'Momentum_Exhaustion': '💜 Momentum Exhaustion',
            'Stop_Loss': '🛑 Stop Loss'
        }
        
        # Process each ticker
        for i, ticker in enumerate(tickers, 1):
            logger.info(f"Processing {ticker} ({i}/{len(tickers)})")
            
            with ErrorContext("processing ticker", ticker=ticker):
                try:
                    validate_ticker(ticker)
                    
                    df = prepare_analysis_dataframe(
                        ticker=ticker,
                        period=period,
                        data_source='yfinance',
                        force_refresh=False,
                        verbose=False
                    )
                    
                    # Filter to requested date range if specified
                    if start_date and end_date:
                        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                        
                        # Filter dataframe to date range
                        mask = (df.index >= start_dt) & (df.index <= end_dt)
                        df = df[mask].copy()
                        logger.info(f"Filtered {ticker} to date range {start_date} to {end_date}: {len(df)} periods")
                    
                    # Apply empirical thresholds to filter signals
                    # This ensures we use validated thresholds (e.g., Moderate Buy ≥6.5 instead of ≥5.0)
                    df = apply_empirical_thresholds(df)
                    logger.info(f"Applied empirical thresholds for {ticker}")
                    
                    if risk_managed:
                        # Use RiskManager for position management and exits
                        risk_result = backtest.run_risk_managed_backtest(
                            df=df,
                            ticker=ticker,
                            account_value=account_value,
                            risk_pct=risk_pct,
                            stop_strategy=stop_strategy,
                            save_to_file=True,
                            output_dir=output_dir
                        )
                        
                        # Extract trades from risk manager
                        paired_trades = risk_result['trades']
                        
                        # Add ticker identifier if not already present
                        for trade in paired_trades:
                            if 'ticker' not in trade:
                                trade['ticker'] = ticker
                        
                        # Aggregate all trades
                        aggregated_results['all_paired_trades'].extend(paired_trades)
                        
                        # Store ticker-specific results
                        aggregated_results['ticker_specific_results'][ticker] = {
                            'total_trades': len(paired_trades),
                            'closed_trades': len([t for t in paired_trades if not t.get('partial_exit', False)]),
                            'risk_managed': True,
                            'analysis': risk_result.get('analysis', {})
                        }
                    else:
                        # Traditional entry/exit signal pairing
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
                            'risk_managed': False,
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
                        
                        def _save_report():
                            with open(filepath, 'w') as f:
                                f.write(f"📊 BACKTEST REPORT: {ticker} ({period})\n")
                                f.write("="*70 + "\n\n")
                                f.write(strategy_report)
                        
                        safe_operation(f"saving backtest report for {ticker}", _save_report)
                    
                    aggregated_results['tickers_processed'].append(ticker)
                    logger.info(f"Completed {ticker}: {len(paired_trades)} trades generated")
                    
                except Exception as e:
                    logger.error(f"Failed to process {ticker}: {str(e)}")
                    aggregated_results['tickers_failed'].append({
                        'ticker': ticker,
                        'error': str(e)
                    })
                    continue
    
        # Aggregate statistics across all tickers
        if aggregated_results['all_paired_trades']:
            logger.info(f"Aggregating results across {len(aggregated_results['tickers_processed'])} tickers")
            
            if not risk_managed:
                # Traditional backtest: Aggregate entry and exit signal performance
                standard_trades = [
                    t for t in aggregated_results['all_paired_trades']
                    if 'entry_signals' in t and 'exit_signals' in t
                ]
                
                if not standard_trades:
                    logger.warning("No standard trades with entry/exit signals available for aggregate analysis.")
                else:
                    for signal_col, signal_name in entry_signals.items():
                        metrics = backtest.analyze_strategy_performance(
                            standard_trades,
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
                            standard_trades,
                            exit_filter=signal_col
                        )
                        
                        if metrics['closed_trades'] > 0:
                            aggregated_results['exit_signal_stats'][signal_col] = {
                                'name': signal_name,
                                **metrics
                            }
            else:
                # Risk-managed: Aggregate R-multiples and exit types
                try:
                    from risk_manager import analyze_risk_managed_trades
                    
                    # Analyze all trades together
                    all_trades_analysis = analyze_risk_managed_trades(aggregated_results['all_paired_trades'])
                    aggregated_results['risk_analysis'] = all_trades_analysis
                    
                except ImportError:
                    logger.error("risk_manager module not available for aggregation")
        
        return aggregated_results


def generate_risk_managed_aggregate_report(results: Dict, period: str, output_dir: str) -> str:
    """Generate aggregate report for risk-managed backtests."""
    try:
        from risk_manager import analyze_risk_managed_trades
    except ImportError:
        logger.error("risk_manager module not available for risk-managed aggregate reporting")
        return "Error: risk_manager module not available"

    trades = results.get("all_paired_trades", [])
    tickers_processed = results.get("tickers_processed", [])
    tickers_failed = results.get("tickers_failed", [])
    partial_trades = [t for t in trades if t.get("partial_exit", False)]
    full_exits = [t for t in trades if not t.get("partial_exit", False)]

    risk_analysis = results.get("risk_analysis")
    if not risk_analysis:
        risk_analysis = analyze_risk_managed_trades(trades)

    starting_equity = results.get("account_value", 100000)
    portfolio_ledger = None
    ending_equity = starting_equity
    total_pnl = 0.0
    return_pct = 0.0

    if trades:
        ledger_df = pd.DataFrame(trades).copy()
        if 'dollar_pnl' not in ledger_df.columns:
            ledger_df['dollar_pnl'] = 0.0
        ledger_df['dollar_pnl'] = ledger_df['dollar_pnl'].fillna(0.0)
        ledger_df['exit_date'] = pd.to_datetime(ledger_df.get('exit_date'), errors='coerce')
        ledger_df = ledger_df.sort_values(by=['exit_date', 'ticker'], na_position='last')
        ledger_df['portfolio_equity'] = starting_equity + ledger_df['dollar_pnl'].cumsum()
        ending_equity = ledger_df['portfolio_equity'].iloc[-1] if not ledger_df.empty else starting_equity
        total_pnl = ending_equity - starting_equity
        return_pct = (total_pnl / starting_equity * 100) if starting_equity else 0.0
        portfolio_ledger = ledger_df[['exit_date', 'ticker', 'dollar_pnl', 'portfolio_equity']]

    def _fmt_date(value):
        if isinstance(value, (pd.Timestamp, datetime)):
            return value.strftime("%Y-%m-%d")
        return value.strftime("%Y-%m-%d") if hasattr(value, "strftime") else (str(value) if value else "N/A")

    report_lines: List[str] = []
    report_lines.append("=" * 80)
    report_lines.append("🎯 RISK-MANAGED BATCH BACKTEST REPORT")
    report_lines.append("Item #5: P&L-Aware Exit Logic - Aggregate Analysis")
    report_lines.append("=" * 80)
    report_lines.append("")
    report_lines.append(f"Analysis Period: {period}")
    report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("")

    report_lines.append("📊 BATCH PROCESSING SUMMARY:")
    report_lines.append(f"  Tickers Analyzed: {len(tickers_processed)}")
    report_lines.append(f"  Tickers Failed: {len(tickers_failed)}")
    report_lines.append(f"  Total Trades Recorded: {len(trades)}")
    report_lines.append(f"  Full Exits Logged: {len(full_exits)}")
    report_lines.append(f"  Partial Exits Logged: {len(partial_trades)}")
    report_lines.append("")

    if tickers_failed:
        report_lines.append("⚠️  FAILED TICKERS:")
        for failure in tickers_failed:
            report_lines.append(f"  • {failure['ticker']}: {failure['error']}")
        report_lines.append("")

    if tickers_processed:
        report_lines.append("✅ Successfully Analyzed:")
        report_lines.append(f"  {', '.join(tickers_processed)}")
        report_lines.append("")
    else:
        report_lines.append("⚠️  No tickers were successfully processed.")
        return "\n".join(report_lines)

    if not trades:
        report_lines.append("⚠️  No trades captured by the RiskManager.")
        report_lines.append("   Verify signal configuration or extend the analysis window.")
        return "\n".join(report_lines)

    report_lines.append("=" * 80)
    report_lines.append("💰 PORTFOLIO SUMMARY")
    report_lines.append("=" * 80)
    report_lines.append("")
    report_lines.append(f"  Starting Equity: ${starting_equity:,.0f}")
    report_lines.append(f"  Ending Equity: ${ending_equity:,.0f}")
    report_lines.append(f"  Net Profit: ${total_pnl:,.0f} ({return_pct:.2f}%)")
    report_lines.append(f"  Trades Counted (including partial exits): {len(trades)}")
    report_lines.append("")
    if portfolio_ledger is not None and not portfolio_ledger.empty:
        report_lines.append("🧾 Latest Portfolio Movements:")
        recent_rows = portfolio_ledger.tail(5)
        for _, row in recent_rows.iterrows():
            date_str = row['exit_date'].strftime("%Y-%m-%d") if pd.notnull(row['exit_date']) else "N/A"
            report_lines.append(
                f"  • {date_str} {row['ticker']}: "
                f"${row['dollar_pnl']:,.0f}  ➜  Equity ${row['portfolio_equity']:,.0f}"
            )
        report_lines.append("")

    report_lines.append("=" * 80)
    report_lines.append("📈 R-MULTIPLE PERFORMANCE")
    report_lines.append("=" * 80)
    report_lines.append("")

    key_metrics = [
        ("Win Rate", "Win Rate"),
        ("Average R-Multiple", "Average R-Multiple"),
        ("Average Profit %", "Average Profit %"),
        ("Average Bars Held", "Average Bars Held"),
        ("Profit Scaling Used", "Profit Scaling Used"),
        ("Peak R-Multiple Avg", "Peak R-Multiple Avg"),
        ("Best Trade", "Best Trade"),
        ("Worst Trade", "Worst Trade"),
    ]

    if isinstance(risk_analysis, dict):
        for label, key in key_metrics:
            report_lines.append(f"  {label}: {risk_analysis.get(key, 'N/A')}")
        report_lines.append("")

        exit_breakdown = risk_analysis.get("Exit Type Breakdown", {})
        if exit_breakdown:
            report_lines.append("🛑 Exit Type Distribution:")
            for exit_type, count in exit_breakdown.items():
                pretty = exit_type.replace('_', ' ').title() if isinstance(exit_type, str) else str(exit_type)
                report_lines.append(f"  • {pretty}: {count}")
            report_lines.append("")

        r_distribution = risk_analysis.get("R-Multiple Distribution", {})
        if r_distribution:
            report_lines.append("📊 R-Multiple Distribution:")
            for bucket, count in r_distribution.items():
                report_lines.append(f"  • {bucket}: {count}")
            report_lines.append("")
    else:
        report_lines.append("  Unable to compute aggregate risk analysis.")
        report_lines.append("")

    sorted_all_trades = sorted(trades, key=lambda t: t.get("r_multiple", 0), reverse=True)
    if sorted_all_trades:
        best_trade = sorted_all_trades[0]
        worst_trade = sorted(trades, key=lambda t: t.get("r_multiple", 0))[0]
        report_lines.append("🏆 Highlight Trades:")
        report_lines.append(
            f"  Best Trade: {best_trade.get('ticker', 'N/A')} "
            f"({ _fmt_date(best_trade.get('exit_date')) }) "
            f"{best_trade.get('r_multiple', 0):+.2f}R / {best_trade.get('profit_pct', 0):+.2f}%"
        )
        report_lines.append(
            f"  Toughest Trade: {worst_trade.get('ticker', 'N/A')} "
            f"({ _fmt_date(worst_trade.get('exit_date')) }) "
            f"{worst_trade.get('r_multiple', 0):+.2f}R / {worst_trade.get('profit_pct', 0):+.2f}%"
        )
        report_lines.append("")

    ticker_results = results.get("ticker_specific_results", {})
    if ticker_results:
        report_lines.append("🗂️  Ticker Breakdown:")
        for ticker, info in sorted(
            ticker_results.items(), key=lambda item: item[1].get("total_trades", 0), reverse=True
        ):
            report_lines.append(
                f"  • {ticker}: {info.get('total_trades', 0)} trades "
                f"({info.get('closed_trades', 0)} fully closed)"
            )
        report_lines.append("")

    report_lines.append("=" * 80)
    report_lines.append("⚠️  DISCLAIMER")
    report_lines.append("=" * 80)
    report_lines.append("")
    report_lines.append("This analysis is based on historical data managed with the RiskManager framework.")
    report_lines.append("Past performance is not indicative of future returns. Validate assumptions before trading.")
    report_lines.append("")
    report_lines.append("=" * 80)

    return "\n".join(report_lines)


def generate_aggregate_report(results: Dict, period: str, output_dir: str) -> str:
    """Generate aggregate report for traditional entry/exit backtests."""
    report_lines: List[str] = []

    tickers_processed = results.get("tickers_processed", [])
    tickers_failed = results.get("tickers_failed", [])
    all_trades = results.get("all_paired_trades", [])
    entry_stats = results.get("entry_signal_stats", {})
    exit_stats = results.get("exit_signal_stats", {})

    report_lines.append("=" * 80)
    report_lines.append("🎯 COLLECTIVE STRATEGY OPTIMIZATION REPORT")
    report_lines.append("=" * 80)
    report_lines.append("")
    report_lines.append(f"Analysis Period: {period}")
    report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("")

    report_lines.append("📊 BATCH PROCESSING SUMMARY:")
    report_lines.append(f"  Tickers Analyzed: {len(tickers_processed)}")
    report_lines.append(f"  Tickers Failed: {len(tickers_failed)}")
    report_lines.append(f"  Total Trades Generated: {len(all_trades)}")

    closed_trades = [t for t in all_trades if not t.get("is_open", False)]
    open_trades = len(all_trades) - len(closed_trades)

    report_lines.append(f"  Closed Trades: {len(closed_trades)}")
    report_lines.append(f"  Open Positions: {open_trades}")
    report_lines.append("")

    if tickers_failed:
        report_lines.append("⚠️  FAILED TICKERS:")
        for failure in tickers_failed:
            report_lines.append(f"  • {failure['ticker']}: {failure['error']}")
        report_lines.append("")

    if tickers_processed:
        report_lines.append("✅ Successfully Analyzed:")
        report_lines.append(f"  {', '.join(tickers_processed)}")
        report_lines.append("")
    else:
        report_lines.append("⚠️  No tickers were successfully processed.")
        return "\n".join(report_lines)

    if len(closed_trades) == 0:
        report_lines.append("⚠️  No closed trades available for analysis.")
        report_lines.append("   Try a longer time period to generate more signals.")
        return "\n".join(report_lines)

    report_lines.append("=" * 80)
    report_lines.append("🚀 COLLECTIVE ENTRY STRATEGY ANALYSIS")
    report_lines.append("=" * 80)
    report_lines.append("")

    sorted_entries = []
    if entry_stats:
        sorted_entries = sorted(
            entry_stats.items(),
            key=lambda item: (item[1]["expectancy"], item[1]["win_rate"]),
            reverse=True
        )
        report_lines.append("Ranked by Expected Value per Trade:")
        report_lines.append("")
        for rank, (_, metrics) in enumerate(sorted_entries, 1):
            report_lines.append(f"{rank}. {metrics['name']}")
            report_lines.append(f"   {'─'*70}")
            report_lines.append(f"   Total Trades: {metrics['total_trades']} ({metrics['closed_trades']} closed, {metrics['open_trades']} open)")
            report_lines.append(f"   Win Rate: {metrics['win_rate']:.1f}% ({metrics['wins']} wins, {metrics['losses']} losses)")
            report_lines.append(f"   Typical Return: {metrics['median_return']:+.2f}% (median) ⭐ USE THIS")
            report_lines.append(f"   Average Return: {metrics['avg_return']:+.2f}% (mean - inflated by outliers)")
            
            # Add outlier warning if mean >> median
            if abs(metrics['avg_return']) > abs(metrics['median_return']) * 2:
                report_lines.append(f"   ⚠️  OUTLIER IMPACT: Mean is {abs(metrics['avg_return'] / metrics['median_return']):.1f}x median - use median for expectations!")
            
            report_lines.append(f"   Avg Win: {metrics['avg_win']:+.2f}% | Avg Loss: {metrics['avg_loss']:+.2f}%")
            
            # Get best/worst trades with ticker information
            best_trade_ticker = metrics.get('best_trade_ticker', 'N/A')
            worst_trade_ticker = metrics.get('worst_trade_ticker', 'N/A')
            report_lines.append(f"   Best Trade: {best_trade_ticker} {metrics['best_trade_date']} ({metrics['best_return']:+.2f}%)")
            report_lines.append(f"   Worst Trade: {worst_trade_ticker} {metrics['worst_trade_date']} ({metrics['worst_return']:+.2f}%)")
            report_lines.append(f"   Avg Holding: {metrics['avg_holding_days']:.1f} days")
            report_lines.append(f"   Profit Factor: {metrics['profit_factor']:.2f}")
            report_lines.append(f"   Expectancy: {metrics['expectancy']:+.2f}%")

            if metrics['win_rate'] >= 70 and metrics['expectancy'] > 2.0:
                rating = "⭐⭐⭐ EXCELLENT - Top tier strategy"
            elif metrics['win_rate'] >= 60 and metrics['expectancy'] > 1.0:
                rating = "⭐⭐ GOOD - Strong positive edge"
            elif metrics['win_rate'] >= 50 and metrics['expectancy'] > 0:
                rating = "⭐ FAIR - Marginal edge, monitor risk"
            else:
                rating = "⚠️ Needs improvement - Refine filters or exits"
            report_lines.append(f"   Rating: {rating}")
            report_lines.append("")
    else:
        report_lines.append("No entry signal performance data available.")
        report_lines.append("Ensure trades were recorded with entry signal metadata.")
        report_lines.append("")

    report_lines.append("=" * 80)
    report_lines.append("🛑 EXIT STRATEGY EFFECTIVENESS")
    report_lines.append("=" * 80)
    report_lines.append("")

    sorted_exits = []
    if exit_stats:
        sorted_exits = sorted(
            exit_stats.items(),
            key=lambda item: (item[1]["win_rate"], item[1]["avg_return"]),
            reverse=True
        )
        report_lines.append("Ranked by Win Rate and Return Preservation:")
        report_lines.append("")
        for rank, (_, metrics) in enumerate(sorted_exits, 1):
            report_lines.append(f"{rank}. {metrics['name']}")
            report_lines.append(f"   {'─'*70}")
            report_lines.append(f"   Total Trades: {metrics['total_trades']} ({metrics['closed_trades']} closed, {metrics['open_trades']} open)")
            report_lines.append(f"   Win Rate: {metrics['win_rate']:.1f}% ({metrics['wins']} wins, {metrics['losses']} losses)")
            report_lines.append(f"   Typical Return: {metrics['median_return']:+.2f}% (median) ⭐ USE THIS")
            report_lines.append(f"   Average Return: {metrics['avg_return']:+.2f}% (mean - may be inflated by outliers)")
            
            # Add outlier warning if mean >> median
            if abs(metrics['avg_return']) > abs(metrics['median_return']) * 2:
                report_lines.append(f"   ⚠️  OUTLIER IMPACT: Mean is {abs(metrics['avg_return'] / metrics['median_return']):.1f}x median!")
            
            report_lines.append(f"   Avg Win: {metrics['avg_win']:+.2f}% | Avg Loss: {metrics['avg_loss']:+.2f}%")
            
            # Get best/worst trades with ticker information
            best_trade_ticker = metrics.get('best_trade_ticker', 'N/A')
            worst_trade_ticker = metrics.get('worst_trade_ticker', 'N/A')
            report_lines.append(f"   Best Trade: {best_trade_ticker} {metrics['best_trade_date']} ({metrics['best_return']:+.2f}%)")
            report_lines.append(f"   Worst Trade: {worst_trade_ticker} {metrics['worst_trade_date']} ({metrics['worst_return']:+.2f}%)")
            report_lines.append(f"   Avg Holding: {metrics['avg_holding_days']:.1f} days")
            report_lines.append(f"   Profit Factor: {metrics['profit_factor']:.2f}")
            report_lines.append(f"   Expectancy: {metrics['expectancy']:+.2f}%")
            report_lines.append("")
    else:
        report_lines.append("No exit signal performance data available.")
        report_lines.append("Ensure trades were recorded with exit signal metadata.")
        report_lines.append("")

    report_lines.append("=" * 80)
    report_lines.append("💡 OPTIMAL STRATEGY RECOMMENDATION")
    report_lines.append("=" * 80)
    report_lines.append("")

    if entry_stats:
        top_entry = max(
            entry_stats.items(), key=lambda item: (item[1]["expectancy"], item[1]["win_rate"])
        )[1]
        report_lines.append("🎯 RECOMMENDED ENTRY SIGNAL:")
        report_lines.append(f"   {top_entry['name']}")
        report_lines.append(f"   • Win Rate: {top_entry['win_rate']:.1f}%")
        report_lines.append(f"   • Expectancy: {top_entry['expectancy']:+.2f}% per trade")
        report_lines.append(f"   • Average Return: {top_entry['avg_return']:+.2f}%")
        report_lines.append(f"   • Profit Factor: {top_entry['profit_factor']:.2f}")
        report_lines.append(f"   • Based on {top_entry['closed_trades']} closed trades")
        report_lines.append("")

    if exit_stats:
        top_exit = max(
            exit_stats.items(), key=lambda item: (item[1]['win_rate'], item[1]['avg_return'])
        )[1]
        report_lines.append("🎯 RECOMMENDED EXIT SIGNAL:")
        report_lines.append(f"   {top_exit['name']}")
        report_lines.append(f"   • Win Rate: {top_exit['win_rate']:.1f}%")
        report_lines.append(f"   • Expectancy: {top_exit['expectancy']:+.2f}%")
        report_lines.append(f"   • Average Return: {top_exit['avg_return']:+.2f}%")
        report_lines.append(f"   • Profit Factor: {top_exit['profit_factor']:.2f}")
        report_lines.append(f"   • Based on {top_exit['closed_trades']} closed trades")
        report_lines.append("")

    if len(closed_trades) >= 100:
        report_lines.append("📈 SAMPLE SIZE: ✅ Robust dataset (100+ closed trades). Findings statistically significant.")
    elif len(closed_trades) >= 40:
        report_lines.append("📈 SAMPLE SIZE: ⚠️ Moderate dataset (40-99 closed trades). Findings directional; monitor for consistency.")
    else:
        report_lines.append("📈 SAMPLE SIZE: ❗ Limited dataset (<40 closed trades). Treat results as exploratory.")
    report_lines.append("")

    report_lines.append("KEY NEXT STEPS:")
    report_lines.append("  • Validate recommended strategies with forward testing")
    report_lines.append("  • Stress test exits under different volatility regimes")
    report_lines.append("  • Incorporate position sizing rules before production use")
    report_lines.append("")

    report_lines.append("=" * 80)
    report_lines.append("💡 KEY INSIGHTS & RECOMMENDATIONS")
    report_lines.append("=" * 80)
    report_lines.append("")

    if entry_stats:
        consistent_entries = [
            (name, metrics) for name, metrics in entry_stats.items() if metrics['closed_trades'] >= 5
        ]
        if consistent_entries:
            most_consistent = max(consistent_entries, key=lambda item: item[1]['win_rate'])
            report_lines.append(f"✓ Most Consistent Entry: {most_consistent[1]['name']}")
            report_lines.append(
                f"  ({most_consistent[1]['win_rate']:.1f}% win rate over {most_consistent[1]['closed_trades']} trades)"
            )
            report_lines.append("")

        if sorted_entries:
            highest_exp = sorted_entries[0]
            report_lines.append(f"✓ Highest Expected Value: {highest_exp[1]['name']}")
            report_lines.append(
                f"  (Expectancy: {highest_exp[1]['expectancy']:+.2f}% per trade)"
            )
            report_lines.append("")

    if exit_stats and sorted_exits:
        safest_exit = sorted_exits[0][1]
        report_lines.append(f"✓ Most Reliable Exit: {safest_exit['name']}")
        report_lines.append(f"  ({safest_exit['win_rate']:.1f}% win rate)")
        report_lines.append("")

    report_lines.append("📝 TRADING RECOMMENDATIONS:")
    report_lines.append("")
    report_lines.append("  1. ENTRY STRATEGY:")
    if sorted_entries:
        for idx, (_, metrics) in enumerate(sorted_entries[:3], 1):
            report_lines.append(
                f"     {idx}. {metrics['name']} (Exp: {metrics['expectancy']:+.2f}%, WR: {metrics['win_rate']:.1f}%)"
            )
    report_lines.append("")

    report_lines.append("  2. EXIT STRATEGY:")
    if sorted_exits:
        for idx, (_, metrics) in enumerate(sorted_exits[:3], 1):
            report_lines.append(
                f"     {idx}. {metrics['name']} (WR: {metrics['win_rate']:.1f}%, Ret: {metrics['avg_return']:+.2f}%)"
            )
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

    report_lines.append("=" * 80)
    report_lines.append("⚠️  DISCLAIMER")
    report_lines.append("=" * 80)
    report_lines.append("")
    report_lines.append("This analysis is based on historical data and does not guarantee future performance.")
    report_lines.append("Past results are not indicative of future returns. Always perform your own due diligence and consider your risk tolerance before trading.")
    report_lines.append("")
    report_lines.append("=" * 80)

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
        '-f', '--file',
        dest='ticker_file',
        required=True,
        help='Path to file containing ticker symbols (one per line)'
    )
    
    parser.add_argument(
        '-p', '--period',
        default='12mo',
        help='Analysis period (default: 12mo) - ignored if date range provided'
    )
    
    parser.add_argument(
        '--start-date',
        help='Start date for analysis (YYYY-MM-DD) - for regime analysis'
    )
    
    parser.add_argument(
        '--end-date',
        help='End date for analysis (YYYY-MM-DD) - for regime analysis'
    )
    
    parser.add_argument(
        '-o', '--output-dir',
        default='backtest_results',
        help='Output directory for backtest reports (default: backtest_results)'
    )
    
    parser.add_argument(
        '--risk-managed',
        action='store_true',
        help='Use RiskManager for P&L-aware exits (Item #5)'
    )
    
    parser.add_argument(
        '--stop-strategy',
        choices=['static', 'vol_regime', 'atr_dynamic', 'pct_trail', 'time_decay'],
        default='time_decay',
        help='Stop-loss strategy when running risk-managed backtests (default: time_decay)'
    )
    
    parser.add_argument(
        '--account-value',
        type=float,
        default=100000,
        help='Starting account equity for risk-managed runs (default: 100000)'
    )
    
    args = parser.parse_args()
    
    # Validate date range if provided
    if (args.start_date and not args.end_date) or (args.end_date and not args.start_date):
        parser.error("--start-date and --end-date must be used together")
    
    # Run batch backtest
    results = run_batch_backtest(
        ticker_file=args.ticker_file,
        period=args.period,
        start_date=args.start_date,
        end_date=args.end_date,
        output_dir=args.output_dir,
        risk_managed=args.risk_managed,
        account_value=args.account_value,
        stop_strategy=args.stop_strategy
    )
    
    if not results or not results['all_paired_trades']:
        print("\n❌ No results generated. Check for errors above.")
        sys.exit(1)
    
    # Determine period display for reports
    if args.start_date and args.end_date:
        period_display = f"{args.start_date} to {args.end_date}"
        file_suffix = f"{args.start_date}_{args.end_date}".replace('-', '')
    else:
        period_display = args.period
        file_suffix = args.period
    
    # Generate aggregate report tailored to run mode
    print(f"\n📊 Generating aggregate optimization report...")
    if args.risk_managed:
        aggregate_report = generate_risk_managed_aggregate_report(results, period_display, args.output_dir)
    else:
        aggregate_report = generate_aggregate_report(results, period_display, args.output_dir)
    
    # Save aggregate report
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    agg_filename = f"AGGREGATE_optimization_{file_suffix}_{timestamp}.txt"
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
