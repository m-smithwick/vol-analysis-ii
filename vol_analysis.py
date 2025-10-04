import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
import argparse
import sys
import os
from datetime import datetime
from typing import List, Optional, Dict, Any

def read_ticker_file(filepath: str) -> List[str]:
    """
    Read ticker symbols from a text file (one ticker per line).
    
    Args:
        filepath (str): Path to the file containing ticker symbols
        
    Returns:
        List[str]: List of ticker symbols
    """
    tickers = []
    try:
        with open(filepath, 'r') as f:
            for line in f:
                ticker = line.strip().upper()
                if ticker and not ticker.startswith('#'):  # Skip empty lines and comments
                    tickers.append(ticker)
        return tickers
    except FileNotFoundError:
        print(f"❌ Error: File '{filepath}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error reading file '{filepath}': {str(e)}")
        sys.exit(1)

def generate_analysis_text(ticker: str, df: pd.DataFrame, period: str) -> str:
    """
    Generate text analysis report for a ticker.
    
    Args:
        ticker (str): Stock symbol
        df (pd.DataFrame): Analysis results dataframe
        period (str): Analysis period
        
    Returns:
        str: Formatted analysis report
    """
    output = []
    
    # Header
    phase_counts = df['Phase'].value_counts()
    output.append("=" * 60)
    output.append(f"📊 ACCUMULATION ANALYSIS FOR {ticker.upper()} ({period})")
    output.append("=" * 60)
    
    # Phase distribution
    output.append("\n📈 PHASE DISTRIBUTION:")
    for phase, count in phase_counts.items():
        percentage = (count / len(df)) * 100
        emoji = {"Strong_Accumulation": "🟢", "Moderate_Accumulation": "🟡", 
                "Support_Accumulation": "🟠", "Distribution": "🔴", "Neutral": "⚪"}.get(phase, "⚪")
        output.append(f"  {emoji} {phase}: {count} days ({percentage:.1f}%)")
    
    # Recent signals
    recent_df = df.tail(10)
    recent_signals = recent_df[recent_df['Phase'] != 'Neutral']
    
    output.append(f"\n🔍 RECENT SIGNALS (Last 10 days):")
    if not recent_signals.empty:
        for date, row in recent_signals.iterrows():
            score = row['Accumulation_Score']
            phase = row['Phase']
            price = row['Close']
            volume_ratio = row['Relative_Volume']
            
            signal_strength = "🔥 STRONG" if score >= 7 else "⚡ MODERATE" if score >= 4 else "💡 WEAK"
            output.append(f"  {date.strftime('%Y-%m-%d')}: {phase} - Score: {score:.1f}/10 {signal_strength}")
            output.append(f"    Price: ${price:.2f}, Volume: {volume_ratio:.1f}x average")
    else:
        output.append("  No significant signals in recent trading days")
    
    # Key metrics
    current_price = df['Close'].iloc[-1]
    current_vwap = df['VWAP'].iloc[-1]
    current_support = df['Support_Level'].iloc[-1]
    avg_acc_score = df['Accumulation_Score'].tail(20).mean()
    
    output.append(f"\n📊 KEY METRICS:")
    output.append(f"  Current Price: ${current_price:.2f}")
    output.append(f"  VWAP: ${current_vwap:.2f} ({'Above' if current_price > current_vwap else 'Below'} VWAP)")
    output.append(f"  Support Level: ${current_support:.2f}")
    output.append(f"  20-day Avg Accumulation Score: {avg_acc_score:.1f}/10")
    output.append(f"  Price-Volume Correlation: {df['PriceVolumeCorr'].mean():.3f}")
    
    # Accumulation opportunities
    high_score_days = df[df['Accumulation_Score'] >= 6]
    if not high_score_days.empty:
        output.append(f"\n🎯 HIGH CONFIDENCE ACCUMULATION OPPORTUNITIES:")
        output.append(f"  Found {len(high_score_days)} days with score ≥ 6.0")
        latest_opportunity = high_score_days.tail(1)
        if not latest_opportunity.empty:
            last_date = latest_opportunity.index[0]
            last_score = latest_opportunity['Accumulation_Score'].iloc[0]
            last_price = latest_opportunity['Close'].iloc[0]
            days_ago = (df.index[-1] - last_date).days
            output.append(f"  Most recent: {last_date.strftime('%Y-%m-%d')} (Score: {last_score:.1f}, Price: ${last_price:.2f})")
            output.append(f"  That was {days_ago} trading days ago")
    
    # Signal counts
    signal_counts = {
        'Strong_Buy': df['Strong_Buy'].sum(),
        'Moderate_Buy': df['Moderate_Buy'].sum(), 
        'Sell_Signal': df['Sell_Signal'].sum(),
        'Stealth_Accumulation': df['Stealth_Accumulation'].sum(),
        'Confluence_Signal': df['Confluence_Signal'].sum(),
        'Volume_Breakout': df['Volume_Breakout'].sum()
    }
    
    output.append(f"\n🎯 ENHANCED SIGNAL SUMMARY:")
    output.append("  Visual markers on charts represent:")
    output.append(f"  🟢 Strong Buy Signals: {signal_counts['Strong_Buy']} (Large green dots - Score ≥7, near support, above VWAP)")
    output.append(f"  🟡 Moderate Buy Signals: {signal_counts['Moderate_Buy']} (Medium yellow dots - Score 5-7, divergence signals)")
    output.append(f"  🔴 Sell Signals: {signal_counts['Sell_Signal']} (Red dots - Distribution below VWAP)")
    output.append(f"  💎 Stealth Accumulation: {signal_counts['Stealth_Accumulation']} (Cyan diamonds - High score, low volume)")
    output.append(f"  ⭐ Multi-Signal Confluence: {signal_counts['Confluence_Signal']} (Magenta stars - All indicators aligned)")
    output.append(f"  🔥 Volume Breakouts: {signal_counts['Volume_Breakout']} (Orange triangles - 2.5x+ volume)")
    
    output.append(f"\n📋 ANALYSIS PERIOD: {period}")
    output.append(f"📅 DATE RANGE: {df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')}")
    output.append(f"📊 TOTAL TRADING DAYS: {len(df)}")
    
    return "\n".join(output)

