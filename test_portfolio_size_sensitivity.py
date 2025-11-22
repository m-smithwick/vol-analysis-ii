#!/usr/bin/env python3
"""
Portfolio Size Sensitivity Analysis

Tests how the number of tickers in a portfolio affects dollar returns.
Runs batch backtests with varying portfolio sizes and compares results.

Usage:
    python test_portfolio_size_sensitivity.py
"""

import subprocess
import os
import sys
import re
import csv
from datetime import datetime
from typing import List, Dict, Tuple
import glob


class PortfolioSizeTester:
    """Tests portfolio performance across different sizes."""
    
    def __init__(
        self,
        ticker_file: str = "cmb.txt",
        portfolio_sizes: List[int] = [10, 25, 40],
        period: str = "24mo",
        account_value: float = 100000,
        stop_strategy: str = "time_decay",
        output_dir: str = "backtest_results/portfolio_sensitivity"
    ):
        """
        Initialize portfolio size tester.
        
        Args:
            ticker_file: Source file with all available tickers
            portfolio_sizes: List of portfolio sizes to test
            period: Backtest period (e.g., "24mo")
            account_value: Starting equity (fixed across all sizes)
            stop_strategy: Stop loss strategy to use
            output_dir: Output directory for results
        """
        self.ticker_file = ticker_file
        self.portfolio_sizes = sorted(portfolio_sizes)
        self.period = period
        self.account_value = account_value
        self.stop_strategy = stop_strategy
        self.output_dir = output_dir
        self.temp_files: List[str] = []
        self.results: List[Dict] = []
        
    def read_tickers(self) -> List[str]:
        """Read ticker list from file."""
        print(f"\n📂 Reading tickers from {self.ticker_file}...")
        
        if not os.path.exists(self.ticker_file):
            raise FileNotFoundError(f"Ticker file not found: {self.ticker_file}")
        
        with open(self.ticker_file, 'r') as f:
            tickers = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        
        print(f"✅ Found {len(tickers)} tickers: {', '.join(tickers[:5])}...")
        return tickers
    
    def create_temp_ticker_files(self, all_tickers: List[str]) -> List[Tuple[int, str]]:
        """
        Create temporary ticker files for each portfolio size.
        
        Args:
            all_tickers: List of all available tickers
            
        Returns:
            List of (size, filepath) tuples
        """
        print(f"\n📝 Creating temporary ticker files...")
        temp_files = []
        
        for size in self.portfolio_sizes:
            if size > len(all_tickers):
                print(f"⚠️  Warning: Portfolio size {size} exceeds available tickers ({len(all_tickers)}). Using all tickers.")
                size = len(all_tickers)
            
            # Select first N tickers
            selected_tickers = all_tickers[:size]
            
            # Create temp file
            temp_filename = f"temp_{size}_tickers.txt"
            with open(temp_filename, 'w') as f:
                for ticker in selected_tickers:
                    f.write(f"{ticker}\n")
            
            self.temp_files.append(temp_filename)
            temp_files.append((size, temp_filename))
            print(f"  ✓ Created {temp_filename}: {', '.join(selected_tickers[:3])}... ({size} tickers)")
        
        return temp_files
    
    def run_backtest(self, size: int, ticker_file: str) -> bool:
        """
        Run batch backtest for a specific portfolio size.
        
        Args:
            size: Portfolio size (number of tickers)
            ticker_file: Path to ticker file
            
        Returns:
            True if successful, False otherwise
        """
        print(f"\n{'='*80}")
        print(f"🚀 RUNNING BACKTEST: {size} tickers")
        print(f"{'='*80}")
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Build command
        cmd = [
            "python", "batch_backtest.py",
            "--file", ticker_file,
            "--period", self.period,
            "--account-value", str(self.account_value),
            "--stop-strategy", self.stop_strategy,
            "--output-dir", self.output_dir,
            "--risk-managed"
        ]
        
        print(f"Command: {' '.join(cmd)}")
        print(f"Starting equity: ${self.account_value:,.0f}")
        print(f"Period: {self.period}")
        print(f"Stop strategy: {self.stop_strategy}")
        print()
        
        try:
            # Run backtest
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            print(result.stdout)
            
            if result.stderr:
                print("⚠️  Warnings/Errors:")
                print(result.stderr)
            
            print(f"\n✅ Backtest completed for {size} tickers")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"\n❌ Backtest failed for {size} tickers")
            print(f"Error: {e}")
            if e.stdout:
                print(f"Output: {e.stdout}")
            if e.stderr:
                print(f"Error output: {e.stderr}")
            return False
    
    def parse_aggregate_report(self, size: int) -> Dict:
        """
        Parse the aggregate report for a specific portfolio size.
        
        Args:
            size: Portfolio size
            
        Returns:
            Dict with extracted metrics
        """
        print(f"\n📊 Parsing results for {size}-ticker portfolio...")
        
        # Find the most recent aggregate report
        pattern = f"{self.output_dir}/AGGREGATE_optimization_*_{self.period}_*.txt"
        report_files = glob.glob(pattern)
        
        if not report_files:
            print(f"⚠️  No aggregate report found matching: {pattern}")
            return None
        
        # Get most recent file
        report_file = max(report_files, key=os.path.getmtime)
        print(f"Reading: {report_file}")
        
        # Parse report
        metrics = {
            'portfolio_size': size,
            'starting_equity': self.account_value,
            'ending_equity': None,
            'total_pnl': None,
            'return_pct': None,
            'total_trades': None,
            'win_rate': None,
            'avg_r_multiple': None,
            'avg_profit_pct': None,
            'avg_bars_held': None,
            'best_trade': None,
            'worst_trade': None,
            'profit_targets': None,
            'time_stops': None,
            'hard_stops': None,
            'trail_stops': None
        }
        
        try:
            with open(report_file, 'r') as f:
                content = f.read()
            
            # Extract metrics using regex
            patterns = {
                'ending_equity': r'Ending Equity:\s*\$([0-9,]+)',
                'total_pnl': r'Net Profit:\s*\$([0-9,]+)\s*\(([+-]?[0-9.]+)%\)',
                'total_trades': r'Trades Counted.*:\s*(\d+)',
                'win_rate': r'Win Rate:\s*([0-9.]+)%',
                'avg_r_multiple': r'Average R-Multiple:\s*([+-]?[0-9.]+)R',
                'avg_profit_pct': r'Average Profit %:\s*([+-]?[0-9.]+)%',
                'avg_bars_held': r'Average Bars Held:\s*([0-9.]+)',
                'best_trade': r'Best Trade:.*\(([+-]?[0-9.]+)R',
                'worst_trade': r'Toughest Trade:.*\(([+-]?[0-9.]+)R',
                'profit_targets': r'Profit Target.*:\s*(\d+)',
                'time_stops': r'Time Stop.*:\s*(\d+)',
                'hard_stops': r'Hard Stop.*:\s*(\d+)',
                'trail_stops': r'Trailing Stop.*:\s*(\d+)'
            }
            
            for key, pattern in patterns.items():
                match = re.search(pattern, content)
                if match:
                    value = match.group(1).replace(',', '')
                    
                    # Handle return_pct separately (it's in group 2 of total_pnl)
                    if key == 'total_pnl':
                        metrics['total_pnl'] = float(value)
                        metrics['return_pct'] = float(match.group(2))
                    elif key in ['win_rate', 'avg_profit_pct', 'avg_bars_held', 'avg_r_multiple', 'best_trade', 'worst_trade']:
                        metrics[key] = float(value)
                    else:
                        metrics[key] = int(value)
            
            print(f"  ✓ Parsed metrics for {size} tickers")
            print(f"    Ending equity: ${metrics['ending_equity']:,.0f}")
            print(f"    Total P&L: ${metrics['total_pnl']:,.0f} ({metrics['return_pct']:+.2f}%)")
            print(f"    Total trades: {metrics['total_trades']}")
            print(f"    Win rate: {metrics['win_rate']:.1f}%")
            
            return metrics
            
        except Exception as e:
            print(f"❌ Error parsing report: {e}")
            return None
    
    def generate_summary_report(self) -> str:
        """
        Generate comprehensive summary report.
        
        Returns:
            Report text
        """
        lines = []
        lines.append("=" * 80)
        lines.append("📈 PORTFOLIO SIZE SENSITIVITY ANALYSIS")
        lines.append("=" * 80)
        lines.append("")
        lines.append(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Period: {self.period}")
        lines.append(f"Starting Equity: ${self.account_value:,.0f} (fixed across all sizes)")
        lines.append(f"Stop Strategy: {self.stop_strategy}")
        lines.append(f"Portfolio Sizes Tested: {', '.join(map(str, self.portfolio_sizes))}")
        lines.append("")
        
        lines.append("=" * 80)
        lines.append("📊 RESULTS SUMMARY")
        lines.append("=" * 80)
        lines.append("")
        
        # Create results table
        lines.append(f"{'Size':<8} {'End Equity':>12} {'P&L':>12} {'Return%':>10} {'Trades':>8} {'WinRate':>9} {'Avg R':>8}")
        lines.append("-" * 80)
        
        for result in self.results:
            lines.append(
                f"{result['portfolio_size']:<8} "
                f"${result['ending_equity']:>11,} "
                f"${result['total_pnl']:>11,} "
                f"{result['return_pct']:>9.2f}% "
                f"{result['total_trades']:>8} "
                f"{result['win_rate']:>8.1f}% "
                f"{result['avg_r_multiple']:>7.2f}R"
            )
        
        lines.append("")
        lines.append("=" * 80)
        lines.append("🎯 DETAILED ANALYSIS")
        lines.append("=" * 80)
        lines.append("")
        
        for result in self.results:
            lines.append(f"Portfolio Size: {result['portfolio_size']} tickers")
            lines.append("-" * 40)
            lines.append(f"  Starting Equity: ${result['starting_equity']:,.0f}")
            lines.append(f"  Ending Equity: ${result['ending_equity']:,.0f}")
            lines.append(f"  Total P&L: ${result['total_pnl']:,.0f}")
            lines.append(f"  Return: {result['return_pct']:+.2f}%")
            lines.append(f"  Total Trades: {result['total_trades']}")
            lines.append(f"  Win Rate: {result['win_rate']:.1f}%")
            lines.append(f"  Avg R-Multiple: {result['avg_r_multiple']:.2f}R")
            lines.append(f"  Avg Profit %: {result['avg_profit_pct']:.2f}%")
            lines.append(f"  Avg Bars Held: {result['avg_bars_held']:.1f}")
            lines.append(f"  Best Trade: {result['best_trade']:.2f}R")
            lines.append(f"  Worst Trade: {result['worst_trade']:.2f}R")
            lines.append("")
            lines.append(f"  Exit Type Distribution:")
            lines.append(f"    Profit Targets: {result['profit_targets']}")
            lines.append(f"    Time Stops: {result['time_stops']}")
            lines.append(f"    Hard/Dynamic Stops: {result['hard_stops']}")
            lines.append(f"    Trailing Stops: {result['trail_stops']}")
            lines.append("")
        
        lines.append("=" * 80)
        lines.append("💡 KEY INSIGHTS")
        lines.append("=" * 80)
        lines.append("")
        
        # Calculate insights
        if len(self.results) >= 2:
            # Find best/worst by different metrics
            best_return = max(self.results, key=lambda x: x['return_pct'])
            best_dollar = max(self.results, key=lambda x: x['total_pnl'])
            best_winrate = max(self.results, key=lambda x: x['win_rate'])
            most_trades = max(self.results, key=lambda x: x['total_trades'])
            
            lines.append(f"🏆 Best Return %: {best_return['portfolio_size']} tickers ({best_return['return_pct']:+.2f}%)")
            lines.append(f"💰 Best Dollar P&L: {best_dollar['portfolio_size']} tickers (${best_dollar['total_pnl']:,.0f})")
            lines.append(f"🎯 Best Win Rate: {best_winrate['portfolio_size']} tickers ({best_winrate['win_rate']:.1f}%)")
            lines.append(f"📊 Most Trade Opportunities: {most_trades['portfolio_size']} tickers ({most_trades['total_trades']} trades)")
            lines.append("")
            
            # Diversification analysis
            lines.append("📈 DIVERSIFICATION ANALYSIS:")
            lines.append("")
            
            # Compare smallest vs largest
            smallest = self.results[0]
            largest = self.results[-1]
            
            pnl_diff = largest['total_pnl'] - smallest['total_pnl']
            pnl_pct_change = (pnl_diff / abs(smallest['total_pnl']) * 100) if smallest['total_pnl'] != 0 else 0
            
            lines.append(f"  {smallest['portfolio_size']} tickers → {largest['portfolio_size']} tickers:")
            lines.append(f"    P&L Change: ${pnl_diff:,.0f} ({pnl_pct_change:+.1f}%)")
            lines.append(f"    Return Change: {largest['return_pct'] - smallest['return_pct']:+.2f} percentage points")
            lines.append(f"    Trade Count Change: {largest['total_trades'] - smallest['total_trades']:+d} trades")
            lines.append(f"    Win Rate Change: {largest['win_rate'] - smallest['win_rate']:+.1f} percentage points")
            lines.append("")
            
            # Risk-adjusted metrics
            lines.append("⚖️ RISK-ADJUSTED METRICS:")
            lines.append("")
            for result in self.results:
                # Simple risk-adjusted return = return% / (100 - win_rate)
                # Higher is better (high return with high win rate)
                risk_adjusted = result['return_pct'] / (100 - result['win_rate']) if result['win_rate'] < 100 else result['return_pct']
                lines.append(f"  {result['portfolio_size']} tickers: Risk-adjusted score = {risk_adjusted:.3f}")
            lines.append("")
        
        lines.append("=" * 80)
        lines.append("🎓 RECOMMENDATIONS")
        lines.append("=" * 80)
        lines.append("")
        
        if self.results:
            # Recommendation based on dollar P&L (primary metric requested)
            best_pnl_result = max(self.results, key=lambda x: x['total_pnl'])
            
            lines.append(f"Primary Recommendation (Best Dollar Returns):")
            lines.append(f"  Portfolio Size: {best_pnl_result['portfolio_size']} tickers")
            lines.append(f"  Expected Return: ${best_pnl_result['total_pnl']:,.0f} ({best_pnl_result['return_pct']:+.2f}%)")
            lines.append(f"  Trade Frequency: {best_pnl_result['total_trades']} opportunities")
            lines.append(f"  Win Rate: {best_pnl_result['win_rate']:.1f}%")
            lines.append("")
            
            # Secondary considerations
            lines.append("Considerations:")
            if len(self.results) >= 2:
                smallest_result = self.results[0]
                largest_result = self.results[-1]
                
                if smallest_result['return_pct'] > largest_result['return_pct']:
                    lines.append("  • Smaller portfolios showed higher concentration returns")
                    lines.append("  • Consider if you can handle higher position concentration")
                else:
                    lines.append("  • Larger portfolios provide better diversification")
                    lines.append("  • More trade opportunities with broader coverage")
                
                if abs(largest_result['total_pnl'] - smallest_result['total_pnl']) < (self.account_value * 0.02):
                    lines.append("  • Portfolio size showed minimal impact on returns")
                    lines.append("  • Focus on other optimization factors (timing, stops, etc.)")
            
            lines.append("")
        
        lines.append("=" * 80)
        lines.append("📁 OUTPUT FILES")
        lines.append("=" * 80)
        lines.append("")
        lines.append(f"  • Summary Report: portfolio_size_sensitivity_report.txt")
        lines.append(f"  • Results CSV: portfolio_size_sensitivity_results.csv")
        lines.append(f"  • Detailed Logs: {self.output_dir}/LOG_FILE_temp_*_{self.period}_*.csv")
        lines.append(f"  • Aggregate Reports: {self.output_dir}/AGGREGATE_optimization_*_{self.period}_*.txt")
        lines.append("")
        
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def save_results_csv(self, filename: str = "portfolio_size_sensitivity_results.csv"):
        """Save results to CSV file."""
        print(f"\n💾 Saving results to {filename}...")
        
        if not self.results:
            print("⚠️  No results to save")
            return
        
        # Define CSV columns
        fieldnames = [
            'portfolio_size', 'starting_equity', 'ending_equity', 'total_pnl', 'return_pct',
            'total_trades', 'win_rate', 'avg_r_multiple', 'avg_profit_pct', 'avg_bars_held',
            'best_trade', 'worst_trade', 'profit_targets', 'time_stops', 'hard_stops', 'trail_stops'
        ]
        
        with open(filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.results)
        
        print(f"✅ Results saved to {filename}")
    
    def cleanup_temp_files(self):
        """Remove temporary ticker files."""
        print(f"\n🧹 Cleaning up temporary files...")
        
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    print(f"  ✓ Removed {temp_file}")
            except Exception as e:
                print(f"  ⚠️  Failed to remove {temp_file}: {e}")
    
    def run(self):
        """Execute complete portfolio size sensitivity analysis."""
        print("=" * 80)
        print("🎯 PORTFOLIO SIZE SENSITIVITY ANALYSIS")
        print("=" * 80)
        print(f"\nTesting portfolio sizes: {', '.join(map(str, self.portfolio_sizes))}")
        print(f"Period: {self.period}")
        print(f"Starting equity: ${self.account_value:,.0f} (fixed)")
        print(f"Selection method: First N tickers from {self.ticker_file}")
        
        try:
            # Step 1: Read tickers
            all_tickers = self.read_tickers()
            
            # Step 2: Create temp files
            temp_files = self.create_temp_ticker_files(all_tickers)
            
            # Step 3: Run backtests
            for size, ticker_file in temp_files:
                success = self.run_backtest(size, ticker_file)
                
                if success:
                    # Parse results
                    metrics = self.parse_aggregate_report(size)
                    if metrics:
                        self.results.append(metrics)
                else:
                    print(f"⚠️  Skipping results for {size} tickers due to backtest failure")
            
            # Step 4: Generate reports
            if self.results:
                print("\n" + "=" * 80)
                print("📊 GENERATING SUMMARY REPORTS")
                print("=" * 80)
                
                # Save CSV
                self.save_results_csv()
                
                # Generate and save summary report
                summary = self.generate_summary_report()
                report_filename = "portfolio_size_sensitivity_report.txt"
                with open(report_filename, 'w') as f:
                    f.write(summary)
                print(f"\n💾 Summary report saved to {report_filename}")
                
                # Print summary to console
                print("\n" + summary)
                
                print(f"\n✅ Analysis complete! Check output files for detailed results.")
            else:
                print("\n❌ No successful results to analyze")
            
        finally:
            # Step 5: Cleanup
            self.cleanup_temp_files()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Test portfolio size sensitivity on dollar returns',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run default test (10, 25, 40 tickers from cmb.txt, 24mo period)
  python test_portfolio_size_sensitivity.py
  
  # Custom portfolio sizes
  python test_portfolio_size_sensitivity.py --sizes 5 15 30
  
  # Different ticker source and period
  python test_portfolio_size_sensitivity.py --file stocks.txt --period 12mo
  
  # Different starting capital
  python test_portfolio_size_sensitivity.py --account-value 50000
        """
    )
    
    parser.add_argument(
        '--file',
        default='cmb.txt',
        help='Ticker source file (default: cmb.txt)'
    )
    
    parser.add_argument(
        '--sizes',
        type=int,
        nargs='+',
        default=[10, 25, 40],
        help='Portfolio sizes to test (default: 10 25 40)'
    )
    
    parser.add_argument(
        '--period',
        default='24mo',
        help='Backtest period (default: 24mo)'
    )
    
    parser.add_argument(
        '--account-value',
        type=float,
        default=100000,
        help='Starting equity (default: 100000)'
    )
    
    parser.add_argument(
        '--stop-strategy',
        default='time_decay',
        choices=['static', 'vol_regime', 'atr_dynamic', 'pct_trail', 'time_decay'],
        help='Stop loss strategy (default: time_decay)'
    )
    
    parser.add_argument(
        '--output-dir',
        default='backtest_results/portfolio_sensitivity',
        help='Output directory (default: backtest_results/portfolio_sensitivity)'
    )
    
    args = parser.parse_args()
    
    # Create tester instance
    tester = PortfolioSizeTester(
        ticker_file=args.file,
        portfolio_sizes=args.sizes,
        period=args.period,
        account_value=args.account_value,
        stop_strategy=args.stop_strategy,
        output_dir=args.output_dir
    )
    
    # Run analysis
    tester.run()


if __name__ == "__main__":
    main()
