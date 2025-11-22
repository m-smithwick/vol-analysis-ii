#!/usr/bin/env python3
"""
Portfolio Decomposition Analysis

Analyzes whether larger portfolios' higher returns are due to:
1. Volume Effect: More trades generating more aggregate profit
2. Sizing Effect: Different average profit per trade

Usage:
    python analyze_portfolio_decomposition.py
"""

import pandas as pd
import numpy as np
import glob
import os
from datetime import datetime
from typing import Dict, List, Optional


class PortfolioDecompositionAnalyzer:
    """Analyzes portfolio size sensitivity to decompose return drivers."""
    
    def __init__(
        self,
        sensitivity_dir: str = "backtest_results/portfolio_sensitivity",
        portfolio_sizes: List[int] = [10, 25, 40],
        period: str = "24mo"
    ):
        """
        Initialize analyzer.
        
        Args:
            sensitivity_dir: Directory containing sensitivity test results
            portfolio_sizes: List of portfolio sizes to analyze
            period: Analysis period (e.g., "24mo")
        """
        self.sensitivity_dir = sensitivity_dir
        self.portfolio_sizes = sorted(portfolio_sizes)
        self.period = period
        self.data = {}
        self.metrics = {}
        
    def find_log_file(self, portfolio_size: int) -> Optional[str]:
        """
        Find the LOG_FILE CSV for a specific portfolio size.
        
        Args:
            portfolio_size: Number of tickers in portfolio
            
        Returns:
            Path to LOG_FILE CSV or None if not found
        """
        pattern = f"{self.sensitivity_dir}/LOG_FILE_temp_{portfolio_size}_{self.period}_*.csv"
        files = glob.glob(pattern)
        
        if not files:
            print(f"⚠️  No LOG_FILE found for {portfolio_size} tickers: {pattern}")
            return None
        
        # Return most recent file if multiple exist
        log_file = max(files, key=os.path.getmtime)
        print(f"✓ Found LOG_FILE for {portfolio_size} tickers: {os.path.basename(log_file)}")
        return log_file
    
    def load_trade_data(self, portfolio_size: int) -> Optional[pd.DataFrame]:
        """
        Load trade data from LOG_FILE CSV.
        
        Args:
            portfolio_size: Number of tickers in portfolio
            
        Returns:
            DataFrame with trade data or None if file not found
        """
        log_file = self.find_log_file(portfolio_size)
        
        if not log_file:
            return None
        
        try:
            df = pd.read_csv(log_file)
            
            # Validate required columns
            required_cols = ['dollar_pnl', 'profit_pct', 'r_multiple', 'position_size', 
                           'entry_price', 'exit_price']
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                print(f"⚠️  Missing columns in LOG_FILE: {missing_cols}")
                return None
            
            # Filter out any rows with missing critical data
            df = df.dropna(subset=['dollar_pnl', 'position_size'])
            
            print(f"  Loaded {len(df)} trades")
            return df
            
        except Exception as e:
            print(f"❌ Error loading LOG_FILE for {portfolio_size} tickers: {e}")
            return None
    
    def calculate_metrics(self, df: pd.DataFrame, portfolio_size: int) -> Dict:
        """
        Calculate comprehensive metrics for a portfolio size.
        
        Args:
            df: DataFrame with trade data
            portfolio_size: Number of tickers in portfolio
            
        Returns:
            Dict with all calculated metrics
        """
        # Basic counts
        total_trades = len(df)
        winning_trades = (df['dollar_pnl'] > 0).sum()
        losing_trades = (df['dollar_pnl'] < 0).sum()
        
        # Dollar P&L metrics
        total_pnl = df['dollar_pnl'].sum()
        avg_pnl_per_trade = df['dollar_pnl'].mean()
        median_pnl_per_trade = df['dollar_pnl'].median()
        std_pnl_per_trade = df['dollar_pnl'].std()
        
        # Return metrics
        avg_return_pct = df['profit_pct'].mean()
        median_return_pct = df['profit_pct'].median()
        avg_r_multiple = df['r_multiple'].mean()
        median_r_multiple = df['r_multiple'].median()
        
        # Win/loss analysis
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        winners = df[df['dollar_pnl'] > 0]
        losers = df[df['dollar_pnl'] < 0]
        
        avg_winner = winners['dollar_pnl'].mean() if len(winners) > 0 else 0
        avg_loser = losers['dollar_pnl'].mean() if len(losers) > 0 else 0
        
        # Profit factor
        total_wins = winners['dollar_pnl'].sum() if len(winners) > 0 else 0
        total_losses = abs(losers['dollar_pnl'].sum()) if len(losers) > 0 else 0
        profit_factor = (total_wins / total_losses) if total_losses > 0 else float('inf')
        
        # Position sizing metrics
        avg_position_size = df['position_size'].mean()
        median_position_size = df['position_size'].median()
        avg_position_value = (df['position_size'] * df['entry_price']).mean()
        
        # Trade duration (if available)
        if 'bars_held' in df.columns:
            avg_bars_held = df['bars_held'].mean()
        else:
            avg_bars_held = np.nan
        
        # Best/worst trades
        best_trade = df['dollar_pnl'].max()
        worst_trade = df['dollar_pnl'].min()
        
        return {
            'portfolio_size': portfolio_size,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            
            # Dollar P&L
            'total_pnl': total_pnl,
            'avg_pnl_per_trade': avg_pnl_per_trade,
            'median_pnl_per_trade': median_pnl_per_trade,
            'std_pnl_per_trade': std_pnl_per_trade,
            
            # Returns
            'avg_return_pct': avg_return_pct,
            'median_return_pct': median_return_pct,
            'avg_r_multiple': avg_r_multiple,
            'median_r_multiple': median_r_multiple,
            
            # Win/Loss
            'avg_winner': avg_winner,
            'avg_loser': avg_loser,
            'profit_factor': profit_factor,
            
            # Position Sizing
            'avg_position_size': avg_position_size,
            'median_position_size': median_position_size,
            'avg_position_value': avg_position_value,
            
            # Other
            'avg_bars_held': avg_bars_held,
            'best_trade': best_trade,
            'worst_trade': worst_trade
        }
    
    def decompose_returns(self) -> Dict:
        """
        Decompose return differences into volume and sizing effects.
        
        Returns:
            Dict with decomposition analysis
        """
        if not self.metrics:
            return {}
        
        decomposition = {}
        
        # Use smallest portfolio as baseline
        baseline_size = self.portfolio_sizes[0]
        baseline = self.metrics[baseline_size]
        
        for size in self.portfolio_sizes:
            if size not in self.metrics:
                continue
            
            current = self.metrics[size]
            
            # Calculate changes vs baseline
            trade_count_change = current['total_trades'] - baseline['total_trades']
            trade_count_pct = (trade_count_change / baseline['total_trades'] * 100) if baseline['total_trades'] > 0 else 0
            
            avg_pnl_change = current['avg_pnl_per_trade'] - baseline['avg_pnl_per_trade']
            avg_pnl_pct = (avg_pnl_change / baseline['avg_pnl_per_trade'] * 100) if baseline['avg_pnl_per_trade'] != 0 else 0
            
            total_pnl_change = current['total_pnl'] - baseline['total_pnl']
            
            # Decompose total change
            # Total change ≈ (baseline avg × Δtrades) + (baseline trades × Δavg) + (Δtrades × Δavg)
            volume_effect = baseline['avg_pnl_per_trade'] * trade_count_change
            sizing_effect = baseline['total_trades'] * avg_pnl_change
            interaction_effect = trade_count_change * avg_pnl_change
            
            # Calculate contribution percentages
            total_change_magnitude = abs(total_pnl_change)
            if total_change_magnitude > 0:
                volume_contribution = abs(volume_effect) / total_change_magnitude * 100
                sizing_contribution = abs(sizing_effect) / total_change_magnitude * 100
            else:
                volume_contribution = 0
                sizing_contribution = 0
            
            decomposition[size] = {
                'baseline_size': baseline_size,
                'current_size': size,
                
                # Changes
                'trade_count_change': trade_count_change,
                'trade_count_pct': trade_count_pct,
                'avg_pnl_change': avg_pnl_change,
                'avg_pnl_pct': avg_pnl_pct,
                'total_pnl_change': total_pnl_change,
                
                # Effects
                'volume_effect': volume_effect,
                'sizing_effect': sizing_effect,
                'interaction_effect': interaction_effect,
                
                # Contributions
                'volume_contribution_pct': volume_contribution,
                'sizing_contribution_pct': sizing_contribution
            }
        
        return decomposition
    
    def generate_report(self) -> str:
        """
        Generate comprehensive text report.
        
        Returns:
            Report text
        """
        lines = []
        
        lines.append("=" * 80)
        lines.append("📊 PORTFOLIO DECOMPOSITION ANALYSIS")
        lines.append("=" * 80)
        lines.append("")
        lines.append(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Period: {self.period}")
        lines.append(f"Portfolio Sizes: {', '.join(map(str, self.portfolio_sizes))}")
        lines.append("")
        lines.append("Question: Why do larger portfolios generate higher returns?")
        lines.append("         Is it more trades (volume) or better per-trade results (sizing)?")
        lines.append("")
        
        # Determine primary driver
        decomp = self.decompose_returns()
        if decomp:
            largest_size = self.portfolio_sizes[-1]
            if largest_size in decomp:
                vol_contrib = decomp[largest_size]['volume_contribution_pct']
                size_contrib = decomp[largest_size]['sizing_contribution_pct']
                
                if vol_contrib > 70:
                    finding = "VOLUME-DRIVEN"
                    explanation = "Returns primarily driven by increased trade frequency"
                elif size_contrib > 70:
                    finding = "SIZING-DRIVEN"
                    explanation = "Returns primarily driven by higher per-trade profits"
                else:
                    finding = "MIXED EFFECT"
                    explanation = "Both trade volume and per-trade quality contribute significantly"
                
                lines.append(f"🎯 PRIMARY FINDING: {finding}")
                lines.append(f"   {explanation}")
                lines.append("")
        
        lines.append("=" * 80)
        lines.append("📈 COMPARISON TABLE")
        lines.append("=" * 80)
        lines.append("")
        
        # Create comparison table
        header = f"{'Size':<6} {'Trades':>8} {'Avg $/Trade':>14} {'Median $/Trade':>16} {'Total P&L':>14} {'Win Rate':>10}"
        lines.append(header)
        lines.append("-" * 80)
        
        for size in self.portfolio_sizes:
            if size not in self.metrics:
                continue
            m = self.metrics[size]
            line = (f"{size:<6} {m['total_trades']:>8} "
                   f"${m['avg_pnl_per_trade']:>13,.0f} "
                   f"${m['median_pnl_per_trade']:>15,.0f} "
                   f"${m['total_pnl']:>13,.0f} "
                   f"{m['win_rate']:>9.1f}%")
            lines.append(line)
        
        lines.append("")
        
        lines.append("=" * 80)
        lines.append("🔍 DECOMPOSITION ANALYSIS")
        lines.append("=" * 80)
        lines.append("")
        
        if decomp:
            baseline_size = self.portfolio_sizes[0]
            
            for i in range(1, len(self.portfolio_sizes)):
                size = self.portfolio_sizes[i]
                if size not in decomp:
                    continue
                
                d = decomp[size]
                
                lines.append(f"{baseline_size} → {size} Tickers:")
                lines.append("-" * 40)
                lines.append(f"  Trade Count Change: {d['trade_count_change']:+d} trades ({d['trade_count_pct']:+.1f}%)")
                lines.append(f"  Avg $/Trade Change: ${d['avg_pnl_change']:+,.0f} ({d['avg_pnl_pct']:+.1f}%)")
                lines.append(f"  Total P&L Change: ${d['total_pnl_change']:+,.0f}")
                lines.append("")
                lines.append(f"  Contribution Breakdown:")
                lines.append(f"    Volume Effect (more trades): ${d['volume_effect']:,.0f} ({d['volume_contribution_pct']:.1f}%)")
                lines.append(f"    Sizing Effect ($/trade diff): ${d['sizing_effect']:,.0f} ({d['sizing_contribution_pct']:.1f}%)")
                
                # Determine primary driver for this comparison
                if d['volume_contribution_pct'] > 70:
                    driver = "VOLUME-DRIVEN: More trading opportunities drive returns"
                elif d['sizing_contribution_pct'] > 70:
                    driver = "SIZING-DRIVEN: Higher per-trade profit drives returns"
                else:
                    driver = "MIXED: Both factors contribute significantly"
                
                lines.append(f"  → {driver}")
                lines.append("")
        
        lines.append("=" * 80)
        lines.append("💰 TRADE QUALITY ANALYSIS")
        lines.append("=" * 80)
        lines.append("")
        lines.append("Does per-trade quality change with portfolio size?")
        lines.append("")
        
        # Quality comparison table
        header = f"{'Metric':<20} " + "  ".join([f"{size:>10}" for size in self.portfolio_sizes])
        lines.append(header)
        lines.append("-" * 80)
        
        metrics_to_compare = [
            ('Win Rate', 'win_rate', '%', '.1f'),
            ('Avg Winner $', 'avg_winner', '$', ',.0f'),
            ('Avg Loser $', 'avg_loser', '$', ',.0f'),
            ('Profit Factor', 'profit_factor', '', '.2f'),
            ('Avg R-Multiple', 'avg_r_multiple', 'R', '.2f'),
            ('Avg % Return', 'avg_return_pct', '%', '.2f')
        ]
        
        for label, key, suffix, fmt in metrics_to_compare:
            values = []
            for size in self.portfolio_sizes:
                if size in self.metrics:
                    val = self.metrics[size][key]
                    if suffix == '$':
                        values.append(f"${val:{fmt}}")
                    elif suffix == 'R':
                        values.append(f"{val:{fmt}}R")
                    elif suffix == '%':
                        values.append(f"{val:{fmt}}%")
                    else:
                        values.append(f"{val:{fmt}}")
                else:
                    values.append("N/A")
            
            line = f"{label:<20} " + "  ".join([f"{v:>10}" for v in values])
            lines.append(line)
        
        lines.append("")
        
        lines.append("=" * 80)
        lines.append("📊 POSITION SIZING CHARACTERISTICS")
        lines.append("=" * 80)
        lines.append("")
        
        for size in self.portfolio_sizes:
            if size not in self.metrics:
                continue
            m = self.metrics[size]
            
            lines.append(f"{size} Tickers:")
            lines.append(f"  Avg Position Size: {m['avg_position_size']:,.0f} shares")
            lines.append(f"  Avg Position Value: ${m['avg_position_value']:,.0f}")
            if not np.isnan(m['avg_bars_held']):
                lines.append(f"  Avg Holding Period: {m['avg_bars_held']:.1f} bars")
            lines.append("")
        
        lines.append("=" * 80)
        lines.append("💡 KEY INSIGHTS & IMPLICATIONS")
        lines.append("=" * 80)
        lines.append("")
        
        if self.metrics and decomp:
            # Calculate key statistics for insights
            smallest = self.metrics[self.portfolio_sizes[0]]
            largest = self.metrics[self.portfolio_sizes[-1]]
            
            avg_pnl_change_pct = ((largest['avg_pnl_per_trade'] - smallest['avg_pnl_per_trade']) / 
                                 smallest['avg_pnl_per_trade'] * 100) if smallest['avg_pnl_per_trade'] != 0 else 0
            
            lines.append("Key Findings:")
            lines.append("")
            
            # 1. Volume vs Sizing conclusion
            largest_decomp = decomp[self.portfolio_sizes[-1]]
            if largest_decomp['volume_contribution_pct'] > 70:
                lines.append("1. VOLUME DOMINATES:")
                lines.append(f"   • Trade count increased {largest_decomp['trade_count_pct']:.0f}% from {smallest['portfolio_size']} to {largest['portfolio_size']} tickers")
                lines.append(f"   • Average per-trade profit stayed relatively stable ({avg_pnl_change_pct:+.1f}% change)")
                lines.append("   • More tickers = more opportunities = more total profit")
                lines.append("")
                
            elif largest_decomp['sizing_contribution_pct'] > 70:
                lines.append("1. SIZING/QUALITY DOMINATES:")
                lines.append(f"   • Average per-trade profit changed significantly ({avg_pnl_change_pct:+.1f}%)")
                lines.append("   • Trade quality differs across portfolio sizes")
                lines.append("   • Concentration vs diversification trade-off present")
                lines.append("")
            else:
                lines.append("1. MIXED EFFECTS:")
                lines.append("   • Both trade volume and per-trade quality contribute")
                lines.append(f"   • Volume contribution: {largest_decomp['volume_contribution_pct']:.0f}%")
                lines.append(f"   • Sizing contribution: {largest_decomp['sizing_contribution_pct']:.0f}%")
                lines.append("")
            
            # 2. Trade quality consistency
            win_rate_range = max([m['win_rate'] for m in self.metrics.values()]) - min([m['win_rate'] for m in self.metrics.values()])
            
            lines.append("2. TRADE QUALITY CONSISTENCY:")
            if win_rate_range < 5:
                lines.append(f"   • Win rate remains consistent ({win_rate_range:.1f}% variation)")
                lines.append("   • Trade quality doesn't deteriorate with portfolio size")
            else:
                lines.append(f"   • Win rate varies by {win_rate_range:.1f}% across portfolio sizes")
                lines.append("   • Trade quality changes with portfolio diversification")
            lines.append("")
            
            # 3. Practical implications
            lines.append("3. TRADING IMPLICATIONS:")
            if largest['total_pnl'] > smallest['total_pnl']:
                lines.append("   • Larger portfolios generated higher absolute returns")
                if largest_decomp['volume_contribution_pct'] > 70:
                    lines.append("   • Recommendation: Maximize ticker universe to capture more opportunities")
                    lines.append("   • Strategy scales well with portfolio size")
                else:
                    lines.append("   • Consider balance between concentration and diversification")
                    lines.append("   • Smaller portfolios may offer higher per-trade quality")
            lines.append("")
        
        lines.append("=" * 80)
        lines.append("📁 DATA SOURCES")
        lines.append("=" * 80)
        lines.append("")
        lines.append(f"Directory: {self.sensitivity_dir}/")
        for size in self.portfolio_sizes:
            log_file = self.find_log_file(size)
            if log_file:
                lines.append(f"  {size} tickers: {os.path.basename(log_file)}")
        lines.append("")
        
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def run(self):
        """Execute complete analysis."""
        print("=" * 80)
        print("📊 PORTFOLIO DECOMPOSITION ANALYSIS")
        print("=" * 80)
        print(f"\nAnalyzing portfolio sizes: {', '.join(map(str, self.portfolio_sizes))}")
        print(f"Period: {self.period}")
        print(f"Directory: {self.sensitivity_dir}")
        print("")
        
        # Load data for each portfolio size
        print("📂 Loading trade data...")
        print("")
        
        for size in self.portfolio_sizes:
            df = self.load_trade_data(size)
            if df is not None:
                self.data[size] = df
                self.metrics[size] = self.calculate_metrics(df, size)
        
        print("")
        
        if not self.metrics:
            print("❌ No data loaded. Cannot perform analysis.")
            print("   Ensure LOG_FILE CSVs exist in the sensitivity directory.")
            return
        
        print(f"✅ Loaded data for {len(self.metrics)} portfolio sizes")
        print("")
        
        # Generate report
        print("📊 Generating decomposition analysis...")
        report = self.generate_report()
        
        # Save report
        output_file = "portfolio_decomposition_analysis.txt"
        with open(output_file, 'w') as f:
            f.write(report)
        
        print(f"✅ Analysis complete!")
        print(f"📄 Report saved to: {output_file}")
        print("")
        
        # Print report to console
        print(report)


def main():
    """Main entry point."""
    analyzer = PortfolioDecompositionAnalyzer(
        sensitivity_dir="backtest_results/portfolio_sensitivity",
        portfolio_sizes=[10, 25, 40],
        period="24mo"
    )
    
    analyzer.run()


if __name__ == "__main__":
    main()
