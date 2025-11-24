#!/usr/bin/env python3
"""
Test ONLY binary timestamp/IP encoding (Otten Phase 1)
Disable template dictionaries to isolate the binary encoding impact
"""

import sys
import time
import gzip
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from logsim.compressor import SemanticCompressor


def test_binary_encoding_only():
    print("=" * 80)
    print("TEST: Binary Encoding Only (Otten Phase 1)")
    print("=" * 80)
    print()
    
    # Load Apache logs
    apache_path = Path("datasets/Apache/Apache_full.log")
    
    print(f"📂 Loading {apache_path}")
    logs = []
    with open(apache_path, 'r', encoding='utf-8', errors='ignore') as f:
        for i, line in enumerate(f):
            if i >= 5000:
                break
            if line.strip():
                logs.append(line.strip())
    
    print(f"✓ Loaded {len(logs):,} logs\n")
    
    original_data = '\n'.join(logs).encode('utf-8')
    original_size = len(original_data)
    
    # gzip baseline
    gzipped = gzip.compress(original_data, compresslevel=9)
    gzip_size = len(gzipped)
    gzip_ratio = original_size / gzip_size
    print(f"gzip baseline: {gzip_ratio:.2f}x\n")
    
    # Baseline
    print("Test 1: Baseline (no Otten)")
    compressor1 = SemanticCompressor(min_support=3, enable_otten=False)
    compressed1, _ = compressor1.compress(logs, verbose=False)
    
    baseline_path = Path("compressed/test_binary_baseline.lsc")
    compressor1.save(baseline_path, verbose=False)
    baseline_size = baseline_path.stat().st_size
    baseline_ratio = original_size / baseline_size
    
    print(f"  Size: {baseline_size:,} bytes")
    print(f"  Ratio: {baseline_ratio:.2f}x ({(baseline_ratio/gzip_ratio)*100:.1f}% of gzip)\n")
    
    # With binary encoding (but disable word dictionaries by not building them)
    print("Test 2: Binary encoding (timestamps + IPs → 4 bytes)")
    
    compressor2 = SemanticCompressor(min_support=3, enable_otten=True)
    # Clear template_dicts to disable word encoding
    compressor2.template_dicts = {}
    
    compressed2, _ = compressor2.compress(logs, verbose=False)
    
    binary_path = Path("compressed/test_binary_only.lsc")
    compressor2.save(binary_path, verbose=False)
    binary_size = binary_path.stat().st_size
    binary_ratio = original_size / binary_size
    
    print(f"  Size: {binary_size:,} bytes")
    print(f"  Ratio: {binary_ratio:.2f}x ({(binary_ratio/gzip_ratio)*100:.1f}% of gzip)\n")
    
    # Results
    improvement = ((binary_ratio - baseline_ratio) / baseline_ratio) * 100
    
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(f"Baseline:         {baseline_ratio:.2f}x")
    print(f"Binary encoding:  {binary_ratio:.2f}x")
    print(f"Improvement:      {improvement:+.1f}%")
    print()
    
    if improvement >= 2:
        print("✅ Binary encoding provides expected +2-3% improvement!")
    elif improvement > 0:
        print(f"✓ Positive improvement (+{improvement:.1f}%)")
    else:
        print(f"⚠ Negative impact ({improvement:.1f}%)")
    
    # Check what happened to timestamps
    print(f"\nAnalysis:")
    print(f"  Timestamp count: {compressed2.timestamp_count}")
    print(f"  Timestamp storage: {len(compressed2.timestamps_varint)} bytes")
    print(f"  IP count: {compressed2.ip_count}")
    print(f"  IP storage: {len(compressed2.ip_addresses_varint)} bytes")


if __name__ == '__main__':
    test_binary_encoding_only()
