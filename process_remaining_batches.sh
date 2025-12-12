#!/bin/bash
# Process remaining ticker batches (03-12) for momentum screening

for i in {03..12}; do
    batch_num=$(printf "%02d" $i)
    echo ""
    echo "======================================================================"
    echo "PROCESSING BATCH $batch_num"
    echo "======================================================================"
    
    # Populate cache
    echo "Step 1: Populating cache..."
    python populate_cache_bulk.py --ticker-files ticker_lists/massive_batch_${batch_num}.txt --months 24 --use-duckdb
    
    if [ $? -ne 0 ]; then
        echo "ERROR: Cache population failed for batch $batch_num"
        exit 1
    fi
    
    # Run momentum screening
    echo ""
    echo "Step 2: Running momentum screening..."
    python momentum_screener.py --file ticker_lists/massive_batch_${batch_num}.txt --output screener/batch${batch_num}_momentum.csv
    
    if [ $? -ne 0 ]; then
        echo "ERROR: Momentum screening failed for batch $batch_num"
        exit 1
    fi
    
    echo ""
    echo "✅ Batch $batch_num complete!"
    echo ""
done

echo ""
echo "======================================================================"
echo "ALL BATCHES COMPLETE!"
echo "======================================================================"
echo ""
echo "Results saved to screener/ directory:"
ls -lh screener/batch*_momentum.csv
