#!/usr/bin/env python3
"""
Simple BWT round-trip test to debug the integration issue
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from logsim.bwt import bwt_transform, bwt_inverse
import msgpack

# Test data
test_dict = {
    'version': '3.2',
    'templates': ['test1', 'test2'],
    'timestamps_varint': b'\x01\x02\x03',
    'timestamp_base': 1234567890,
    'numbers': [1, 2, 3, 4, 5]
}

print("Original dict:", test_dict)

# Pack with msgpack
msgpack_data = msgpack.packb(test_dict, use_bin_type=True)
print(f"\nMessagePack size: {len(msgpack_data)} bytes")
print(f"MessagePack hex (first 50 bytes): {msgpack_data[:50].hex()}")

# Apply BWT
bwt_data = bwt_transform(msgpack_data, block_size=256*1024)
print(f"\nBWT size: {len(bwt_data)} bytes")
print(f"BWT hex (first 50 bytes): {bwt_data[:50].hex()}")

# Reverse BWT
recovered_msgpack = bwt_inverse(bwt_data)
print(f"\nRecovered size: {len(recovered_msgpack)} bytes")
print(f"Recovered hex (first 50 bytes): {recovered_msgpack[:50].hex()}")

# Check if identical
if msgpack_data == recovered_msgpack:
    print("\n✅ BWT round-trip successful! Data matches exactly.")
else:
    print(f"\n❌ BWT round-trip FAILED!")
    print(f"   Original:  {len(msgpack_data)} bytes")
    print(f"   Recovered: {len(recovered_msgpack)} bytes")
    
    # Find first difference
    for i in range(min(len(msgpack_data), len(recovered_msgpack))):
        if msgpack_data[i] != recovered_msgpack[i]:
            print(f"   First diff at byte {i}: {msgpack_data[i]} != {recovered_msgpack[i]}")
            break

# Try to unpack
try:
    recovered_dict = msgpack.unpackb(recovered_msgpack, raw=False)
    print(f"\n✅ MessagePack unpack successful!")
    print(f"Recovered dict: {recovered_dict}")
    
    if recovered_dict == test_dict:
        print("\n✅ Full round-trip successful! Dicts match exactly.")
    else:
        print(f"\n❌ Dicts don't match!")
        print(f"   Original keys:  {set(test_dict.keys())}")
        print(f"   Recovered keys: {set(recovered_dict.keys())}")
except Exception as e:
    print(f"\n❌ MessagePack unpack failed: {e}")
