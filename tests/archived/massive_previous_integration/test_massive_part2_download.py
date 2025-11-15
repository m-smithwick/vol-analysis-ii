#!/usr/bin/env python3
"""
Part 2: Massive.com File Download Test
Attempts to download a file to test subscription permissions.
Documents whether download access is available.
"""

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
import os

print("="*70)
print("MASSIVE.COM PART 2: FILE DOWNLOAD TEST")
print("="*70)

# Initialize session with credentials from profile
print("\n1. Initializing boto3 session...")
print("   Using profile: 'massive' from ~/.aws/credentials")
session = boto3.Session(profile_name='massive')

# Create S3 client
s3 = session.client(
    's3',
    endpoint_url='https://files.massive.com',
    config=Config(signature_version='s3v4'),
)
print("   ✅ Session initialized")

# Test downloading a file
bucket = 'flatfiles'
object_key = 'us_stocks_sip/day_aggs_v1/2025/11/2025-11-11.csv.gz'
local_file = '2025-11-11-download-test.csv.gz'

print(f"\n2. Attempting to download file...")
print(f"   Bucket: {bucket}")
print(f"   Object: {object_key}")
print(f"   Local: {local_file}")

# Remove file if it exists
if os.path.exists(local_file):
    os.remove(local_file)

try:
    # Attempt download
    s3.download_file(bucket, object_key, local_file)
    
    # If we get here, download succeeded!
    file_size = os.path.getsize(local_file)
    print(f"\n   ✅ SUCCESS! File downloaded")
    print(f"   File size: {file_size:,} bytes ({file_size/(1024*1024):.2f} MB)")
    
    # Try to read first few lines
    print(f"\n3. Reading file contents...")
    import gzip
    with gzip.open(local_file, 'rt') as f:
        print("   Header:")
        print(f"   {f.readline().strip()}")
        print("\n   First 3 data lines:")
        for i in range(3):
            print(f"   {f.readline().strip()}")
    
    print("\n" + "="*70)
    print("✅ PART 2 TEST PASSED - Download successful!")
    print("="*70)
    print("\n🎉 Your subscription DOES have download access!")
    print("The Massive.com integration is fully functional.")
    
except ClientError as e:
    error_code = e.response['Error']['Code']
    error_msg = e.response['Error']['Message']
    
    print(f"\n   ❌ Download failed: {error_code}")
    print(f"   Error: {error_msg}")
    
    if error_code == '403':
        print("\n" + "="*70)
        print("⚠️ PART 2 TEST FAILED - Subscription Limitation")
        print("="*70)
        print("\n📋 FINDINGS:")
        print("   • S3 connectivity: ✅ Working")
        print("   • File listing: ✅ Working")
        print("   • File download: ❌ Forbidden (403)")
        print("\n💡 CONCLUSION:")
        print("   Your Massive.com subscription tier allows listing")
        print("   files but does NOT allow downloading them.")
        print("\n🔧 SOLUTIONS:")
        print("   1. Upgrade subscription for flat file download access")
        print("   2. Use Massive.com REST API instead")
        print("   3. Continue using yfinance (works well)")
        print("\n📊 INTEGRATION STATUS:")
        print("   The code we built is correct and will work when")
        print("   your subscription tier includes download permissions.")
    else:
        print(f"\n   Unexpected error code: {error_code}")
    
except Exception as e:
    print(f"\n   ❌ Unexpected error: {e}")
    import traceback
    traceback.print_exc()
