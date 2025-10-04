# 📊 Advanced Stock Volume Analysis Tool

A sophisticated Python tool for analyzing stock accumulation and distribution patterns using advanced volume indicators and visual signal detection.

## 🚀 Features

### **Enhanced Accumulation Detection**
- **6 Different Signal Types**: Strong Buy, Moderate Buy, Sell, Stealth Accumulation, Multi-Signal Confluence, Volume Breakouts
- **Advanced Technical Indicators**: OBV divergence, A/D Line analysis, VWAP positioning, support level detection
- **Confidence Scoring**: 0-10 scale with threshold-based alerts and visual markers

### **Professional Visualization**
- **Color-coded Signal Markers**: 🟢 Green dots (Strong Buy), 🟡 Yellow dots (Moderate Buy), 🔴 Red dots (Sell)
- **Special Symbol Detection**: 💎 Diamonds (Stealth), ⭐ Stars (Confluence), 🔥 Triangles (Breakouts)
- **Multi-panel Charts**: Price action, Volume indicators with divergences, Volume bars with accumulation score
- **Threshold Lines**: Visual buy/sell zones at confidence levels 3, 5, and 7

### **Command Line Interface**
- **Flexible Usage**: Analyze any stock ticker with customizable time periods
- **Multi-timeframe Analysis**: Cross-reference signals across different time horizons
- **Screen Optimized**: Charts sized perfectly for 16-inch Mac displays

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

### Advanced Options
```bash
# Multi-timeframe analysis
python vol_analysis.py GOOGL --multi

# Custom interval (for shorter periods)
python vol_analysis.py AAPL -p 1mo -i 1h

# Get help
python vol_analysis.py --help
```

### Available Time Periods
- `1d`, `5d`, `1mo`, `3mo`, `6mo`, `1y`, `2y`, `5y`, `10y`, `ytd`, `max`

### Available Intervals
- `1m`, `2m`, `5m`, `15m`, `30m`, `60m`, `90m`, `1h`, `1d`, `5d`, `1wk`, `1mo`, `3mo`

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

## 🎯 Signal Types Explained

### **🟢 Strong Buy Signals (Large Green Dots)**
**Criteria**: Score ≥7, near support, above VWAP, moderate volume (1.2-3.0x average)
- **Meaning**: Highest confidence accumulation opportunity
- **Action**: Prime entry point for accumulation

### **🟡 Moderate Buy Signals (Medium Yellow Dots)**
**Criteria**: Score 5-7, divergence signals, above VWAP
- **Meaning**: Good accumulation opportunity with some risk
- **Action**: Consider entry with position sizing

### **🔴 Sell Signals (Large Red Dots)**
**Criteria**: Distribution phase, below VWAP, high volume
- **Meaning**: Institutional selling pressure detected
- **Action**: Consider exit or avoid entry

### **💎 Stealth Accumulation (Cyan Diamonds)**
**Criteria**: Score ≥6, low volume (<1.3x), A/D divergence
- **Meaning**: Hidden accumulation without price movement
- **Action**: Early accumulation opportunity

### **⭐ Multi-Signal Confluence (Magenta Stars)**
**Criteria**: Multiple indicators aligned (Score ≥6, support, volume, VWAP, divergences)
- **Meaning**: Strongest possible accumulation signal
- **Action**: High-conviction entry point

### **🔥 Volume Breakout (Orange Triangles)**
**Criteria**: Score ≥5, volume >2.5x average, price up, above VWAP
- **Meaning**: Accumulation with momentum breakout
- **Action**: Momentum-based entry

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

### **Confidence Scoring Algorithm**
Points awarded for:
- **A/D Line divergence**: +2 points
- **OBV trend divergence**: +2 points  
- **Volume spike**: +1 point
- **Above VWAP**: +1 point
- **Near support**: +1 point

**Final score**: Normalized to 0-10 scale

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
🎯 ENHANCED SIGNAL SUMMARY:
  🟢 Strong Buy Signals: 2 (Large green dots - Score ≥7, near support, above VWAP)
  🟡 Moderate Buy Signals: 5 (Medium yellow dots - Score 5-7, divergence signals)
  🔴 Sell Signals: 0 (Red dots - Distribution below VWAP)
  💎 Stealth Accumulation: 3 (Cyan diamonds - High score, low volume)
  ⭐ Multi-Signal Confluence: 1 (Magenta stars - All indicators aligned)
  🔥 Volume Breakouts: 0 (Orange triangles - 2.5x+ volume)
```

**Analysis**: This shows a stock in accumulation phase with multiple buy signals, no sell pressure, and one high-confidence confluence signal.

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
- Avoid intraday intervals (`1m`, `5m`) for daily analysis
- Use `1d` interval for most stock analysis

## 📖 Example Analysis Workflow

1. **Start with overview**: `python vol_analysis.py TICKER`
2. **Check recent activity**: Look at "Recent Signals" section
3. **Identify key levels**: Note current price vs VWAP and support
4. **Spot accumulation zones**: Look for clustering of green/yellow signals
5. **Confirm with indicators**: Check OBV and A/D line trends
6. **Multi-timeframe confirmation**: Run with `--multi` flag
7. **Plan entry**: Use confluence signals for highest-probability entries

## 🎨 Chart Color Guide

| Color | Meaning |
|-------|---------|
| 🟢 Lime/Dark Green | Strong accumulation signals |
| 🟡 Gold/Orange | Moderate accumulation signals |  
| 🔴 Red/Dark Red | Distribution/sell signals |
| 💎 Cyan | Stealth accumulation |
| ⭐ Magenta | Multi-signal confluence |
| 🔥 Orange Red | Volume breakouts |
| 🟦 Blue | OBV trend line |
| 🟧 Orange | A/D Line |
| 🟣 Purple | VWAP and accumulation score |
| ⚫ Black | Price line |
| 🔘 Gray | Support level |

## 💡 Tips for Best Results

### **Signal Quality**
- **Look for clusters**: Multiple signals in same area = higher confidence
- **Confirm with volume**: Best signals have supporting volume patterns
- **Check timeframe**: Longer periods give more reliable signals
- **Watch divergences**: OBV/A/D rising while price flat = accumulation

### **Risk Management**
- **Position sizing**: Use signal strength for position sizing
- **Stop losses**: Place below recent support levels
- **Confirmation**: Wait for multiple signal types to align
- **Market context**: Consider overall market conditions

### **Entry Strategies**
- **Conservative**: Only trade ⭐ confluence signals
- **Moderate**: Trade 🟢 strong buy signals
- **Aggressive**: Include 🟡 moderate buy signals
- **Avoid**: Never trade against 🔴 sell signals

## 📚 Further Reading

- **On-Balance Volume**: [Investopedia OBV](https://www.investopedia.com/terms/o/onbalancevolume.asp)
- **Accumulation/Distribution**: [A/D Line Explanation](https://www.investopedia.com/terms/a/accumulationdistribution.asp)
- **VWAP Trading**: [Volume Weighted Average Price](https://www.investopedia.com/terms/v/vwap.asp)
- **Volume Analysis**: [Volume and Price Analysis](https://www.investopedia.com/articles/technical/02/010702.asp)

## 📄 License

This tool is provided for educational and research purposes. Not financial advice.

---

**Happy Trading! 📈**
