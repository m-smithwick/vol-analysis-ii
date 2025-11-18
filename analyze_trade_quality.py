"""
Signal Quality Analyzer

Analyzes portfolio trade logs to determine which signal characteristics predict
high-quality trades. Answers questions like:
- What accumulation score threshold maximizes expectancy?
- Which signal types are most reliable?
- Does signal strength correlate with holding period?

Usage:
    python analyze_trade_quality.py PORTFOLIO_TRADE_LOG_*.csv
"""

import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import matplotlib.pyplot as plt


class TradeQualityAnalyzer:
    """Analyzes trade performance based on signal metadata."""
    
    def __init__(self, csv_path: str):
        """
        Load portfolio trade log with signal metadata.
        
        Args:
            csv_path: Path to PORTFOLIO_TRADE_LOG CSV file
        """
        self.csv_path = csv_path
        self.df = pd.read_csv(csv_path)
        
        # Convert date columns
        for col in ['entry_date', 'exit_date']:
            if col in self.df.columns:
                self.df[col] = pd.to_datetime(self.df[col], errors='coerce')
        
        # Ensure numeric columns
        numeric_cols = ['r_multiple', 'profit_pct', 'accumulation_score', 
                       'moderate_buy_score', 'profit_taking_score']
        for col in numeric_cols:
            if col in self.df.columns:
                self.df[col] = pd.to_numeric(self.df[col], errors='coerce')
        
        # Calculate holding days if not present
        if 'holding_days' not in self.df.columns:
            self.df['holding_days'] = (self.df['exit_date'] - self.df['entry_date']).dt.days
        
        print(f"✅ Loaded {len(self.df)} trades from {os.path.basename(csv_path)}")
        print(f"   Tickers: {self.df['ticker'].nunique() if 'ticker' in self.df.columns else 'N/A'}")
        print(f"   Date range: {self.df['entry_date'].min()} to {self.df['exit_date'].max()}")
    
    def analyze_by_score_buckets(
        self, 
        score_col: str = 'accumulation_score',
        buckets: List[Tuple[float, float]] = None
    ) -> pd.DataFrame:
        """
        Analyze performance by score ranges.
        
        Args:
            score_col: Column name for signal score
            buckets: List of (min, max) tuples for score ranges
            
        Returns:
            DataFrame with performance by bucket
        """
        if score_col not in self.df.columns:
            print(f"⚠️  Column '{score_col}' not found in data")
            return pd.DataFrame()
        
        if buckets is None:
            buckets = [(0, 4), (4, 6), (6, 8), (8, 10)]
        
        results = []
        
        for min_score, max_score in buckets:
            mask = (self.df[score_col] >= min_score) & (self.df[score_col] < max_score)
            bucket_trades = self.df[mask].copy()
            
            if len(bucket_trades) == 0:
                continue
            
            wins = bucket_trades[bucket_trades['profit_pct'] > 0]
            losses = bucket_trades[bucket_trades['profit_pct'] <= 0]
            
            win_rate = len(wins) / len(bucket_trades) * 100
            avg_return = bucket_trades['profit_pct'].mean()
            median_return = bucket_trades['profit_pct'].median()
            avg_win = wins['profit_pct'].mean() if len(wins) > 0 else 0
            avg_loss = losses['profit_pct'].mean() if len(losses) > 0 else 0
            expectancy = (win_rate/100 * avg_win) + ((1-win_rate/100) * avg_loss)
            
            results.append({
                'score_range': f'{min_score:.1f} - {max_score:.1f}',
                'trades': len(bucket_trades),
                'win_rate': win_rate,
                'avg_return': avg_return,
                'median_return': median_return,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'expectancy': expectancy,
                'best_return': bucket_trades['profit_pct'].max(),
                'worst_return': bucket_trades['profit_pct'].min()
            })
        
        return pd.DataFrame(results)
    
    def analyze_by_signal_type(self) -> pd.DataFrame:
        """
        Compare performance across signal types.
        
        Returns:
            DataFrame with performance by signal type
        """
        if 'primary_signal' not in self.df.columns:
            print("⚠️  'primary_signal' column not found in data")
            return pd.DataFrame()
        
        # Filter out empty signals
        signals_df = self.df[self.df['primary_signal'].notna() & (self.df['primary_signal'] != '')].copy()
        
        results = []
        
        for signal in signals_df['primary_signal'].unique():
            signal_trades = signals_df[signals_df['primary_signal'] == signal].copy()
            
            if len(signal_trades) == 0:
                continue
            
            wins = signal_trades[signal_trades['profit_pct'] > 0]
            losses = signal_trades[signal_trades['profit_pct'] <= 0]
            
            win_rate = len(wins) / len(signal_trades) * 100
            avg_return = signal_trades['profit_pct'].mean()
            median_return = signal_trades['profit_pct'].median()
            avg_win = wins['profit_pct'].mean() if len(wins) > 0 else 0
            avg_loss = losses['profit_pct'].mean() if len(losses) > 0 else 0
            expectancy = (win_rate/100 * avg_win) + ((1-win_rate/100) * avg_loss)
            avg_holding = signal_trades['holding_days'].mean()
            
            results.append({
                'signal': signal,
                'trades': len(signal_trades),
                'win_rate': win_rate,
                'avg_return': avg_return,
                'median_return': median_return,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'expectancy': expectancy,
                'avg_holding_days': avg_holding,
                'best_return': signal_trades['profit_pct'].max(),
                'worst_return': signal_trades['profit_pct'].min()
            })
        
        df_results = pd.DataFrame(results)
        return df_results.sort_values('expectancy', ascending=False)
    
    def optimize_thresholds(
        self,
        score_col: str = 'accumulation_score',
        thresholds: List[float] = None
    ) -> pd.DataFrame:
        """
        Test different score thresholds to find optimal cutoff.
        
        Args:
            score_col: Column name for signal score
            thresholds: List of threshold values to test
            
        Returns:
            DataFrame with performance at each threshold
        """
        if score_col not in self.df.columns:
            print(f"⚠️  Column '{score_col}' not found in data")
            return pd.DataFrame()
        
        if thresholds is None:
            thresholds = [0, 4.0, 5.0, 6.0, 6.5, 7.0, 7.5, 8.0, 9.0]
        
        results = []
        
        for threshold in thresholds:
            # Filter trades meeting threshold
            filtered = self.df[self.df[score_col] >= threshold].copy()
            
            if len(filtered) == 0:
                continue
            
            wins = filtered[filtered['profit_pct'] > 0]
            losses = filtered[filtered['profit_pct'] <= 0]
            
            win_rate = len(wins) / len(filtered) * 100
            avg_return = filtered['profit_pct'].mean()
            median_return = filtered['profit_pct'].median()
            avg_win = wins['profit_pct'].mean() if len(wins) > 0 else 0
            avg_loss = losses['profit_pct'].mean() if len(losses) > 0 else 0
            expectancy = (win_rate/100 * avg_win) + ((1-win_rate/100) * avg_loss)
            
            results.append({
                'threshold': f'≥{threshold:.1f}',
                'trades': len(filtered),
                'win_rate': win_rate,
                'median_return': median_return,
                'expectancy': expectancy,
                'avg_win': avg_win,
                'avg_loss': avg_loss
            })
        
        return pd.DataFrame(results)
    
    def generate_visualizations(self, output_dir: str = 'backtest_results'):
        """
        Create charts for signal quality analysis.
        
        Args:
            output_dir: Directory to save charts
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # Set matplotlib style
        plt.style.use('default')
        plt.rcParams['axes.grid'] = True
        plt.rcParams['grid.alpha'] = 0.3
        
        # 1. Scatter plot: Accumulation Score vs Return
        if 'accumulation_score' in self.df.columns:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # Color by win/loss
            colors = ['green' if x > 0 else 'red' for x in self.df['profit_pct']]
            
            ax.scatter(self.df['accumulation_score'], self.df['profit_pct'], 
                      c=colors, alpha=0.5, s=30)
            ax.axhline(y=0, color='black', linestyle='--', linewidth=1)
            ax.set_xlabel('Accumulation Score', fontsize=12)
            ax.set_ylabel('Return %', fontsize=12)
            ax.set_title('Signal Strength vs Trade Return', fontsize=14, fontweight='bold')
            ax.grid(True, alpha=0.3)
            
            plt.tight_layout()
            filepath = os.path.join(output_dir, 'signal_score_vs_return.png')
            plt.savefig(filepath, dpi=150, bbox_inches='tight')
            plt.close()
            print(f"  📊 Saved: {filepath}")
        
        # 2. Box plot: Returns by Score Bucket
        if 'accumulation_score' in self.df.columns:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # Create score buckets
            self.df['score_bucket'] = pd.cut(
                self.df['accumulation_score'], 
                bins=[0, 4, 6, 8, 10],
                labels=['0-4', '4-6', '6-8', '8-10']
            )
            
            # Prepare data for box plot
            bucket_data = [
                self.df[self.df['score_bucket'] == label]['profit_pct'].dropna().values
                for label in ['0-4', '4-6', '6-8', '8-10']
            ]
            
            # Box plot using pure matplotlib
            bp = ax.boxplot(bucket_data, labels=['0-4', '4-6', '6-8', '8-10'], 
                           patch_artist=True, showmeans=True)
            
            # Color the boxes
            for patch in bp['boxes']:
                patch.set_facecolor('lightblue')
                patch.set_alpha(0.7)
            
            ax.axhline(y=0, color='red', linestyle='--', linewidth=1)
            ax.set_xlabel('Accumulation Score Bucket', fontsize=12)
            ax.set_ylabel('Return %', fontsize=12)
            ax.set_title('Return Distribution by Signal Strength', fontsize=14, fontweight='bold')
            
            plt.tight_layout()
            filepath = os.path.join(output_dir, 'returns_by_score_bucket.png')
            plt.savefig(filepath, dpi=150, bbox_inches='tight')
            plt.close()
            print(f"  📊 Saved: {filepath}")
        
        # 3. Cumulative P&L: High vs Low Score Trades
        if 'accumulation_score' in self.df.columns and 'exit_date' in self.df.columns:
            fig, ax = plt.subplots(figsize=(12, 6))
            
            # Split into high and low score trades
            high_score = self.df[self.df['accumulation_score'] >= 7].copy()
            low_score = self.df[self.df['accumulation_score'] < 6].copy()
            
            # Sort by date and calculate cumulative P&L
            for subset, label, color in [
                (high_score, 'High Score (≥7)', 'green'),
                (low_score, 'Low Score (<6)', 'red')
            ]:
                if len(subset) > 0:
                    subset_sorted = subset.sort_values('exit_date')
                    cumulative_pnl = subset_sorted['profit_pct'].cumsum()
                    ax.plot(subset_sorted['exit_date'], cumulative_pnl, 
                           label=label, linewidth=2, color=color)
            
            ax.axhline(y=0, color='black', linestyle='--', linewidth=1)
            ax.set_xlabel('Date', fontsize=12)
            ax.set_ylabel('Cumulative Return %', fontsize=12)
            ax.set_title('Cumulative P&L: High vs Low Score Trades', 
                        fontsize=14, fontweight='bold')
            ax.legend(fontsize=11)
            ax.grid(True, alpha=0.3)
            
            plt.tight_layout()
            filepath = os.path.join(output_dir, 'cumulative_pnl_by_score.png')
            plt.savefig(filepath, dpi=150, bbox_inches='tight')
            plt.close()
            print(f"  📊 Saved: {filepath}")
    
    def generate_report(self, output_dir: str = 'backtest_results') -> str:
        """
        Generate comprehensive signal quality report.
        
        Args:
            output_dir: Directory to save report
            
        Returns:
            Report text
        """
        report_lines = []
        
        report_lines.append("=" * 80)
        report_lines.append("🎯 SIGNAL QUALITY ANALYSIS REPORT")
        report_lines.append("=" * 80)
        report_lines.append("")
        report_lines.append(f"Portfolio: {os.path.basename(self.csv_path)}")
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"Total Trades: {len(self.df)}")
        
        if 'ticker' in self.df.columns:
            report_lines.append(f"Tickers: {self.df['ticker'].nunique()}")
        
        report_lines.append("")
        
        # Overall statistics
        wins = self.df[self.df['profit_pct'] > 0]
        overall_win_rate = len(wins) / len(self.df) * 100
        overall_expectancy = (
            (overall_win_rate/100 * wins['profit_pct'].mean()) + 
            ((1-overall_win_rate/100) * self.df[self.df['profit_pct'] <= 0]['profit_pct'].mean())
        )
        
        report_lines.append("📊 OVERALL PERFORMANCE:")
        report_lines.append(f"  Win Rate: {overall_win_rate:.1f}%")
        report_lines.append(f"  Median Return: {self.df['profit_pct'].median():+.2f}%")
        report_lines.append(f"  Expectancy: {overall_expectancy:+.2f}%")
        report_lines.append("")
        
        # Analysis by score buckets
        if 'accumulation_score' in self.df.columns:
            report_lines.append("=" * 80)
            report_lines.append("📈 ACCUMULATION SCORE ANALYSIS")
            report_lines.append("=" * 80)
            report_lines.append("")
            
            bucket_analysis = self.analyze_by_score_buckets()
            
            if not bucket_analysis.empty:
                report_lines.append(f"{'Score Range':<15} {'Trades':<8} {'Win Rate':<10} {'Median':<10} {'Expectancy':<12}")
                report_lines.append("-" * 70)
                
                for _, row in bucket_analysis.iterrows():
                    # Rating
                    if row['expectancy'] > 3.0:
                        rating = "⭐⭐⭐"
                    elif row['expectancy'] > 1.5:
                        rating = "⭐⭐"
                    elif row['expectancy'] > 0:
                        rating = "⭐"
                    else:
                        rating = "❌"
                    
                    report_lines.append(
                        f"{row['score_range']:<15} "
                        f"{row['trades']:<8} "
                        f"{row['win_rate']:<10.1f}% "
                        f"{row['median_return']:<+10.2f}% "
                        f"{row['expectancy']:<+12.2f}% {rating}"
                    )
                
                report_lines.append("")
                
                # Find best bucket
                best_bucket = bucket_analysis.loc[bucket_analysis['expectancy'].idxmax()]
                report_lines.append("💡 KEY FINDING:")
                report_lines.append(f"  Best performing bucket: {best_bucket['score_range']}")
                report_lines.append(f"  • Win Rate: {best_bucket['win_rate']:.1f}%")
                report_lines.append(f"  • Expectancy: {best_bucket['expectancy']:+.2f}%")
                report_lines.append(f"  • Sample: {best_bucket['trades']} trades")
                report_lines.append("")
        
        # Threshold optimization
        if 'accumulation_score' in self.df.columns:
            report_lines.append("=" * 80)
            report_lines.append("🎯 THRESHOLD OPTIMIZATION")
            report_lines.append("=" * 80)
            report_lines.append("")
            
            threshold_analysis = self.optimize_thresholds()
            
            if not threshold_analysis.empty:
                report_lines.append(f"{'Threshold':<12} {'Trades':<8} {'Win Rate':<10} {'Median':<10} {'Expectancy':<12}")
                report_lines.append("-" * 70)
                
                best_expectancy = -999
                best_threshold = None
                
                for _, row in threshold_analysis.iterrows():
                    # Only consider thresholds with sufficient trades
                    if row['trades'] >= 20 and row['expectancy'] > best_expectancy:
                        best_expectancy = row['expectancy']
                        best_threshold = row['threshold']
                    
                    marker = "✅" if row['threshold'] == best_threshold else ""
                    
                    report_lines.append(
                        f"{row['threshold']:<12} "
                        f"{row['trades']:<8} "
                        f"{row['win_rate']:<10.1f}% "
                        f"{row['median_return']:<+10.2f}% "
                        f"{row['expectancy']:<+12.2f}% {marker}"
                    )
                
                report_lines.append("")
                
                if best_threshold:
                    best_row = threshold_analysis[threshold_analysis['threshold'] == best_threshold].iloc[0]
                    report_lines.append("💡 RECOMMENDED THRESHOLD:")
                    report_lines.append(f"  Use {best_threshold} (minimum ≥20 trades)")
                    report_lines.append(f"  • Win Rate: {best_row['win_rate']:.1f}%")
                    report_lines.append(f"  • Expectancy: {best_row['expectancy']:+.2f}%")
                    report_lines.append(f"  • Trades: {best_row['trades']}")
                    report_lines.append("")
        
        # Signal type analysis
        if 'primary_signal' in self.df.columns:
            report_lines.append("=" * 80)
            report_lines.append("🚀 SIGNAL TYPE ANALYSIS")
            report_lines.append("=" * 80)
            report_lines.append("")
            
            signal_analysis = self.analyze_by_signal_type()
            
            if not signal_analysis.empty:
                report_lines.append(f"{'Signal':<25} {'Trades':<8} {'Win Rate':<10} {'Median':<10} {'Expectancy':<12}")
                report_lines.append("-" * 80)
                
                for _, row in signal_analysis.iterrows():
                    # Rating
                    if row['expectancy'] > 3.0 and row['win_rate'] > 65:
                        rating = "⭐⭐⭐"
                    elif row['expectancy'] > 1.5 and row['win_rate'] > 55:
                        rating = "⭐⭐"
                    elif row['expectancy'] > 0:
                        rating = "⭐"
                    else:
                        rating = "❌"
                    
                    report_lines.append(
                        f"{row['signal']:<25} "
                        f"{row['trades']:<8} "
                        f"{row['win_rate']:<10.1f}% "
                        f"{row['median_return']:<+10.2f}% "
                        f"{row['expectancy']:<+12.2f}% {rating}"
                    )
                
                report_lines.append("")
                
                # Best signal
                best_signal = signal_analysis.iloc[0]
                report_lines.append("💡 MOST RELIABLE SIGNAL:")
                report_lines.append(f"  {best_signal['signal']}")
                report_lines.append(f"  • Win Rate: {best_signal['win_rate']:.1f}%")
                report_lines.append(f"  • Expectancy: {best_signal['expectancy']:+.2f}%")
                report_lines.append(f"  • Trades: {best_signal['trades']}")
                report_lines.append("")
        
        # Recommendations
        report_lines.append("=" * 80)
        report_lines.append("💡 ACTION ITEMS")
        report_lines.append("=" * 80)
        report_lines.append("")
        
        report_lines.append("Based on this analysis:")
        report_lines.append("")
        
        if 'accumulation_score' in self.df.columns and not threshold_analysis.empty:
            best_row = threshold_analysis[threshold_analysis['threshold'] == best_threshold].iloc[0]
            report_lines.append(f"1. FILTER BY SCORE: Only take trades with accumulation_score {best_threshold}")
            report_lines.append(f"   Expected improvement: {best_row['expectancy']:+.2f}% expectancy vs {overall_expectancy:+.2f}% overall")
            report_lines.append("")
        
        if 'primary_signal' in self.df.columns and not signal_analysis.empty:
            top_3 = signal_analysis.head(3)
            report_lines.append("2. PRIORITIZE SIGNALS:")
            for i, (_, row) in enumerate(top_3.iterrows(), 1):
                report_lines.append(f"   {i}. {row['signal']} ({row['expectancy']:+.2f}% expectancy)")
            report_lines.append("")
        
        report_lines.append("3. MONITOR PERFORMANCE:")
        report_lines.append("   • Track win rate by score bucket monthly")
        report_lines.append("   • Re-run this analysis quarterly to verify thresholds")
        report_lines.append("   • Test new thresholds on paper trades first")
        report_lines.append("")
        
        report_lines.append("=" * 80)
        report_lines.append("")
        
        return "\n".join(report_lines)


def main():
    """Main function for signal quality analysis."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Analyze signal quality from portfolio trade log'
    )
    
    parser.add_argument(
        'csv_file',
        help='Path to PORTFOLIO_TRADE_LOG CSV file'
    )
    
    parser.add_argument(
        '-o', '--output-dir',
        default='backtest_results',
        help='Output directory for reports and charts (default: backtest_results)'
    )
    
    parser.add_argument(
        '--no-charts',
        action='store_true',
        help='Skip generating visualizations'
    )
    
    args = parser.parse_args()
    
    # Validate input file
    if not os.path.exists(args.csv_file):
        print(f"❌ Error: File not found: {args.csv_file}")
        sys.exit(1)
    
    print(f"\n🎯 SIGNAL QUALITY ANALYZER")
    print("=" * 80)
    print("")
    
    # Load and analyze
    analyzer = TradeQualityAnalyzer(args.csv_file)
    
    # Generate visualizations
    if not args.no_charts:
        print("\n📊 Generating visualizations...")
        try:
            analyzer.generate_visualizations(args.output_dir)
        except Exception as e:
            print(f"⚠️  Chart generation failed: {e}")
            print("   Continuing with report...")
    
    # Generate report
    print("\n📝 Generating analysis report...")
    report = analyzer.generate_report(args.output_dir)
    
    # Save report
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_filename = f"SIGNAL_QUALITY_ANALYSIS_{timestamp}.txt"
    report_path = os.path.join(args.output_dir, report_filename)
    
    with open(report_path, 'w') as f:
        f.write(report)
    
    print(f"  ✅ Saved: {report_path}")
    
    # Print report to console
    print("\n" + report)
    
    print(f"\n✅ Analysis complete!")
    print(f"📁 Results saved to: {os.path.abspath(args.output_dir)}")


if __name__ == "__main__":
    main()
