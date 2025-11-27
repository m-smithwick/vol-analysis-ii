# Ticker Lists Directory

This directory contains various ticker list files used by the volume analysis system.

## Files

- **sector_mappings.csv** - Stock-to-sector ETF mappings (see below)
- **sector_etfs.txt** - List of all valid sector ETF symbols
- **stocks.txt** - Default stock list for analysis
- **ibd*.txt** - IBD (Investor's Business Daily) stock lists
- **Other .txt files** - Various custom ticker lists

---

## Sector Mappings Configuration

### File: `sector_mappings.csv`

This CSV file maps individual stock tickers to their sector ETF symbols. The regime filter (`regime_filter.py`) uses these mappings to determine which sector ETF's 50-day moving average to check for each stock.

### Format

```csv
ticker,sector_etf,sector_name
AAPL,XLK,Technology
JPM,XLF,Financials
...
```

**Columns:**
- `ticker` - Stock symbol (case-insensitive, will be converted to uppercase)
- `sector_etf` - Sector ETF symbol (must be one of the 11 valid sector ETFs listed below)
- `sector_name` - Human-readable sector name (for reference only, not used by code)

### Valid Sector ETFs

The following sector ETF symbols are valid:

| ETF Symbol | Sector Name |
|------------|-------------|
| XLK | Technology |
| XLF | Financials |
| XLV | Healthcare |
| XLE | Energy |
| XLY | Consumer Discretionary |
| XLP | Consumer Staples |
| XLI | Industrials |
| XLU | Utilities |
| XLRE | Real Estate |
| XLB | Materials |
| XLC | Communication Services |
| SPY | Market Index (special case) |

### Adding New Stocks

To add a new stock mapping:

1. Open `sector_mappings.csv` in a text editor or Excel
2. Add a new row with the ticker, sector ETF, and sector name
3. Save the file
4. The changes will be loaded automatically next time you run the system

**Example:**
```csv
NVDA,XLK,Technology
```

### Modifying Existing Mappings

Simply edit the corresponding row in the CSV file and save. Changes take effect on next module load.

### Default Behavior

If a stock is not found in the mappings file, it will default to **SPY** (S&P 500 index) for regime checks. This is a conservative approach that uses the broad market regime.

### Validation

The system validates sector ETF symbols when loading the file:
- Invalid sector ETFs will be logged as warnings and skipped
- Malformed rows will be logged as errors and skipped
- The system will continue to operate with valid mappings only

### Example Entries

```csv
ticker,sector_etf,sector_name
AAPL,XLK,Technology
MSFT,XLK,Technology
GOOGL,XLK,Technology
JPM,XLF,Financials
BAC,XLF,Financials
JNJ,XLV,Healthcare
XOM,XLE,Energy
AMZN,XLY,Consumer Discretionary
WMT,XLP,Consumer Staples
CAT,XLI,Industrials
NEE,XLU,Utilities
AMT,XLRE,Real Estate
LIN,XLB,Materials
NFLX,XLC,Communication Services
SPY,SPY,Market Index
```

### Troubleshooting

**Problem:** "Sector mappings file not found" warning

**Solution:** Ensure `sector_mappings.csv` exists in the `ticker_lists/` directory.

---

**Problem:** Invalid sector ETF warning for a ticker

**Solution:** Check that the sector_etf column uses one of the valid ETF symbols listed above (case-insensitive).

---

**Problem:** Stock not being assigned correct sector

**Solution:** 
1. Check that the ticker is spelled correctly in the CSV
2. Verify the CSV file saved properly (no extra spaces, correct format)
3. Restart your analysis (mappings are loaded at module initialization)

---

## Other Ticker Lists

The other `.txt` files in this directory contain simple lists of ticker symbols (one per line) for various purposes:

- **stocks.txt** - Main list used by batch analysis scripts
- **ibd.txt** - IBD-focused stock lists
- **sector_etfs.txt** - All sector ETF symbols

These can be used with the `--file` parameter in various scripts.

---

## Maintenance

When adding new stocks to the system:

1. Add the ticker to the appropriate `.txt` list file (e.g., `stocks.txt`)
2. Add the sector mapping to `sector_mappings.csv`
3. Run cache population to download historical data

This ensures the system has both the data and the proper sector classification.