def analyze_ticker(ticker: str, period='6mo', save_to_file=False, output_dir='.', save_chart=False):
    """
    Retrieve and analyze price-volume data for a given ticker symbol.
    
    Args:
        ticker (str): Stock symbol, e.g. 'AAPL' or 'MSFT'
        period (str): Data period, e.g. '1y', '6mo', '5y'
        save_to_file (bool): Whether to save analysis to file instead of printing
        output_dir (str): Directory to save output files
        save_chart (bool): Whether to save chart as PNG file
    """
    # --- Retrieve Data ---
    df = yf.download(ticker, period=period, interval='1d', auto_adjust=True)
    
    # Check if we have MultiIndex columns and flatten if necessary
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)  # Remove the ticker level
    
    df.dropna(inplace=True)
    
    # --- OBV (On-Balance Volume) ---
    df['OBV'] = ( (df['Close'] > df['Close'].shift(1)) * df['Volume']
                - (df['Close'] < df['Close'].shift(1)) * df['Volume'] ).cumsum()
    
    # --- Accumulation/Distribution Line ---
    # Handle division by zero when High == Low
    high_low_diff = df['High'] - df['Low']
    
    # Calculate AD_Multiplier with proper handling of zero divisions
    ad_multiplier = ((df['Close'] - df['Low']) - (df['High'] - df['Close'])) / high_low_diff
    ad_multiplier = ad_multiplier.fillna(0)  # Replace inf/NaN with 0
    ad_multiplier = ad_multiplier.replace([np.inf, -np.inf], 0)  # Replace inf values with 0
    
    df['AD_Multiplier'] = ad_multiplier
    df['AD_Line'] = (df['AD_Multiplier'] * df['Volume']).cumsum()
    
    # --- Rolling correlation between price and volume ---
    df['Return'] = df['Close'].pct_change()
    df['VolChange'] = df['Volume'].pct_change()
    df['PriceVolumeCorr'] = df['Return'].rolling(20).corr(df['VolChange'])
    
    # --- Enhanced Accumulation/Distribution Detection ---
    
    # 1. OBV Trend Analysis
    df['OBV_MA'] = df['OBV'].rolling(window=10).mean()
    df['OBV_Trend'] = df['OBV'] > df['OBV_MA']
    df['Price_MA'] = df['Close'].rolling(window=10).mean()
    df['Price_Trend'] = df['Close'] > df['Price_MA']
    
    # 2. A/D Line Divergence Detection
    df['AD_MA'] = df['AD_Line'].rolling(window=10).mean()
    df['AD_Rising'] = df['AD_Line'] > df['AD_MA']
    df['Price_Rising'] = df['Close'] > df['Close'].shift(5)
    
    # 3. Volume Analysis
    df['Volume_MA'] = df['Volume'].rolling(window=20).mean()
    df['Volume_Spike'] = df['Volume'] > (df['Volume_MA'] * 1.5)  # 50% above average
    df['Relative_Volume'] = df['Volume'] / df['Volume_MA']
    
    # 4. Smart Money Indicators
    df['VWAP'] = (df['Close'] * df['Volume']).cumsum() / df['Volume'].cumsum()
    df['Above_VWAP'] = df['Close'] > df['VWAP']
    
    # 5. Support Level Analysis (using rolling lows)
    df['Support_Level'] = df['Low'].rolling(window=20).min()
    df['Near_Support'] = (df['Close'] - df['Support_Level']) / df['Support_Level'] < 0.05  # Within 5%
    
    # --- Accumulation Signal Generation ---
    accumulation_conditions = [
        # Strong Accumulation: Multiple confirmations
        (df['AD_Rising'] & ~df['Price_Rising'] & df['Volume_Spike'] & df['Above_VWAP']),
        
        # Moderate Accumulation: OBV divergence with volume
        (df['OBV_Trend'] & ~df['Price_Trend'] & (df['Relative_Volume'] > 1.2)),
        
        # Support Accumulation: High volume near support
        (df['Near_Support'] & df['Volume_Spike'] & (df['Close'] > df['Close'].shift(1))),
        
        # Distribution: Price down with high volume
        ((df['Close'] < df['Close'].shift(1)) & df['Volume_Spike'] & ~df['AD_Rising'])
    ]
    
    accumulation_choices = ['Strong_Accumulation', 'Moderate_Accumulation', 'Support_Accumulation', 'Distribution']
    df['Phase'] = pd.Series(pd.Categorical(np.select(accumulation_conditions, accumulation_choices, default='Neutral')))
    
    # --- Confidence Scoring ---
    df['Accumulation_Score'] = 0
    df.loc[df['AD_Rising'] & ~df['Price_Rising'], 'Accumulation_Score'] += 2  # A/D divergence
    df.loc[df['OBV_Trend'] & ~df['Price_Trend'], 'Accumulation_Score'] += 2  # OBV divergence
    df.loc[df['Volume_Spike'], 'Accumulation_Score'] += 1  # Volume spike
    df.loc[df['Above_VWAP'], 'Accumulation_Score'] += 1  # Above VWAP
    df.loc[df['Near_Support'], 'Accumulation_Score'] += 1  # Near support
    
    # Normalize score to 0-10 scale
    df['Accumulation_Score'] = np.clip(df['Accumulation_Score'] * 10 / 7, 0, 10)
    
    # --- Enhanced Signal Generation for Visual Markers ---
    
    # BUY SIGNALS (Green Dots)
    strong_buy_conditions = (
        (df['Accumulation_Score'] >= 7) & 
        df['Near_Support'] & 
        df['Above_VWAP'] & 
        (df['Relative_Volume'] >= 1.2) &
        (df['Relative_Volume'] <= 3.0)  # Not excessive volume
    )
    
    moderate_buy_conditions = (
        (df['Accumulation_Score'] >= 5) & 
        (df['Accumulation_Score'] < 7) &
        (df['AD_Rising'] | df['OBV_Trend']) &
        df['Above_VWAP']
    )
    
    # SELL SIGNALS (Red Dots)
    sell_conditions = (
        (df['Phase'] == 'Distribution') &
        ~df['Above_VWAP'] &
        (df['Relative_Volume'] > 1.5)
    )
    
    # SPECIAL SIGNALS
    stealth_accumulation = (
        (df['Accumulation_Score'] >= 6) &
        (df['Relative_Volume'] < 1.3) &  # Low/normal volume
        (df['AD_Rising'] & ~df['Price_Rising'])  # A/D divergence
    )
    
    confluence_signals = (
        (df['Accumulation_Score'] >= 6) &
        df['Near_Support'] &
        df['Volume_Spike'] &
        df['Above_VWAP'] &
        (df['AD_Rising'] & df['OBV_Trend'])  # Multiple indicators aligned
    )
    
    volume_breakout = (
        (df['Accumulation_Score'] >= 5) &
        (df['Relative_Volume'] > 2.5) &
        (df['Close'] > df['Close'].shift(1)) &
        df['Above_VWAP']
    )
    
    # Create signal flags
    df['Strong_Buy'] = strong_buy_conditions
    df['Moderate_Buy'] = moderate_buy_conditions & ~strong_buy_conditions
    df['Sell_Signal'] = sell_conditions
    df['Stealth_Accumulation'] = stealth_accumulation & ~strong_buy_conditions & ~moderate_buy_conditions
    df['Confluence_Signal'] = confluence_signals
    df['Volume_Breakout'] = volume_breakout & ~strong_buy_conditions
    
    # --- Enhanced Visualization with Accumulation Signals (Optimized for 16" Mac) ---
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 9), sharex=True)
    
    # Top plot: Price with enhanced signal markers
    ax1.plot(df.index, df['Close'], label='Close Price', color='black', linewidth=1.5)
    ax1.plot(df.index, df['VWAP'], label='VWAP', color='purple', alpha=0.7, linestyle='--')
    ax1.plot(df.index, df['Support_Level'], label='Support Level', color='gray', alpha=0.5, linestyle=':')
    
    # --- ENHANCED BUY/SELL SIGNAL MARKERS ---
    
    # STRONG BUY SIGNALS (Large Green Dots)
    strong_buys = df[df['Strong_Buy']]
    if not strong_buys.empty:
        ax1.scatter(strong_buys.index, strong_buys['Close'], color='lime', marker='o', 
                   s=150, label='Strong Buy', zorder=10, edgecolors='darkgreen', linewidth=2)
    
    # MODERATE BUY SIGNALS (Medium Yellow Dots)  
    moderate_buys = df[df['Moderate_Buy']]
    if not moderate_buys.empty:
        ax1.scatter(moderate_buys.index, moderate_buys['Close'], color='gold', marker='o', 
                   s=100, label='Moderate Buy', zorder=9, edgecolors='orange', linewidth=1.5)
    
    # SELL SIGNALS (Large Red Dots)
    sells = df[df['Sell_Signal']]
    if not sells.empty:
        ax1.scatter(sells.index, sells['Close'], color='red', marker='o', 
                   s=120, label='Sell Signal', zorder=10, edgecolors='darkred', linewidth=2)
    
    # STEALTH ACCUMULATION (Diamond Symbols)
    stealth = df[df['Stealth_Accumulation']]
    if not stealth.empty:
        ax1.scatter(stealth.index, stealth['Close'], color='cyan', marker='D', 
                   s=80, label='Stealth Accumulation', zorder=8, alpha=0.8)
    
    # CONFLUENCE SIGNALS (Star Symbols)
    confluence = df[df['Confluence_Signal']]
    if not confluence.empty:
        ax1.scatter(confluence.index, confluence['Close'], color='magenta', marker='*', 
                   s=200, label='Multi-Signal Confluence', zorder=11)
    
    # VOLUME BREAKOUT (Triangle Symbols)
    breakouts = df[df['Volume_Breakout']]
    if not breakouts.empty:
        ax1.scatter(breakouts.index, breakouts['Close'], color='orangered', marker='^', 
                   s=120, label='Volume Breakout', zorder=9, edgecolors='darkred')
    
    ax1.set_ylabel('Price ($)')
    ax1.legend(loc='upper left')
    ax1.set_title(f'{ticker} — Accumulation/Distribution Analysis ({period})')
    ax1.grid(True, alpha=0.3)
    
    # Middle plot: Volume indicators with divergence markers
    ax2.plot(df.index, df['OBV'], label='OBV', color='blue', alpha=0.8)
    ax2.plot(df.index, df['AD_Line'], label='A/D Line', color='orange', alpha=0.8)
    ax2.plot(df.index, df['OBV_MA'], label='OBV MA', color='lightblue', linestyle='--', alpha=0.6)
    ax2.plot(df.index, df['AD_MA'], label='A/D MA', color='moccasin', linestyle='--', alpha=0.6)
    
    # Add divergence markers to volume indicators panel
    if not stealth.empty:
        # Mark stealth accumulation on A/D Line
        ax2.scatter(stealth.index, stealth.index.map(lambda x: df.loc[x, 'AD_Line']), 
                   color='cyan', marker='D', s=60, alpha=0.8, zorder=8)
    
    if not strong_buys.empty:
        # Mark strong buys on OBV
        ax2.scatter(strong_buys.index, strong_buys.index.map(lambda x: df.loc[x, 'OBV']), 
                   color='lime', marker='o', s=80, zorder=9, edgecolors='darkgreen')
    
    ax2.set_ylabel('Volume Indicators')
    ax2.legend(loc='upper left')
    ax2.grid(True, alpha=0.3)
    
    # Bottom plot: Volume and Accumulation Score with threshold markers
    ax3_twin = ax3.twinx()
    
    # Volume bars with color coding
    volume_colors = ['red' if phase == 'Distribution' 
                     else 'darkgreen' if phase == 'Strong_Accumulation'
                     else 'lightgreen' if phase == 'Moderate_Accumulation'
                     else 'yellow' if phase == 'Support_Accumulation'
                     else 'lightgray' for phase in df['Phase']]
    
    ax3.bar(df.index, df['Volume'], color=volume_colors, alpha=0.6, width=1)
    ax3.plot(df.index, df['Volume_MA'], label='Volume MA', color='black', linestyle='-', alpha=0.8)
    
    # Add volume breakout markers
    if not breakouts.empty:
        ax3.scatter(breakouts.index, breakouts.index.map(lambda x: df.loc[x, 'Volume']), 
                   color='orangered', marker='^', s=100, zorder=9, edgecolors='darkred')
    
    ax3.set_ylabel('Volume')
    ax3.legend(loc='upper left')
    
    # Accumulation score line with threshold markers
    ax3_twin.plot(df.index, df['Accumulation_Score'], label='Accumulation Score', 
                  color='purple', linewidth=2)
    
    # Add horizontal threshold lines
    ax3_twin.axhline(y=7, color='lime', linestyle=':', alpha=0.7, label='Strong Buy Threshold')
    ax3_twin.axhline(y=5, color='gold', linestyle=':', alpha=0.7, label='Moderate Buy Threshold')
    ax3_twin.axhline(y=3, color='lightcoral', linestyle=':', alpha=0.7, label='Caution Threshold')
    
    # Mark threshold crossovers
    high_score_points = df[df['Accumulation_Score'] >= 7]
    if not high_score_points.empty:
        ax3_twin.scatter(high_score_points.index, high_score_points['Accumulation_Score'], 
                        color='lime', marker='o', s=50, zorder=10, alpha=0.8)
    
    ax3_twin.set_ylabel('Accumulation Score (0-10)')
    ax3_twin.legend(loc='upper right')
    ax3_twin.set_ylim(0, 10)
    
    ax3.grid(True, alpha=0.3)
    plt.xlabel('Date')
    plt.tight_layout()
    
    # Handle chart display/saving
    if save_chart:
        # Create filename with date range
        start_date = df.index[0].strftime('%Y%m%d')
        end_date = df.index[-1].strftime('%Y%m%d')
        chart_filename = f"{ticker}_{period}_{start_date}_{end_date}_chart.png"
        chart_filepath = os.path.join(output_dir, chart_filename)
        plt.savefig(chart_filepath, dpi=150, bbox_inches='tight')
        print(f"📊 Chart saved: {chart_filename}")
        plt.close()  # Close the figure to free memory
    else:
        plt.show()
    
    # Handle text output
    if save_to_file:
        # Generate filename with date range
        start_date = df.index[0].strftime('%Y%m%d')
        end_date = df.index[-1].strftime('%Y%m%d')
        filename = f"{ticker}_{period}_{start_date}_{end_date}_analysis.txt"
        filepath = os.path.join(output_dir, filename)
        
        # Generate analysis text
        analysis_text = generate_analysis_text(ticker, df, period)
        
        # Write to file
        with open(filepath, 'w') as f:
            f.write(analysis_text)
        
        return df, filepath
    else:
        # --- Enhanced Summary with Accumulation Signals ---
        phase_counts = df['Phase'].value_counts()
        print("\n" + "="*60)
        print(f"📊 ACCUMULATION ANALYSIS FOR {ticker.upper()} ({period})")
        print("="*60)
        
        print("\n📈 PHASE DISTRIBUTION:")
        for phase, count in phase_counts.items():
            percentage = (count / len(df)) * 100
            emoji = {"Strong_Accumulation": "🟢", "Moderate_Accumulation": "🟡", 
                    "Support_Accumulation": "🟠", "Distribution": "🔴", "Neutral": "⚪"}.get(phase, "⚪")
            print(f"  {emoji} {phase}: {count} days ({percentage:.1f}%)")
        
        # Recent accumulation signals (last 10 trading days)
        recent_df = df.tail(10)
        recent_signals = recent_df[recent_df['Phase'] != 'Neutral']
        
        print(f"\n🔍 RECENT SIGNALS (Last 10 days):")
        if not recent_signals.empty:
            for date, row in recent_signals.iterrows():
                score = row['Accumulation_Score']
                phase = row['Phase']
                price = row['Close']
                volume_ratio = row['Relative_Volume']
                
                signal_strength = "🔥 STRONG" if score >= 7 else "⚡ MODERATE" if score >= 4 else "💡 WEAK"
                print(f"  {date.strftime('%Y-%m-%d')}: {phase} - Score: {score:.1f}/10 {signal_strength}")
                print(f"    Price: ${price:.2f}, Volume: {volume_ratio:.1f}x average")
        else:
            print("  No significant signals in recent trading days")
        
        # Key metrics
        current_price = df['Close'].iloc[-1]
        current_vwap = df['VWAP'].iloc[-1]
        current_support = df['Support_Level'].iloc[-1]
        avg_acc_score = df['Accumulation_Score'].tail(20).mean()
        
        print(f"\n📊 KEY METRICS:")
        print(f"  Current Price: ${current_price:.2f}")
        print(f"  VWAP: ${current_vwap:.2f} ({'Above' if current_price > current_vwap else 'Below'} VWAP)")
        print(f"  Support Level: ${current_support:.2f}")
        print(f"  20-day Avg Accumulation Score: {avg_acc_score:.1f}/10")
        print(f"  Price-Volume Correlation: {df['PriceVolumeCorr'].mean():.3f}")
        
        # Accumulation opportunities
        high_score_days = df[df['Accumulation_Score'] >= 6]
        if not high_score_days.empty:
            print(f"\n🎯 HIGH CONFIDENCE ACCUMULATION OPPORTUNITIES:")
            print(f"  Found {len(high_score_days)} days with score ≥ 6.0")
            latest_opportunity = high_score_days.tail(1)
            if not latest_opportunity.empty:
                last_date = latest_opportunity.index[0]
                last_score = latest_opportunity['Accumulation_Score'].iloc[0]
                last_price = latest_opportunity['Close'].iloc[0]
                days_ago = (df.index[-1] - last_date).days
                print(f"  Most recent: {last_date.strftime('%Y-%m-%d')} (Score: {last_score:.1f}, Price: ${last_price:.2f})")
                print(f"  That was {days_ago} trading days ago")
        
        # Enhanced signal counts
        signal_counts = {
            'Strong_Buy': df['Strong_Buy'].sum(),
            'Moderate_Buy': df['Moderate_Buy'].sum(), 
            'Sell_Signal': df['Sell_Signal'].sum(),
            'Stealth_Accumulation': df['Stealth_Accumulation'].sum(),
            'Confluence_Signal': df['Confluence_Signal'].sum(),
            'Volume_Breakout': df['Volume_Breakout'].sum()
        }
        
        print(f"\n🎯 ENHANCED SIGNAL SUMMARY:")
        print("  Visual markers on charts represent:")
        print(f"  🟢 Strong Buy Signals: {signal_counts['Strong_Buy']} (Large green dots - Score ≥7, near support, above VWAP)")
        print(f"  🟡 Moderate Buy Signals: {signal_counts['Moderate_Buy']} (Medium yellow dots - Score 5-7, divergence signals)")
        print(f"  🔴 Sell Signals: {signal_counts['Sell_Signal']} (Red dots - Distribution below VWAP)")
        print(f"  💎 Stealth Accumulation: {signal_counts['Stealth_Accumulation']} (Cyan diamonds - High score, low volume)")
        print(f"  ⭐ Multi-Signal Confluence: {signal_counts['Confluence_Signal']} (Magenta stars - All indicators aligned)")
        print(f"  🔥 Volume Breakouts: {signal_counts['Volume_Breakout']} (Orange triangles - 2.5x+ volume)")
        
        print(f"\n📋 CHART READING GUIDE:")
        print("  • Top Panel: Price action with buy/sell signals")
        print("  • Middle Panel: OBV & A/D Line divergences marked")
        print("  • Bottom Panel: Color-coded volume bars + accumulation score")
        print("  • Purple score line above 7 = Strong accumulation zone")
        print("  • Look for clustering of multiple signal types")
        
        return df

