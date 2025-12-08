#!/bin/bash
# analyze_ticker.sh - Simple workflow wrapper
TICKER=$1
MONTHS=${2:-24}
CONFIG=${3:-configs/conservative_config.yaml}

# Step 1: Populate cache
python populate_cache_bulk.py --ticker $TICKER --months $MONTHS --use-duckdb

# Step 2: Run analysis with chart (use batch mode to enable file saving)
python vol_analysis.py --file <(echo $TICKER) --period ${MONTHS}mo \
  --config $CONFIG --chart-backend plotly --save-charts \
  --output-dir results_volume

# Step 3: Run backtest
python batch_backtest.py -f <(echo $TICKER) -p ${MONTHS}mo \
  -c $CONFIG -o backtest_results/$TICKER --no-individual-reports

echo "✅ Complete! Results in backtest_results/$TICKER/"
