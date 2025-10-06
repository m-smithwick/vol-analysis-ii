# 📊 Advanced Stock Volume Analysis Tool

A sophisticated Python tool for analyzing stock accumulation and distribution patterns using advanced volume indicators and visual signal detection.

## 🚀 Features

### **Complete Entry & Exit Signal System**
- **6 Entry Signal Types**: Strong Buy, Moderate Buy, Stealth Accumulation, Multi-Signal Confluence, Volume Breakouts, Sell Avoidance
- **5 Exit Signal Types**: Profit Taking, Distribution Warning, Sell Signals, Momentum Exhaustion, Stop Loss Triggers
- **Advanced Technical Indicators**: OBV divergence, A/D Line analysis, VWAP positioning, support level detection
- **Dual Scoring System**: Entry Score (0-10) + Exit Score (1-10) with threshold-based alerts and visual markers

### **Professional Visualization**
- **Entry Signal Markers**: 🟢 Green dots (Strong Buy), 🟡 Yellow dots (Moderate Buy), 💎 Cyan diamonds (Stealth), ⭐ Magenta stars (Confluence), 🔥 Orange triangles (Breakouts)
- **Exit Signal Markers**: 🟠 Orange dots (Profit Taking), ⚠️ Gold squares (Distribution Warning), 🔴 Red dots (Sell), 💜 Purple X's (Momentum Exhaustion), 🛑 Dark red triangles (Stop Loss)
- **Multi-panel Charts**: Price action with all signals, Volume indicators with divergences, Volume bars with dual scoring
- **Enhanced Threshold Lines**: Visual zones at levels 2, 4, 6, 7, and 8 for both entry and exit scoring

### **Command Line Interface**
- **Flexible Usage**: Analyze any stock ticker with customizable time periods
- **Batch Processing**: Process multiple tickers from files with individual output reports
- **Multi-timeframe Analysis**: Cross-reference signals across different time horizons
- **Screen Optimized**: Charts sized perfectly for 16-inch Mac displays

### **Smart Data Caching System (NEW)**
- **Local Cache**: Stores Yahoo Finance data locally to avoid redundant downloads
- **Incremental Updates**: Only downloads new data since last cache update
- **Automatic Management**: Creates and maintains cache automatically
- **Cache Information**: View cached tickers and their status
- **Selective Clearing**: Clear cache for specific tickers or entire cache
- **Force Refresh**: Override cache when fresh data is needed

### **Batch Processing & File Output**
- **File Input**: Process ticker lists from text files (one ticker per line)
- **Individual Reports**: Generate separate analysis files for each ticker
- **Stealth Ranking**: Focus on recent stealth accumulation over historical averages
- **Chart Export**: Optional PNG chart generation for batch processing
- **Summary Reports**: Consolidated rankings with stealth activity scores

## 📦 Installation

### Requirements
```bash
pip install pandas numpy yfinance matplotlib argparse
```

### Python Version
- Python 3.7 or higher required
- Tested on Python 3.12

## 🔧 Usage

### Basic Usage
```bash
# Analyze AAPL with default 1-year period
python vol_analysis.py

# Analyze specific ticker
python vol_analysis.py TSLA

# Custom time period
python vol_analysis.py NVDA --period 6mo

# Short form
python vol_analysis.py MSFT -p 3mo
```

### Batch Processing (NEW)
```bash
# Process all tickers from a file
python vol_analysis.py --file stocks.txt

# Batch processing with custom period and output directory
python vol_analysis.py -f stocks.txt --period 3mo --output-dir results

# Include chart images for all tickers
python vol_analysis.py -f stocks.txt --save-charts

# Full batch processing example
python vol_analysis.py -f watchlist.txt -p 6mo -o analysis_output --save-charts
```