def multi_timeframe_analysis(ticker: str, periods=['1mo', '3mo', '6mo', '1y']):
    """
    Analyze accumulation signals across multiple timeframes for stronger confirmation.
    """
    print(f"\n🔍 MULTI-TIMEFRAME ACCUMULATION ANALYSIS FOR {ticker.upper()}")
    print("="*70)
    
    results = {}
    for period in periods:
        print(f"\n📅 Analyzing {period} timeframe...")
        df_temp = analyze_ticker(ticker, period=period)
        
        # Get recent accumulation metrics
        recent_score = df_temp['Accumulation_Score'].tail(5).mean()
        phase_counts = df_temp['Phase'].value_counts()
        acc_percentage = ((phase_counts.get('Strong_Accumulation', 0) + 
                          phase_counts.get('Moderate_Accumulation', 0) + 
                          phase_counts.get('Support_Accumulation', 0)) / len(df_temp)) * 100
        
        results[period] = {
            'recent_score': recent_score,
            'accumulation_percentage': acc_percentage,
            'total_days': len(df_temp),
            'latest_phase': df_temp['Phase'].iloc[-1]
        }
        
        print(f"  Recent 5-day avg score: {recent_score:.1f}/10")
        print(f"  Accumulation days: {acc_percentage:.1f}% of period")
        print(f"  Latest signal: {df_temp['Phase'].iloc[-1]}")
    
    print(f"\n📋 TIMEFRAME CONSENSUS:")
    avg_score = np.mean([r['recent_score'] for r in results.values()])
    avg_acc_pct = np.mean([r['accumulation_percentage'] for r in results.values()])
    
    consensus_strength = ("🔥 VERY STRONG" if avg_score >= 6 else 
                         "⚡ STRONG" if avg_score >= 4 else 
                         "💡 MODERATE" if avg_score >= 2 else "❄️ WEAK")
    
    print(f"  Multi-timeframe Average Score: {avg_score:.1f}/10 {consensus_strength}")
    print(f"  Average Accumulation Activity: {avg_acc_pct:.1f}%")
    
    return results

