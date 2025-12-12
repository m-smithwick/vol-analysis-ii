#!/usr/bin/env python3
"""
Consolidate momentum screening results from all batch files.

This script reads all batch screening results and creates:
1. A master file with all results
2. A perfect candidates file (passed all filters)
3. A summary report
"""

import pandas as pd
from pathlib import Path
import glob

def consolidate_results():
    """Consolidate all batch screening results."""
    
    print("="*70)
    print("MOMENTUM SCREENING RESULTS CONSOLIDATION")
    print("="*70)
    print()
    
    # Find all batch result files
    result_files = sorted(glob.glob("screener/batch*_momentum.csv"))
    
    if not result_files:
        print("❌ No batch result files found in screener/ directory")
        return
    
    print(f"📂 Found {len(result_files)} batch result files")
    print()
    
    # Load and concatenate all results
    all_dfs = []
    for file in result_files:
        batch_num = file.split('batch')[1].split('_')[0]
        df = pd.read_csv(file)
        print(f"   Batch {batch_num}: {len(df)} tickers screened")
        all_dfs.append(df)
    
    # Combine all results
    master_df = pd.concat(all_dfs, ignore_index=True)
    
    print()
    print("="*70)
    print("SUMMARY STATISTICS")
    print("="*70)
    print()
    
    # Calculate statistics
    total_screened = len(master_df)
    passed_all = master_df['passes_all_filters'].sum()
    velocity_increasing = master_df['velocity_increasing'].sum()
    vcp_active = master_df['vcp_active'].sum()
    above_200sma = master_df['above_200sma'].sum()
    liquidity_ok = master_df['liquidity_ok'].sum()
    
    print(f"Total tickers screened:     {total_screened:,}")
    print(f"Passed ALL filters:         {passed_all:,} ({passed_all/total_screened*100:.2f}%)")
    print()
    print("Individual Filter Results:")
    print(f"  RS Velocity Increasing:   {velocity_increasing:,} ({velocity_increasing/total_screened*100:.1f}%)")
    print(f"  VCP Active:               {vcp_active:,} ({vcp_active/total_screened*100:.1f}%)")
    print(f"  Above 200-day SMA:        {above_200sma:,} ({above_200sma/total_screened*100:.1f}%)")
    print(f"  Liquidity OK (>500k):     {liquidity_ok:,} ({liquidity_ok/total_screened*100:.1f}%)")
    
    # Save master file
    master_file = "screener/all_momentum_results.csv"
    master_df.to_csv(master_file, index=False)
    print()
    print(f"💾 Master file saved: {master_file}")
    
    # Extract perfect candidates
    perfect_candidates = master_df[master_df['passes_all_filters'] == True].copy()
    
    if not perfect_candidates.empty:
        # Sort by RS velocity (descending)
        perfect_candidates = perfect_candidates.sort_values('rs_slope_10d', ascending=False)
        
        perfect_file = "screener/perfect_candidates.csv"
        perfect_candidates.to_csv(perfect_file, index=False)
        
        print(f"⭐ Perfect candidates file: {perfect_file}")
        print()
        print("="*70)
        print(f"🎯 PERFECT CANDIDATES ({len(perfect_candidates)} tickers)")
        print("="*70)
        print()
        
        # Display perfect candidates
        for i, row in perfect_candidates.iterrows():
            print(f"{row['ticker']:6s} - RS Velocity: {row['rs_slope_10d']:.6f}")
            print(f"       Price: ${row['current_price']:.2f} (+{row['price_vs_sma_pct']:.1f}% above 200 SMA)")
            print(f"       VCP Contraction: {row['contraction_ratio']:.2f} ({row['contraction_ratio']*100:.0f}% of avg range)")
            print(f"       Volume: {row['avg_volume_20d']/1e6:.2f}M avg")
            print()
    else:
        print()
        print("ℹ️  No tickers passed all filters")
        print("   Most common failure: VCP not active (no tight consolidation)")
    
    # Top RS Velocity candidates (even if don't pass all filters)
    print()
    print("="*70)
    print("TOP 20 BY RS VELOCITY (regardless of filters)")
    print("="*70)
    print()
    
    top_rs = master_df.nlargest(20, 'rs_slope_10d')[
        ['ticker', 'rs_slope_10d', 'velocity_increasing', 'vcp_active', 
         'above_200sma', 'liquidity_ok', 'passes_all_filters']
    ]
    
    print(top_rs.to_string(index=False))
    
    # Summary report
    summary_file = "screener/screening_summary.txt"
    with open(summary_file, 'w') as f:
        f.write("MOMENTUM SCREENING SUMMARY\n")
        f.write("="*70 + "\n\n")
        f.write(f"Total Tickers Screened: {total_screened:,}\n")
        f.write(f"Perfect Candidates: {passed_all:,}\n\n")
        f.write("Filter Results:\n")
        f.write(f"  RS Velocity Increasing: {velocity_increasing:,} ({velocity_increasing/total_screened*100:.1f}%)\n")
        f.write(f"  VCP Active: {vcp_active:,} ({vcp_active/total_screened*100:.1f}%)\n")
        f.write(f"  Above 200 SMA: {above_200sma:,} ({above_200sma/total_screened*100:.1f}%)\n")
        f.write(f"  Liquidity OK: {liquidity_ok:,} ({liquidity_ok/total_screened*100:.1f}%)\n\n")
        
        if not perfect_candidates.empty:
            f.write("PERFECT CANDIDATES:\n")
            f.write("-"*70 + "\n")
            for i, row in perfect_candidates.iterrows():
                f.write(f"\n{row['ticker']}\n")
                f.write(f"  RS Velocity: {row['rs_slope_10d']:.6f}\n")
                f.write(f"  Price: ${row['current_price']:.2f} (+{row['price_vs_sma_pct']:.1f}% above 200 SMA)\n")
                f.write(f"  VCP Contraction: {row['contraction_ratio']:.2f}\n")
                f.write(f"  Volume: {row['avg_volume_20d']/1e6:.2f}M avg\n")
    
    print()
    print(f"📄 Summary report saved: {summary_file}")
    print()
    print("="*70)
    print("✅ CONSOLIDATION COMPLETE")
    print("="*70)


if __name__ == "__main__":
    consolidate_results()
