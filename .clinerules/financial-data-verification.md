# Financial Data Verification Standards

This trading system manages real monetary investments. Data accuracy and verification protocols are CRITICAL.

## 🚨 Core Principle

**FILESYSTEM METADATA ≠ DATA DATE**

- File modification time = when file was written to disk
- Data date = the market date the data represents
- These can be YEARS apart in historical data systems
- ALWAYS use semantic dates (filenames, content) NOT filesystem timestamps

## 📊 Time-Series Data Verification Protocol

### Before Making ANY Claim About Data Availability

You MUST perform these verification steps:

#### 1. Check Actual Date Range (By Filename)

```bash
# For date-named files (YYYY-MM-DD format)
ls -1 directory/*.csv.gz | sort | head -5    # Oldest dates
ls -1 directory/*.csv.gz | sort | tail -5    # Newest dates

# Count total coverage
ls -1 directory/*.csv.gz | wc -l
```

**NEVER use:**
```bash
ls -lt directory/    # WRONG: Sorts by modification time
ls -ltr directory/   # WRONG: Reverse modification time
```

#### 2. Verify Claims by Testing

Before stating "data not available" or "returns 403":
- Attempt to download the claimed unavailable date
- Check if cache already contains that date
- Review test results to see what dates were actually tested
- Don't extrapolate from limited testing

#### 3. Sample Content for Date Verification

If dates aren't in filenames:
```bash
# Check first and last records in time-series files
zcat file.csv.gz | head -2
zcat file.csv.gz | tail -2
```

## 🎯 MASSIVE Data System Specifics

### File Structure
```
massive_cache/YYYY-MM-DD.csv.gz
```

- Filename = market date
- File modification time = download time
- These are independent values

### Verifying Most Recent Data

```bash
# CORRECT: Sort by filename (market date)
ls massive_cache/*.csv.gz | sort | tail -1

# WRONG: Sort by modification time
ls -lt massive_cache/ | head -1
```

### Daily Cache Update Pattern

The bulk population script may process dates out of order:
- Download order ≠ chronological order
- Batch processing creates files in unpredictable sequence
- File timestamps DO NOT indicate data recency

## 📝 Documentation Review Standards

### When Documentation Claims Data Limitations

If docs say:
- "Data not available after [date]"
- "Returns 403 for recent dates"
- "Only historical data accessible"

**REQUIRED verification:**

1. **Check actual cached data:**
   ```bash
   ls -1 massive_cache/*.csv.gz | sort | tail -20
   ```

2. **Review test coverage:**
   - What dates did tests actually try?
   - Did tests attempt recent dates?
   - Or only historical dates?

3. **Attempt to access "unavailable" data:**
   - Try downloading claimed unavailable dates
   - Check for actual error messages
   - Distinguish between "tested and failed" vs "assumed unavailable"

### Red Flags in Documentation

Watch for circular reasoning:
- "We tested March 2024 → March 2024 works → Assume newer dates don't work"
- This is NOT evidence that recent dates are unavailable

## 🔬 Testing Requirements

### Before Claiming Data Availability Issues

You MUST:

1. Test at least 3 different date ranges:
   - Historical (6+ months old)
   - Recent (current month)
   - Multiple points in between

2. Document actual error messages:
   - Don't say "doesn't work"
   - Show actual HTTP code, error text
   - Distinguish 403, 404, timeout, etc.

3. Verify cache state:
   - Check what's already cached
   - Don't claim data unavailable if it's cached

## 💰 Financial Impact Awareness

### Why This Matters

- Wrong data date = Wrong backtest results
- Wrong backtest = Bad strategy
- Bad strategy = Lost money
- Simple filesystem confusion = Potential financial loss

### Zero Tolerance Errors

These errors are UNACCEPTABLE:
- Using `ls -lt` to determine data recency
- Assuming data unavailable without testing
- Extrapolating from limited test coverage
- Confusing download time with data date

## ✅ Verification Checklist

Before responding about data availability:

- [ ] Used semantic dates (filename/content) not filesystem metadata
- [ ] Sorted time-series data chronologically by date value
- [ ] Tested multiple date ranges including recent
- [ ] Verified cache contents by examining filenames
- [ ] Documented actual error messages if claiming failures
- [ ] Checked test coverage of existing documentation
- [ ] Double-checked assumptions with actual commands

## 🎓 Learning from Mistakes

### The November 2025 Error

**What Happened:**
- Used `ls -lt` which showed 2024-09-16 files first
- Confused file modification time with market data date
- Concluded September 2024 was most recent data
- Actually had November 2025 data cached

**Root Cause:**
- Conflated filesystem metadata with semantic data dates
- Failed to verify assumptions
- Trusted documentation without testing

**Prevention:**
- This rules file
- Always sort by semantic date
- Test claims before accepting them

## 📚 Additional Resources

### Useful Commands

```bash
# Find date gaps in sequential data
ls -1 massive_cache/*.csv.gz | sort | awk -F'[/.]' '{print $2}' | uniq

# Check date range coverage
ls -1 massive_cache/*.csv.gz | head -1 && ls -1 massive_cache/*.csv.gz | tail -1

# Verify no duplicates
ls -1 massive_cache/*.csv.gz | sort | uniq -c | grep -v "   1 "
```

### File Naming Best Practices

For any time-series data:
- Use ISO 8601 format: YYYY-MM-DD
- This ensures correct alphabetical = chronological sorting
- Makes `sort` command work as expected

## 🔒 Mandatory Reviews

When working with:
- Cache systems
- Historical data
- Time-series files
- Financial data

You MUST review this rules file and follow all protocols.

**No exceptions. Money is at stake.**
