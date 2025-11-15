#!/bin/bash
#
# Standalone test script for Massive.com data access via AWS CLI
# Tests with historical data (March 2024) that should be accessible
#

set -e  # Exit on error

echo "========================================================================"
echo "MASSIVE.COM AWS CLI TEST - Historical Data"
echo "========================================================================"

# Configure AWS credentials
echo ""
echo "1. Configuring AWS credentials..."
aws configure set aws_access_key_id 572c8693-717a-4773-854f-142470c3f7c1
aws configure set aws_secret_access_key sdv27L3qI5tfOTdU0wT4EQwuqKU6eops
echo "   ✅ Credentials configured"

# Test 1: List files (prove connectivity)
echo ""
echo "2. Testing S3 connectivity - listing files..."
echo "   Command: aws s3 ls s3://flatfiles/ --endpoint-url https://files.massive.com"
echo ""
if aws s3 ls s3://flatfiles/ --endpoint-url https://files.massive.com | head -5; then
    echo ""
    echo "   ✅ Successfully connected to Massive.com S3"
else
    echo ""
    echo "   ❌ Failed to connect"
    exit 1
fi

# Test 2: Download specific historical file
echo ""
echo "3. Downloading historical trades data (2024-03-07)..."
echo "   File: us_stocks_sip/trades_v1/2024/03/2024-03-07.csv.gz"
echo ""

# Remove file if it exists
rm -f 2024-03-07.csv.gz

if aws s3 cp s3://flatfiles/us_stocks_sip/trades_v1/2024/03/2024-03-07.csv.gz . \
    --endpoint-url https://files.massive.com; then
    echo ""
    echo "   ✅ File downloaded successfully"
    
    # Check file size
    FILE_SIZE=$(ls -lh 2024-03-07.csv.gz | awk '{print $5}')
    echo "   File size: $FILE_SIZE"
else
    echo ""
    echo "   ❌ Failed to download file"
    exit 1
fi

# Test 3: Extract and show sample data
echo ""
echo "4. Extracting and displaying sample data..."
echo "   (First 10 lines of CSV)"
echo ""

if command -v gzcat &> /dev/null; then
    # macOS
    gzcat 2024-03-07.csv.gz | head -10
elif command -v zcat &> /dev/null; then
    # Linux
    zcat 2024-03-07.csv.gz | head -10
else
    # Fallback - decompress and read
    gunzip -c 2024-03-07.csv.gz | head -10
fi

echo ""
echo "5. Counting total records in file..."
if command -v gzcat &> /dev/null; then
    RECORD_COUNT=$(gzcat 2024-03-07.csv.gz | wc -l)
elif command -v zcat &> /dev/null; then
    RECORD_COUNT=$(zcat 2024-03-07.csv.gz | wc -l)
else
    RECORD_COUNT=$(gunzip -c 2024-03-07.csv.gz | wc -l)
fi
echo "   Total records: $RECORD_COUNT"

# Summary
echo ""
echo "========================================================================"
echo "✅ TEST PASSED - Massive.com data access confirmed!"
echo "========================================================================"
echo ""
echo "Summary:"
echo "  • S3 connection: ✅ Working"
echo "  • File download: ✅ Working"
echo "  • Data extraction: ✅ Working"
echo "  • File size: $FILE_SIZE"
echo "  • Total records: $RECORD_COUNT"
echo ""
echo "The downloaded file '2024-03-07.csv.gz' contains real market data"
echo "from March 7, 2024 including trades data for all tickers."
echo ""