### Data Caching Options (NEW)
```bash
# View cache information
python vol_analysis.py --cache-info

# Clear cache for specific ticker
python vol_analysis.py --clear-cache AAPL

# Clear entire cache
python vol_analysis.py --clear-cache all

# Force refresh (ignore cache)
python vol_analysis.py AAPL --force-refresh

# Force refresh in batch processing
python vol_analysis.py -f stocks.txt --force-refresh
```

### Advanced Options
```bash
# Multi-timeframe analysis (single ticker)
python vol_analysis.py GOOGL --multi

# Get help
python vol_analysis.py --help
```

### Ticker File Format
Create a text file with one ticker symbol per line:
```
AAPL
MSFT
GOOGL
TSLA
NVDA
# Comments start with # and are ignored
AMZN
```

### Batch Processing Output
All files are saved to the `results/` directory by default.

**Individual Analysis Files**: `{TICKER}_{PERIOD}_{STARTDATE}_{ENDDATE}_analysis.txt`
- Example: `results/AAPL_6mo_20240404_20241003_analysis.txt`

**Chart Files** (when `--save-charts` used): `{TICKER}_{PERIOD}_{STARTDATE}_{ENDDATE}_chart.png`
- Example: `results/AAPL_6mo_20240404_20241003_chart.png`

**Summary Report**: `batch_summary_{PERIOD}_{TIMESTAMP}.txt`
- Example: `results/batch_summary_6mo_20241004_122312.txt`
- Contains ranked list of all processed tickers

### Available Time Periods
- `1d`, `5d`, `1mo`, `3mo`, `6mo`, `1y`, `2y`, `5y`, `10y`, `ytd`, `max`

## 📈 Chart Interpretation Guide

### **Three-Panel Layout**

#### **Top Panel: Price Action with Signals**
- **Black line**: Stock price
- **Purple dashed line**: VWAP (Volume Weighted Average Price)
- **Gray dotted line**: Support level (20-day rolling low)
- **Signal markers**: See signal types below

#### **Middle Panel: Volume Indicators**
- **Blue line**: On-Balance Volume (OBV)
- **Orange line**: Accumulation/Distribution Line
- **Dashed lines**: Moving averages of OBV and A/D Line
- **Markers**: Divergence signals overlaid on indicators

#### **Bottom Panel: Volume & Accumulation Score**
- **Color-coded bars**: Volume with phase identification
- **Purple line**: Accumulation confidence score (0-10 scale)
- **Horizontal threshold lines**: Buy zones at scores 3, 5, and 7

## 🎯 Complete Signal System Explained

### **ENTRY SIGNALS**

#### **🟢 Strong Buy Signals (Large Green Dots)**
**Criteria**: Score ≥7, near support, above VWAP, moderate volume (1.2-3.0x average)
- **Meaning**: Highest confidence accumulation opportunity
- **Action**: Prime entry point for accumulation

#### **🟡 Moderate Buy Signals (Medium Yellow Dots)**
**Criteria**: Score 5-7, divergence signals, above VWAP
- **Meaning**: Good accumulation opportunity with some risk
- **Action**: Consider entry with position sizing

#### **💎 Stealth Accumulation (Cyan Diamonds)**
**Criteria**: Score ≥6, low volume (<1.3x), A/D divergence
- **Meaning**: Hidden accumulation without price movement
- **Action**: Early accumulation opportunity

#### **⭐ Multi-Signal Confluence (Magenta Stars)**
**Criteria**: Multiple indicators aligned (Score ≥6, support, volume, VWAP, divergences)
- **Meaning**: Strongest possible accumulation signal
- **Action**: High-conviction entry point

#### **🔥 Volume Breakout (Orange Triangles)**
**Criteria**: Score ≥5, volume >2.5x average, price up, above VWAP
- **Meaning**: Accumulation with momentum breakout
- **Action**: Momentum-based entry

### **EXIT SIGNALS**