def calculate_recent_stealth_score(df: pd.DataFrame) -> Dict[str, float]:
    """
    Calculate recent stealth buying activity score focusing on recent signals.
    
    Args:
        df (pd.DataFrame): Analysis results dataframe
        
    Returns:
        Dict[str, float]: Dictionary with stealth metrics
    """
    # Focus on recent 10 days for stealth activity
    recent_df = df.tail(10)
    
    # 1. Recent Stealth Signal Count (0-4 points)
    recent_stealth_count = recent_df['Stealth_Accumulation'].sum()
    stealth_recency_score = min(recent_stealth_count * 2, 4)  # Max 4 points
    
    # 2. Days since last stealth signal (0-3 points)
    stealth_signals = df[df['Stealth_Accumulation'] == True]
    if not stealth_signals.empty:
        last_stealth_date = stealth_signals.index[-1]
        days_since_stealth = (df.index[-1] - last_stealth_date).days
        # More recent = higher score
        recency_score = max(3 - (days_since_stealth / 3), 0)  # Max 3 points
    else:
        recency_score = 0
    
    # 3. Price containment during stealth period (0-3 points)
    if not stealth_signals.empty:
        # Get price change from first stealth signal to now
        first_stealth_price = stealth_signals['Close'].iloc[0] if len(stealth_signals) > 1 else stealth_signals['Close'].iloc[-1]
        current_price = df['Close'].iloc[-1]
        price_change_pct = ((current_price - first_stealth_price) / first_stealth_price) * 100
        
        # Lower price appreciation = higher score (what user wants)
        if price_change_pct <= 2:  # Less than 2% gain
            containment_score = 3
        elif price_change_pct <= 5:  # Less than 5% gain
            containment_score = 2
        elif price_change_pct <= 10:  # Less than 10% gain
            containment_score = 1
        else:
            containment_score = 0
    else:
        containment_score = 0
    
    # Total stealth score (0-10 scale)
    total_stealth_score = stealth_recency_score + recency_score + containment_score
    
    return {
        'stealth_score': min(total_stealth_score, 10),
        'recent_stealth_count': recent_stealth_count,
        'days_since_stealth': days_since_stealth if not stealth_signals.empty else 999,
        'price_change_pct': price_change_pct if not stealth_signals.empty else 0
    }

