#!/usr/bin/env python3
"""
Quick script to display the most recent batch summary from results_volume directory.
This makes it easy to see the summary without scrolling through all the processing output.
"""

import os
import glob
from pathlib import Path

def show_latest_summary(results_dir='results_volume'):
    """Display the most recent batch summary file."""
    if not os.path.exists(results_dir):
        print(f"❌ Directory '{results_dir}' not found")
        return
    
    # Find all batch summary files
    pattern = os.path.join(results_dir, 'batch_summary_*.txt')
    summary_files = glob.glob(pattern)
    
    if not summary_files:
        print(f"❌ No batch summary files found in '{results_dir}'")
        return
    
    # Get the most recent file
    latest_file = max(summary_files, key=os.path.getmtime)
    
    # Display the content
    print("\n" + "="*70)
    print(f"📋 DISPLAYING: {os.path.basename(latest_file)}")
    print("="*70 + "\n")
    
    with open(latest_file, 'r') as f:
        print(f.read())

if __name__ == "__main__":
    import sys
    results_dir = sys.argv[1] if len(sys.argv) > 1 else 'results_volume'
    show_latest_summary(results_dir)