#### **🟠 Profit Taking (Orange Dots)**
**Criteria**: New 20-day highs, high volume (>1.8x), above VWAP, but accumulation waning (<4)
- **Meaning**: Take profits on strength before momentum fades
- **Action**: Consider taking partial profits

#### **⚠️ Distribution Warning (Gold Squares)**
**Criteria**: Distribution phase, below VWAP, above average volume, declining A/D line
- **Meaning**: Early warning signs of institutional selling
- **Action**: Prepare exit strategy, monitor closely

#### **🔴 Sell Signals (Red Dots)**
**Criteria**: Distribution phase, below VWAP, breaking support, declining OBV and A/D line
- **Meaning**: Strong institutional selling pressure detected
- **Action**: Consider exit or avoid entry

#### **💜 Momentum Exhaustion (Purple X's)**
**Criteria**: Price rising but volume declining, low accumulation, extended above MA
- **Meaning**: Volume/price divergence indicating exhaustion
- **Action**: Prepare for potential reversal

#### **🛑 Stop Loss Triggers (Dark Red Triangles)**
**Criteria**: Below support, high volume breakdown, below VWAP and 5-day MA
- **Meaning**: Urgent exit signal for risk management
- **Action**: Immediate exit consideration

## 📊 Technical Indicators Used

### **On-Balance Volume (OBV)**
- Cumulative volume indicator showing money flow
- **Bullish**: OBV rising while price flat/declining
- **Bearish**: OBV falling while price rising

### **Accumulation/Distribution Line**
- Measures the cumulative flow of money into/out of security
- Uses intraday price action relative to close
- **Formula**: `((Close - Low) - (High - Close)) / (High - Low) * Volume`

### **Volume Weighted Average Price (VWAP)**
- Average price weighted by volume
- **Above VWAP**: Generally bullish positioning
- **Below VWAP**: Generally bearish positioning

### **Support Level Detection**
- 20-day rolling minimum low price
- **Near Support**: Within 5% of support level
- **Significance**: Potential bounce/accumulation zone

### **Dual Scoring System**

#### **Entry Score (0-10 scale)**
Points awarded for:
- **A/D Line divergence**: +2 points
- **OBV trend divergence**: +2 points  
- **Volume spike**: +1 point
- **Above VWAP**: +1 point
- **Near support**: +1 point

#### **Exit Score (1-10 scale)**
Points awarded for:
- **Distribution phase**: +2 points
- **Below VWAP**: +1.5 points
- **Below support**: +2 points
- **High volume (>2.5x)**: +1.5 points
- **Declining A/D line**: +1 point
- **Declining OBV**: +1 point
- **Low accumulation**: +1 point

**Final scores**: Normalized and clipped to respective scales

## 🎯 Stealth Accumulation Ranking System (NEW)

The batch processing feature uses a **Recent Stealth Activity Score** instead of traditional averages to identify stocks with fresh institutional buying that haven't broken out yet.

### **Stealth Scoring Algorithm (0-10 scale)**

**Recent Stealth Signals** (0-4 points):
- Counts stealth accumulation signals in the last 10 trading days
- Multiple recent signals = higher score

**Signal Recency** (0-3 points):
- Days since the last stealth accumulation signal
- More recent signals = higher score
- Recent (≤2 days) gets maximum points

**Price Containment** (0-3 points):
- Price appreciation during the stealth accumulation period
- Lower price gains = higher score (ideal for stealth buying)
- ≤2% gain = 3 points, ≤5% gain = 2 points, ≤10% gain = 1 point

### **Batch Processing Ranking Display**
```
🎯 TOP STEALTH ACCUMULATION CANDIDATES (by recent activity):
   1. AMZN  - Stealth:  8.0/10 🎯 (Last: Recent, Recent: 1, Price: +0.0%, Total: 1)
   2. AI    - Stealth:  5.3/10 💎 (Last: Recent, Recent: 1, Price: +9.5%, Total: 1)
   3. MSFT  - Stealth:  0.0/10 💤 (Last: None, Recent: 0, Price: +0.0%, Total: 0)
```

