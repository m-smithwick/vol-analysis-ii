#!/usr/bin/env python3
"""
Part 1: Massive.com File Listing Test
Tests connectivity and lists available files WITHOUT downloading.
Writes results to massive_file_list.txt
"""

import boto3
from botocore.config import Config
from datetime import datetime

print("="*70)
print("MASSIVE.COM PART 1: FILE LISTING TEST")
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

# Test listing day_aggs files date below
prefix = 'us_stocks_sip/day_aggs_v1/2025/11/'
bucket = 'flatfiles'

print(f"\n2. Listing files from Massive.com...")
print(f"   Bucket: {bucket}")
print(f"   Prefix: {prefix}")

# Initialize paginator
paginator = s3.get_paginator('list_objects_v2')

# Write to file
output_file = 'massive_file_list.txt'
file_count = 0
total_size = 0

try:
    with open(output_file, 'w') as f:
        f.write("="*70 + "\n")
        f.write("MASSIVE.COM FILE LISTING\n")
        f.write("="*70 + "\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Bucket: {bucket}\n")
        f.write(f"Prefix: {prefix}\n")
        f.write("="*70 + "\n\n")
        
        # List all files
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            if 'Contents' in page:
                for obj in page['Contents']:
                    key = obj['Key']
                    size = obj['Size']
                    size_mb = size / (1024 * 1024)
                    modified = obj['LastModified']
                    
                    f.write(f"{key}\n")
                    f.write(f"  Size: {size:,} bytes ({size_mb:.2f} MB)\n")
                    f.write(f"  Modified: {modified}\n")
                    f.write("\n")
                    
                    file_count += 1
                    total_size += size
                    
                    # Print to console too
                    if file_count <= 5 or file_count % 5 == 0:
                        print(f"   Found: {key.split('/')[-1]} ({size_mb:.2f} MB)")
        
        # Write summary
        f.write("="*70 + "\n")
        f.write("SUMMARY\n")
        f.write("="*70 + "\n")
        f.write(f"Total files: {file_count}\n")
        f.write(f"Total size: {total_size:,} bytes ({total_size/(1024*1024):.2f} MB)\n")
        f.write(f"Average file size: {total_size/file_count if file_count > 0 else 0:,.0f} bytes\n")
    
    print(f"\n3. Results:")
    print(f"   ✅ Found {file_count} files")
    print(f"   ✅ Total size: {total_size/(1024*1024):.2f} MB")
    print(f"   ✅ Listing saved to: {output_file}")
    
    print("\n" + "="*70)
    print("✅ PART 1 TEST PASSED - File listing successful!")
    print("="*70)
    print(f"\nCheck '{output_file}' for complete file listing.")
    print("\nNote: This test only LISTS files. Download testing is in Part 2.")
    
except Exception as e:
    print(f"\n   ❌ Error: {e}")
    import traceback
    traceback.print_exc()