def batch_process_tickers(ticker_file: str, period='1y', output_dir='results', save_charts=False):
    """
    Process multiple tickers from a file and save individual analysis reports.
    
    Args:
        ticker_file (str): Path to file containing ticker symbols
        period (str): Analysis period
        output_dir (str): Directory to save output files
        save_charts (bool): Whether to save chart images
    """
    # Read tickers from file
    tickers = read_ticker_file(ticker_file)
    
    if not tickers:
        print("❌ No valid tickers found in file.")
        return
    
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"📁 Created output directory: {output_dir}")
    
    print(f"\n🚀 BATCH PROCESSING {len(tickers)} TICKERS")
    print("="*50)
    print(f"📁 Output directory: {output_dir}")
    print(f"📅 Period: {period}")
    print(f"📊 Save charts: {'Yes' if save_charts else 'No'}")
    print("="*50)
    
    # Track results for summary
    results = []
    errors = []
    
    for i, ticker in enumerate(tickers, 1):
        print(f"\n[{i}/{len(tickers)}] Processing {ticker}...")
        
        try:
            # Analyze ticker with file output
            result = analyze_ticker(
                ticker=ticker,
                period=period,
                save_to_file=True,
                output_dir=output_dir,
                save_chart=save_charts
            )
            
            if isinstance(result, tuple):
                df, filepath = result
                filename = os.path.basename(filepath)
                print(f"✅ {ticker}: Analysis saved to {filename}")
                
                # Collect summary data using new stealth scoring
                phase_counts = df['Phase'].value_counts()
                stealth_metrics = calculate_recent_stealth_score(df)
                
                results.append({
                    'ticker': ticker,
                    'filename': filename,
                    'stealth_score': stealth_metrics['stealth_score'],
                    'recent_stealth_count': stealth_metrics['recent_stealth_count'],
                    'days_since_stealth': stealth_metrics['days_since_stealth'],
                    'price_change_pct': stealth_metrics['price_change_pct'],
                    'total_days': len(df),
                    'strong_signals': df['Strong_Buy'].sum(),
                    'moderate_signals': df['Moderate_Buy'].sum(),
                    'total_stealth_signals': df['Stealth_Accumulation'].sum(),
                    'latest_phase': df['Phase'].iloc[-1]
                })
            
        except Exception as e:
            error_msg = f"Error processing {ticker}: {str(e)}"
            print(f"❌ {error_msg}")
            errors.append({'ticker': ticker, 'error': str(e)})
            continue
    
    # Generate summary report
    if results:
        print(f"\n📋 BATCH PROCESSING SUMMARY")
        print("="*60)
        print(f"✅ Successfully processed: {len(results)}/{len(tickers)} tickers")
        
        if errors:
            print(f"❌ Errors: {len(errors)}")
            for error in errors:
                print(f"   • {error['ticker']}: {error['error']}")
        
        print(f"\n🎯 TOP STEALTH ACCUMULATION CANDIDATES (by recent activity):")
        sorted_results = sorted(results, key=lambda x: x['stealth_score'], reverse=True)
        
        for i, result in enumerate(sorted_results[:10], 1):  # Top 10
            stealth_score = result['stealth_score']
            recent_count = result['recent_stealth_count']
            days_since = result['days_since_stealth']
            price_change = result['price_change_pct']
            total_stealth = result['total_stealth_signals']
            
            score_emoji = "🎯" if stealth_score >= 7 else "💎" if stealth_score >= 5 else "👁️" if stealth_score >= 3 else "💤"
            
            # Display days since or "Recent" if very recent
            recency_text = "Recent" if days_since <= 2 else f"{days_since}d ago" if days_since < 999 else "None"
            
            print(f"  {i:2d}. {result['ticker']:5s} - Stealth: {stealth_score:4.1f}/10 {score_emoji} "
                  f"(Last: {recency_text}, Recent: {recent_count}, Price: {price_change:+4.1f}%, Total: {total_stealth})")
        
        # Generate consolidated summary file
        summary_filename = f"batch_summary_{period}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        summary_filepath = os.path.join(output_dir, summary_filename)
        
        with open(summary_filepath, 'w') as f:
            f.write("BATCH PROCESSING SUMMARY\n")
            f.write("="*60 + "\n\n")
            f.write(f"Processing Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Period: {period}\n")
            f.write(f"Total Tickers: {len(tickers)}\n")
            f.write(f"Successfully Processed: {len(results)}\n")
            f.write(f"Errors: {len(errors)}\n\n")
            
            if errors:
                f.write("ERRORS:\n")
                for error in errors:
                    f.write(f"  • {error['ticker']}: {error['error']}\n")
                f.write("\n")
            
            f.write("RESULTS RANKED BY STEALTH ACCUMULATION SCORE:\n")
            f.write("-" * 90 + "\n")
            f.write(f"{'Rank':<4} {'Ticker':<6} {'Stealth':<7} {'Recent':<6} {'DaysAgo':<7} {'Price%':<7} {'Total':<5} {'File'}\n")
            f.write("-" * 90 + "\n")
            
            for i, result in enumerate(sorted_results, 1):
                days_text = "Recent" if result['days_since_stealth'] <= 2 else f"{result['days_since_stealth']}d" if result['days_since_stealth'] < 999 else "None"
                f.write(f"{i:<4} {result['ticker']:<6} {result['stealth_score']:<7.1f} "
                       f"{result['recent_stealth_count']:<6} {days_text:<7} {result['price_change_pct']:<+7.1f} "
                       f"{result['total_stealth_signals']:<5} {result['filename']}\n")
        
        print(f"\n📄 Summary report saved: {summary_filename}")
        print(f"📁 All files saved to: {os.path.abspath(output_dir)}")
    
    else:
        print(f"\n❌ No tickers were successfully processed.")