**Explanation**:
- **Stealth Score**: Recent activity score (0-10)
- **Last**: Days since last stealth signal ("Recent" = ≤2 days)
- **Recent**: Count of stealth signals in last 10 days
- **Price**: Price change during stealth accumulation period
- **Total**: Total stealth signals across entire analysis period

### **Stealth Score Emojis**
- 🎯 **7-10**: High recent stealth activity - prime candidates
- 💎 **5-7**: Moderate recent stealth activity
- 👁️ **3-5**: Low recent stealth activity
- 💤 **0-3**: No meaningful recent stealth activity

## 🔍 Multi-Timeframe Analysis

Use the `--multi` flag to analyze across multiple timeframes:

```bash
python vol_analysis.py AAPL --multi
```

**Analyzes**: 1-month, 3-month, 6-month, and 1-year periods
**Output**: Consensus strength rating and average accumulation activity

**Interpretation**:
- **🔥 VERY STRONG**: Average score ≥6 across timeframes
- **⚡ STRONG**: Average score ≥4 across timeframes  
- **💡 MODERATE**: Average score ≥2 across timeframes
- **❄️ WEAK**: Average score <2 across timeframes

## 📋 Sample Output Interpretation

```
🎯 ENTRY SIGNAL SUMMARY:
  🟢 Strong Buy Signals: 2 (Large green dots - Score ≥7, near support, above VWAP)
  🟡 Moderate Buy Signals: 5 (Medium yellow dots - Score 5-7, divergence signals)
  💎 Stealth Accumulation: 3 (Cyan diamonds - High score, low volume)
  ⭐ Multi-Signal Confluence: 1 (Magenta stars - All indicators aligned)
  🔥 Volume Breakouts: 0 (Orange triangles - 2.5x+ volume)

🚪 EXIT SIGNAL SUMMARY:
  🟠 Profit Taking: 1 (Orange dots - New highs with waning accumulation)
  ⚠️ Distribution Warning: 0 (Gold squares - Early distribution signs)
  🔴 Sell Signals: 0 (Red dots - Strong distribution below VWAP)
  💜 Momentum Exhaustion: 0 (Purple X's - Rising price, declining volume)
  🛑 Stop Loss Triggers: 0 (Dark red triangles - Support breakdown)

📊 CURRENT EXIT ANALYSIS:
  Current Exit Score: 2.3/10 - ✅ LOW
  Recent Exit Activity (5 days): No
  🎯 RECOMMENDATION: LOW RISK - Normal monitoring, position appears stable
```

**Analysis**: This shows a stock in accumulation phase with multiple entry signals, minimal exit pressure, and one profit-taking opportunity. Low exit score indicates position is stable for continued holding.

## 🛠️ Troubleshooting

### **Common Issues**

#### **"No module named 'yfinance'"**
```bash
pip install yfinance
```

#### **Charts too small/large**
- Chart size optimized for 16-inch Mac displays
- Modify `figsize=(12, 9)` in code if needed

#### **Emoji warnings in plots**
- Cosmetic font warnings, doesn't affect functionality
- Charts will display properly despite warnings

#### **Invalid ticker symbol**
```
❌ Error analyzing XYZ: No data found, symbol may be delisted
```
- Verify ticker symbol is correct and actively traded
- Use proper exchange format (e.g., `BRK-A` not `BRKA`)

### **Performance Tips**
- Use shorter periods (`3mo`, `6mo`) for faster analysis
- Daily intervals only - simplified for closing price analysis
- Longer periods provide more reliable signals

## 📖 Example Analysis Workflow

