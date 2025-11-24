#!/usr/bin/env python3
"""
Test Otten's preprocessing techniques on Apache dataset

This script compares compression with and without Otten's:
1. Binary timestamp/IP encoding (+2-3% expected)
2. Template word dictionaries (+10-14% expected)

Expected total improvement: +12-17% (16.46x → 18.4-19.3x)
"""

import sys
import time
import gzip
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from logsim.compressor import SemanticCompressor


def test_otten_preprocessing():
    """Test Otten's preprocessing on Apache logs"""
    
    print("=" * 80)
    print("OTTEN PREPROCESSING TEST - Apache Dataset")
    print("=" * 80)
    print()
    
    # Load Apache logs (5,000 samples for faster testing)
    apache_path = Path("datasets/Apache/Apache_full.log")
    
    print(f"📂 Loading Apache logs from {apache_path}")
    logs = []
    with open(apache_path, 'r', encoding='utf-8', errors='ignore') as f:
        for i, line in enumerate(f):
            if i >= 5000:
                break
            line = line.strip()
            if line:
                logs.append(line)
    
    print(f"✓ Loaded {len(logs):,} logs")
    print()
    
    # Calculate original size
    original_data = '\n'.join(logs).encode('utf-8')
    original_size = len(original_data)
    
    # Get gzip baseline
    print("📊 Compressing with gzip -9 (baseline)...")
    gzipped = gzip.compress(original_data, compresslevel=9)
    gzip_size = len(gzipped)
    gzip_ratio = original_size / gzip_size
    
    print(f"✓ gzip: {original_size:,} → {gzip_size:,} bytes ({gzip_ratio:.2f}x)")
    print()
    
    # Test 1: Without Otten (baseline LogSim)
    print("=" * 80)
    print("TEST 1: LogSim WITHOUT Otten's Preprocessing (Baseline)")
    print("=" * 80)
    print()
    
    compressor_baseline = SemanticCompressor(min_support=3, enable_otten=False)
    
    start = time.time()
    compressed_baseline, stats_baseline = compressor_baseline.compress(logs, verbose=True)
    compress_time_baseline = time.time() - start
    
    # Save and measure file size
    baseline_path = Path("compressed/apache_otten_baseline.lsc")
    compressor_baseline.save(baseline_path, verbose=False)
    baseline_size = baseline_path.stat().st_size
    baseline_ratio = original_size / baseline_size
    
    print()
    print(f"Results:")
    print(f"  Original:    {original_size:,} bytes")
    print(f"  Compressed:  {baseline_size:,} bytes")
    print(f"  Ratio:       {baseline_ratio:.2f}x")
    print(f"  vs gzip:     {(baseline_ratio/gzip_ratio)*100:.1f}%")
    print(f"  Time:        {compress_time_baseline:.2f}s")
    print()
    
    # Test 2: With Otten's preprocessing
    print("=" * 80)
    print("TEST 2: LogSim WITH Otten's Preprocessing (Phase 1+2)")
    print("=" * 80)
    print()
    print("Otten's Phase 1: Binary timestamp/IP encoding (15+ bytes → 4 bytes)")
    print("Otten's Phase 2: Per-template word dictionaries (frequency × length scoring)")
    print()
    
    compressor_otten = SemanticCompressor(min_support=3, enable_otten=True)
    
    start = time.time()
    compressed_otten, stats_otten = compressor_otten.compress(logs, verbose=True)
    compress_time_otten = time.time() - start
    
    # Save and measure file size
    otten_path = Path("compressed/apache_otten_enabled.lsc")
    compressor_otten.save(otten_path, verbose=False)
    otten_size = otten_path.stat().st_size
    otten_ratio = original_size / otten_size
    
    print()
    print(f"Results:")
    print(f"  Original:    {original_size:,} bytes")
    print(f"  Compressed:  {otten_size:,} bytes")
    print(f"  Ratio:       {otten_ratio:.2f}x")
    print(f"  vs gzip:     {(otten_ratio/gzip_ratio)*100:.1f}%")
    print(f"  Time:        {compress_time_otten:.2f}s")
    print()
    
    # Test 3: Round-trip verification
    print("=" * 80)
    print("TEST 3: Round-trip Verification (Otten Enabled)")
    print("=" * 80)
    print()
    
    # Load and decompress
    loaded = SemanticCompressor.load(otten_path)
    decompressor = SemanticCompressor(min_support=3, enable_otten=True)
    decompressor.compressed_data = loaded
    
    start = time.time()
    decompressed_logs = decompressor.decompress(enable_otten=True)
    decompress_time = time.time() - start
    
    # Verify
    match_count = sum(1 for i, (orig, decomp) in enumerate(zip(logs, decompressed_logs)) if orig == decomp)
    mismatch_count = len(logs) - match_count
    
    print(f"✓ Decompressed {len(decompressed_logs):,} logs in {decompress_time:.2f}s")
    print(f"✓ Exact matches: {match_count:,}/{len(logs):,}")
    
    if mismatch_count > 0:
        print(f"⚠ Mismatches: {mismatch_count} (checking first 3...)")
        shown = 0
        for i, (orig, decomp) in enumerate(zip(logs, decompressed_logs)):
            if orig != decomp and shown < 3:
                print(f"\n  Log {i}:")
                print(f"    Original:     {orig[:100]}...")
                print(f"    Decompressed: {decomp[:100]}...")
                shown += 1
    else:
        print(f"✓ Perfect round-trip! All logs match exactly.")
    print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY: Otten's Preprocessing Impact")
    print("=" * 80)
    print()
    
    improvement = ((otten_ratio - baseline_ratio) / baseline_ratio) * 100
    time_overhead = compress_time_otten - compress_time_baseline
    
    print(f"Compression Improvement:")
    print(f"  Baseline:       {baseline_ratio:.2f}x ({(baseline_ratio/gzip_ratio)*100:.1f}% of gzip)")
    print(f"  With Otten:     {otten_ratio:.2f}x ({(otten_ratio/gzip_ratio)*100:.1f}% of gzip)")
    print(f"  Improvement:    +{improvement:.1f}%")
    print()
    
    print(f"Size Comparison:")
    print(f"  Baseline:       {baseline_size:,} bytes")
    print(f"  With Otten:     {otten_size:,} bytes")
    print(f"  Saved:          {baseline_size - otten_size:,} bytes")
    print()
    
    print(f"Performance:")
    print(f"  Baseline time:  {compress_time_baseline:.2f}s")
    print(f"  Otten time:     {compress_time_otten:.2f}s")
    print(f"  Overhead:       +{time_overhead:.2f}s ({(time_overhead/compress_time_baseline)*100:.0f}%)")
    print()
    
    # Expected vs actual
    print(f"Expected vs Actual:")
    print(f"  Expected improvement: +12-17% (Otten's paper: +2-3% binary, +10-14% dictionaries)")
    print(f"  Actual improvement:   +{improvement:.1f}%")
    
    if improvement >= 12:
        print(f"  ✅ MEETS/EXCEEDS EXPECTATIONS!")
    elif improvement >= 8:
        print(f"  ✓ Good improvement (close to expectations)")
    else:
        print(f"  ⚠ Below expectations (may need tuning)")
    
    print()
    print("=" * 80)


if __name__ == '__main__':
    test_otten_preprocessing()