def main():
    """
    Main function to handle command-line arguments and run the analysis.
    """
    parser = argparse.ArgumentParser(
        description='📊 Advanced Stock Volume Analysis Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single ticker analysis
  python vol_analysis.py                    # Analyze AAPL with default 1-year period
  python vol_analysis.py TSLA               # Analyze TESLA with 1-year period
  python vol_analysis.py NVDA --period 6mo  # Analyze NVIDIA with 6-month period
  python vol_analysis.py MSFT -p 3mo        # Analyze Microsoft with 3-month period
  python vol_analysis.py GOOGL --multi      # Run multi-timeframe analysis

  # Batch processing from file
  python vol_analysis.py --file stocks.txt                    # Process all tickers in stocks.txt
  python vol_analysis.py -f stocks.txt --period 3mo           # Process with 3-month period
  python vol_analysis.py -f stocks.txt --output-dir results   # Save to 'results' directory
  python vol_analysis.py -f stocks.txt --save-charts          # Also save chart images

Available periods: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
        """
    )
    
    parser.add_argument(
        'ticker', 
        nargs='?', 
        default='AAPL',
        help='Stock ticker symbol (default: AAPL). Ignored if --file is used.'
    )
    
    parser.add_argument(
        '-f', '--file',
        help='Path to file containing ticker symbols (one per line). When used, processes all tickers in batch mode.'
    )
    
    parser.add_argument(
        '-p', '--period',
        default='1y',
        help='Analysis period (default: 1y). Options: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max'
    )
    
    
    parser.add_argument(
        '-o', '--output-dir',
        default='results',
        help='Output directory for batch processing files (default: results)'
    )
    
    parser.add_argument(
        '--save-charts',
        action='store_true',
        help='Save chart images as PNG files (batch mode only)'
    )
    
    parser.add_argument(
        '--multi',
        action='store_true',
        help='Run multi-timeframe analysis instead of single period (single ticker mode only)'
    )
    
    args = parser.parse_args()
    
    try:
        if args.file:
            # Batch processing mode
            print(f"🚀 Starting batch processing from file: {args.file}")
            batch_process_tickers(
                ticker_file=args.file,
                period=args.period,
                output_dir=args.output_dir,
                save_charts=args.save_charts
            )
            print(f"\n✅ Batch processing complete!")
        else:
            # Single ticker mode
            ticker = args.ticker.upper()
            print(f"🚀 Starting analysis for {ticker}...")
            
            if args.multi:
                # Run multi-timeframe analysis
                results = multi_timeframe_analysis(ticker)
            else:
                # Run single period analysis
                df = analyze_ticker(ticker, period=args.period)
                
            print(f"\n✅ Analysis complete for {ticker}!")
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print("Please check your inputs and try again.")
        sys.exit(1)

if __name__ == "__main__":
    main()