1. **Start with overview**: `python vol_analysis.py TICKER`
2. **Check recent activity**: Look at "Recent Signals" section
3. **Identify key levels**: Note current price vs VWAP and support
4. **Spot accumulation zones**: Look for clustering of green/yellow signals
5. **Confirm with indicators**: Check OBV and A/D line trends
6. **Multi-timeframe confirmation**: Run with `--multi` flag
7. **Plan entry**: Use confluence signals for highest-probability entries

## 🎨 Chart Color Guide

### **Entry Signals**
| Color | Meaning |
|-------|---------|
| 🟢 Lime/Dark Green | Strong buy signals |
| 🟡 Gold | Moderate buy signals |
| 💎 Cyan | Stealth accumulation |
| ⭐ Magenta | Multi-signal confluence |
| 🔥 Orange Red | Volume breakouts |

### **Exit Signals**
| Color | Meaning |
|-------|---------|
| 🟠 Orange | Profit taking opportunities |
| ⚠️ Gold (Square) | Distribution warnings |
| 🔴 Red | Strong sell signals |
| 💜 Purple | Momentum exhaustion |
| 🛑 Dark Red | Stop loss triggers |

### **Chart Elements**
| Color | Meaning |
|-------|---------|
| 🟦 Blue | OBV trend line |
| 🟧 Orange | A/D Line |
| 🟣 Purple | VWAP |
| 🟢 Green Line | Entry/Accumulation score |
| 🔴 Red Line | Exit score |
| ⚫ Black | Price line |
| 🔘 Gray | Support level |

## 💡 Tips for Best Results

### **Signal Quality**
- **Look for clusters**: Multiple signals in same area = higher confidence
- **Confirm with volume**: Best signals have supporting volume patterns
- **Check timeframe**: Longer periods give more reliable signals
- **Watch divergences**: OBV/A/D rising while price flat = accumulation

### **Complete Trading System**
- **Entry Strategy**: Use entry signals (🟢🟡💎⭐🔥) for position initiation
- **Exit Strategy**: Monitor exit signals (🟠⚠️🔴💜🛑) for position management
- **Dual Scoring**: Entry score >7 = strong buy, Exit score >6 = high risk
- **Signal Transitions**: Watch for Entry→Hold→Exit phase changes

### **Risk Management**
- **Position sizing**: Use entry signal strength for initial position sizing
- **Profit taking**: Act on 🟠 profit taking signals for partial exits
- **Stop losses**: Respond to 🛑 stop loss triggers immediately
- **Early warnings**: Prepare exit strategy on ⚠️ distribution warnings
- **Market context**: Consider overall market conditions

### **Trading Strategies**
- **Conservative**: Only trade ⭐ confluence entries, exit on ⚠️ warnings
- **Moderate**: Trade 🟢 strong buy signals, exit on 🔴 sell signals
- **Aggressive**: Include 🟡 moderate buy signals, use 💜 exhaustion exits
- **Risk-Averse**: Exit immediately on 🛑 stop loss triggers

### **Exit Score Interpretation**
- **8-10**: 🚨 URGENT - Consider immediate exit or tight stop loss
- **6-8**: ⚠️ HIGH RISK - Reduce position size significantly
- **4-6**: 💡 MODERATE RISK - Monitor closely, consider partial exit
- **2-4**: ✅ LOW RISK - Normal monitoring, position appears stable
- **1-2**: 🟢 MINIMAL RISK - Position looks healthy for continued holding

## 📚 Further Reading

- **On-Balance Volume**: [Investopedia OBV](https://www.investopedia.com/terms/o/onbalancevolume.asp)
- **Accumulation/Distribution**: [A/D Line Explanation](https://www.investopedia.com/terms/a/accumulationdistribution.asp)
- **VWAP Trading**: [Volume Weighted Average Price](https://www.investopedia.com/terms/v/vwap.asp)
- **Volume Analysis**: [Volume and Price Analysis](https://www.investopedia.com/articles/technical/02/010702.asp)

## 📄 License

This tool is provided for educational and research purposes. Not financial advice.

---

**Happy Trading! 📈**
