#!/usr/bin/env python3
"""
Test BWT integration in production compressor

Validates that use_bwt=True achieves the expected 28.10x average compression
"""

import sys
import time
import gzip
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from logsim.compressor import SemanticCompressor


def load_logs(filepath: Path, max_lines: int = None) -> list:
    """Load log entries"""
    logs = []
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for i, line in enumerate(f):
            if max_lines and i >= max_lines:
                break
            line = line.strip()
            if line:
                logs.append(line)
    return logs


def test_dataset(dataset_name: str, log_file: Path):
    """Test BWT integration on a dataset"""
    print(f"\n{'='*80}")
    print(f"Testing: {dataset_name}")
    print(f"{'='*80}")
    
    # Load 5K logs (same as standalone test)
    logs = load_logs(log_file, max_lines=5000)
    print(f"Loaded {len(logs):,} log entries")
    
    # Calculate original size
    original_data = '\n'.join(logs).encode('utf-8')
    original_size = len(original_data)
    print(f"Original size: {original_size:,} bytes ({original_size/1024:.1f} KB)")
    
    # Baseline: gzip -9
    gzipped = gzip.compress(original_data, compresslevel=9)
    gzip_size = len(gzipped)
    gzip_ratio = original_size / gzip_size
    print(f"gzip -9 size: {gzip_size:,} bytes → {gzip_ratio:.2f}x compression")
    
    # Test WITHOUT BWT (baseline)
    print(f"\n[1/2] Testing WITHOUT BWT (baseline)...")
    compressor = SemanticCompressor(min_support=5)
    start = time.time()
    compressed, stats = compressor.compress(logs, verbose=False)
    compress_time = time.time() - start
    
    temp_file = Path(f"compressed/{dataset_name}_nobwt_test.lsc")
    compressor.save(temp_file, verbose=False, use_bwt=False)
    nobwt_size = temp_file.stat().st_size
    nobwt_ratio = original_size / nobwt_size
    
    print(f"  ✓ Size: {nobwt_size:,} bytes ({nobwt_size/1024:.1f} KB)")
    print(f"  ✓ Compression ratio: {nobwt_ratio:.2f}x")
    print(f"  ✓ vs gzip: {nobwt_ratio/gzip_ratio*100:.1f}%")
    print(f"  ✓ Time: {compress_time:.2f}s")
    
    # Test WITH BWT
    print(f"\n[2/2] Testing WITH BWT...")
    start = time.time()
    temp_file_bwt = Path(f"compressed/{dataset_name}_bwt_test.lsc")
    compressor.save(temp_file_bwt, verbose=True, use_bwt=True)
    save_time = time.time() - start
    
    bwt_size = temp_file_bwt.stat().st_size
    bwt_ratio = original_size / bwt_size
    
    print(f"  ✓ Size: {bwt_size:,} bytes ({bwt_size/1024:.1f} KB)")
    print(f"  ✓ Compression ratio: {bwt_ratio:.2f}x")
    print(f"  ✓ vs gzip: {bwt_ratio/gzip_ratio*100:.1f}%")
    print(f"  ✓ BWT processing time: {save_time:.2f}s")
    
    # Validate round-trip
    print(f"\n[3/3] Validating round-trip (load with use_bwt=True)...")
    loaded_compressed_data = SemanticCompressor.load(temp_file_bwt, use_bwt=True)
    
    # Create a new compressor and decompress
    decompressor = SemanticCompressor(min_support=5)
    decompressor.compressed_data = loaded_compressed_data
    decompressed_logs = decompressor.decompress()
    
    if len(decompressed_logs) == len(logs):
        print(f"  ✓ Round-trip successful: {len(decompressed_logs):,} logs recovered")
        # Sample check
        mismatches = sum(1 for i in range(min(100, len(logs))) if decompressed_logs[i] != logs[i])
        if mismatches == 0:
            print(f"  ✓ First 100 logs match exactly")
        else:
            print(f"  ✗ WARNING: {mismatches} mismatches in first 100 logs")
    else:
        print(f"  ✗ ERROR: Expected {len(logs)} logs, got {len(decompressed_logs)}")
    
    # Summary
    improvement = ((bwt_ratio / nobwt_ratio) - 1) * 100
    print(f"\n📊 Summary:")
    print(f"   Baseline (no BWT):  {nobwt_ratio:.2f}x")
    print(f"   With BWT:           {bwt_ratio:.2f}x")
    print(f"   Improvement:        {improvement:+.1f}%")
    print(f"   vs gzip target:     {bwt_ratio/gzip_ratio*100:.1f}% (target: 100%)")
    
    return {
        'dataset': dataset_name,
        'original_size': original_size,
        'gzip_ratio': gzip_ratio,
        'nobwt_ratio': nobwt_ratio,
        'bwt_ratio': bwt_ratio,
        'improvement_pct': improvement
    }


def main():
    print("="*80)
    print("BWT Integration Test - Production Compressor")
    print("="*80)
    print("This validates that use_bwt=True achieves expected compression gains")
    
    datasets = [
        ('Apache', Path('datasets/Apache/Apache_full.log')),
        ('HealthApp', Path('datasets/HealthApp/HealthApp_full.log')),
        ('Zookeeper', Path('datasets/Zookeeper/Zookeeper_full.log')),
        ('Proxifier', Path('datasets/Proxifier/Proxifier_full.log')),
    ]
    
    results = []
    for name, path in datasets:
        if path.exists():
            result = test_dataset(name, path)
            results.append(result)
        else:
            print(f"\n⚠️  Skipping {name}: {path} not found")
    
    # Overall summary
    print(f"\n{'='*80}")
    print("OVERALL RESULTS")
    print(f"{'='*80}")
    print(f"{'Dataset':<15} {'Baseline':<12} {'With BWT':<12} {'Gain':<10} {'vs gzip'}")
    print(f"{'-'*80}")
    
    total_improvement = 0
    for r in results:
        gain_str = f"{r['improvement_pct']:+.1f}%"
        vs_gzip_str = f"{r['bwt_ratio']/r['gzip_ratio']*100:.1f}%"
        print(f"{r['dataset']:<15} {r['nobwt_ratio']:>6.2f}x      {r['bwt_ratio']:>6.2f}x      {gain_str:<10} {vs_gzip_str}")
        total_improvement += r['improvement_pct']
    
    if results:
        avg_improvement = total_improvement / len(results)
        avg_bwt_ratio = sum(r['bwt_ratio'] for r in results) / len(results)
        avg_gzip_ratio = sum(r['gzip_ratio'] for r in results) / len(results)
        
        print(f"{'-'*80}")
        print(f"{'AVERAGE':<15} {'':>6}       {avg_bwt_ratio:>6.2f}x      {avg_improvement:+.1f}%       {avg_bwt_ratio/avg_gzip_ratio*100:.1f}%")
        
        # Target validation
        print(f"\n✅ Target Validation:")
        print(f"   Expected improvement: +79.7% (from standalone test)")
        print(f"   Achieved improvement: {avg_improvement:+.1f}%")
        
        if avg_improvement >= 75:
            print(f"   ✅ SUCCESS: Matches standalone BWT test results!")
        elif avg_improvement >= 50:
            print(f"   ⚠️  WARNING: Lower than standalone test, but still good")
        else:
            print(f"   ✗ ISSUE: Significantly lower than standalone test")
        
        print(f"\n   Expected avg ratio: 28.10x (150% of gzip)")
        print(f"   Achieved avg ratio: {avg_bwt_ratio:.2f}x ({avg_bwt_ratio/avg_gzip_ratio*100:.1f}% of gzip)")


if __name__ == '__main__':
    main()
