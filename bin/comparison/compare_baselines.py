#!/usr/bin/env python3
"""
Comprehensive baseline comparison: LogSim vs LZ4, Zstandard, Gzip

Compares LogSim's semantic compression against pure compression baselines:
1. Gzip (standard baseline) - already tested
2. LZ4 (fast compression)
3. Zstandard-only (modern compression, no semantic layer)
4. Snappy (very fast compression)

Shows if semantic preprocessing adds value over pure compression.
"""

import sys
import gzip
import lz4.frame
import zstandard as zstd
import snappy
from pathlib import Path
from typing import Dict, Tuple
import json
import time

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from logsim.compressor import SemanticCompressor


def compress_with_gzip(data: bytes) -> Tuple[bytes, float]:
    """Compress with gzip level 9"""
    start = time.time()
    compressed = gzip.compress(data, compresslevel=9)
    elapsed = time.time() - start
    return compressed, elapsed


def compress_with_lz4(data: bytes) -> Tuple[bytes, float]:
    """Compress with LZ4 (high compression mode)"""
    start = time.time()
    compressed = lz4.frame.compress(data, compression_level=lz4.frame.COMPRESSIONLEVEL_MAX)
    elapsed = time.time() - start
    return compressed, elapsed


def compress_with_zstd(data: bytes) -> Tuple[bytes, float]:
    """Compress with Zstandard level 19 (max)"""
    start = time.time()
    cctx = zstd.ZstdCompressor(level=19)
    compressed = cctx.compress(data)
    elapsed = time.time() - start
    return compressed, elapsed


def compress_with_snappy(data: bytes) -> Tuple[bytes, float]:
    """Compress with Snappy (speed-focused)"""
    start = time.time()
    compressed = snappy.compress(data)
    elapsed = time.time() - start
    return compressed, elapsed


def compress_with_logsim(log_file: Path, output_file: Path) -> Tuple[int, float, Dict]:
    """Compress with LogSim semantic compression"""
    # Read logs
    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        logs = [line.strip() for line in f if line.strip()]
    
    # Take sample for faster testing
    sample_size = min(5000, len(logs))
    logs = logs[:sample_size]
    
    # Compress
    start = time.time()
    compressor = SemanticCompressor(min_support=3)
    compressed_data, stats = compressor.compress(logs, verbose=False)
    compressor.save(output_file)
    elapsed = time.time() - start
    
    # Get file size
    file_size = output_file.stat().st_size
    
    return file_size, elapsed, {
        'original_size': stats.original_size,
        'compression_ratio': stats.compression_ratio,
        'template_count': stats.template_count,
        'log_count': stats.log_count
    }


def run_baseline_comparison(dataset_name: str, log_file: Path):
    """Run comprehensive baseline comparison"""
    print(f"\n{'='*80}")
    print(f"BASELINE COMPARISON: {dataset_name}")
    print(f"{'='*80}\n")
    
    # Read log file
    with open(log_file, 'rb') as f:
        raw_data = f.read()
    
    # Take sample (5000 lines)
    lines = raw_data.decode('utf-8', errors='ignore').strip().split('\n')
    sample_size = min(5000, len(lines))
    sample_data = '\n'.join(lines[:sample_size]).encode('utf-8')
    original_size = len(sample_data)
    
    print(f"Original size: {original_size:,} bytes ({original_size/1024:.1f} KB)")
    print(f"Sample: {sample_size:,} log lines\n")
    
    results = {}
    
    # Test Gzip
    print("Testing Gzip (level 9)...")
    gzip_compressed, gzip_time = compress_with_gzip(sample_data)
    gzip_ratio = original_size / len(gzip_compressed)
    results['gzip'] = {
        'size': len(gzip_compressed),
        'ratio': gzip_ratio,
        'time': gzip_time
    }
    print(f"  ✓ Size: {len(gzip_compressed):,} bytes ({len(gzip_compressed)/1024:.1f} KB)")
    print(f"  ✓ Ratio: {gzip_ratio:.2f}x")
    print(f"  ✓ Time: {gzip_time:.3f}s\n")
    
    # Test LZ4
    print("Testing LZ4 (max compression)...")
    lz4_compressed, lz4_time = compress_with_lz4(sample_data)
    lz4_ratio = original_size / len(lz4_compressed)
    results['lz4'] = {
        'size': len(lz4_compressed),
        'ratio': lz4_ratio,
        'time': lz4_time
    }
    print(f"  ✓ Size: {len(lz4_compressed):,} bytes ({len(lz4_compressed)/1024:.1f} KB)")
    print(f"  ✓ Ratio: {lz4_ratio:.2f}x")
    print(f"  ✓ Time: {lz4_time:.3f}s\n")
    
    # Test Zstandard
    print("Testing Zstandard (level 19)...")
    zstd_compressed, zstd_time = compress_with_zstd(sample_data)
    zstd_ratio = original_size / len(zstd_compressed)
    results['zstd'] = {
        'size': len(zstd_compressed),
        'ratio': zstd_ratio,
        'time': zstd_time
    }
    print(f"  ✓ Size: {len(zstd_compressed):,} bytes ({len(zstd_compressed)/1024:.1f} KB)")
    print(f"  ✓ Ratio: {zstd_ratio:.2f}x")
    print(f"  ✓ Time: {zstd_time:.3f}s\n")
    
    # Test Snappy
    print("Testing Snappy (speed-focused)...")
    snappy_compressed, snappy_time = compress_with_snappy(sample_data)
    snappy_ratio = original_size / len(snappy_compressed)
    results['snappy'] = {
        'size': len(snappy_compressed),
        'ratio': snappy_ratio,
        'time': snappy_time
    }
    print(f"  ✓ Size: {len(snappy_compressed):,} bytes ({len(snappy_compressed)/1024:.1f} KB)")
    print(f"  ✓ Ratio: {snappy_ratio:.2f}x")
    print(f"  ✓ Time: {snappy_time:.3f}s\n")
    
    # Test LogSim
    print("Testing LogSim (semantic + MessagePack + gzip + zstd)...")
    output_file = Path(f"compressed/{dataset_name.lower()}_baseline_test.lsc")
    logsim_size, logsim_time, logsim_info = compress_with_logsim(log_file, output_file)
    logsim_ratio = logsim_info['original_size'] / logsim_size
    results['logsim'] = {
        'size': logsim_size,
        'ratio': logsim_ratio,
        'time': logsim_time,
        'templates': logsim_info['template_count'],
        'logs': logsim_info['log_count']
    }
    print(f"  ✓ Size: {logsim_size:,} bytes ({logsim_size/1024:.1f} KB)")
    print(f"  ✓ Ratio: {logsim_ratio:.2f}x")
    print(f"  ✓ Time: {logsim_time:.3f}s")
    print(f"  ✓ Templates: {logsim_info['template_count']}")
    print(f"  ✓ Queryable: Yes (columnar storage)\n")
    
    # Summary table
    print(f"\n{'='*80}")
    print("SUMMARY TABLE")
    print(f"{'='*80}\n")
    print(f"{'Method':<15} {'Size (KB)':<12} {'Ratio':<10} {'Time (s)':<10} {'Queryable':<10}")
    print(f"{'-'*80}")
    
    for method, data in results.items():
        queryable = "Yes" if method == 'logsim' else "No"
        print(f"{method.upper():<15} {data['size']/1024:<12.1f} {data['ratio']:<10.2f} {data['time']:<10.3f} {queryable:<10}")
    
    print(f"\n{'='*80}")
    print("KEY INSIGHTS")
    print(f"{'='*80}\n")
    
    # Find best compression
    best_ratio = max(results.items(), key=lambda x: x[1]['ratio'])
    fastest = min(results.items(), key=lambda x: x[1]['time'])
    
    print(f"✓ Best compression: {best_ratio[0].upper()} ({best_ratio[1]['ratio']:.2f}x)")
    print(f"✓ Fastest: {fastest[0].upper()} ({fastest[1]['time']:.3f}s)")
    print(f"✓ LogSim ratio: {results['logsim']['ratio']:.2f}x")
    print(f"✓ LogSim vs Gzip: {(results['logsim']['ratio'] / results['gzip']['ratio'] - 1) * 100:+.1f}%")
    print(f"✓ LogSim advantage: Queryable without full decompression\n")
    
    # Save results
    results_file = Path(f"results/comparison/baseline_{dataset_name.lower()}.json")
    results_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(results_file, 'w') as f:
        json.dump({
            'dataset': dataset_name,
            'original_size': original_size,
            'sample_size': sample_size,
            'results': results
        }, f, indent=2)
    
    print(f"Results saved to: {results_file}\n")
    
    return results


def main():
    """Run baseline comparison on all datasets"""
    datasets = {
        'Apache': Path('datasets/Apache/Apache_full.log'),
        'HealthApp': Path('datasets/HealthApp/HealthApp_full.log'),
        'Zookeeper': Path('datasets/Zookeeper/Zookeeper_full.log'),
        'Proxifier': Path('datasets/Proxifier/Proxifier_full.log')
    }
    
    all_results = {}
    
    for dataset_name, log_file in datasets.items():
        if not log_file.exists():
            print(f"⚠️  Skipping {dataset_name}: file not found")
            continue
        
        results = run_baseline_comparison(dataset_name, log_file)
        all_results[dataset_name] = results
    
    # Generate final summary
    print(f"\n{'='*80}")
    print("FINAL COMPARISON ACROSS ALL DATASETS")
    print(f"{'='*80}\n")
    
    print(f"{'Dataset':<15} {'Gzip':<10} {'LZ4':<10} {'Zstd':<10} {'Snappy':<10} {'LogSim':<10}")
    print(f"{'-'*80}")
    
    for dataset_name, results in all_results.items():
        print(f"{dataset_name:<15} "
              f"{results['gzip']['ratio']:<10.2f} "
              f"{results['lz4']['ratio']:<10.2f} "
              f"{results['zstd']['ratio']:<10.2f} "
              f"{results['snappy']['ratio']:<10.2f} "
              f"{results['logsim']['ratio']:<10.2f}")
    
    # Calculate averages
    avg_gzip = sum(r['gzip']['ratio'] for r in all_results.values()) / len(all_results)
    avg_lz4 = sum(r['lz4']['ratio'] for r in all_results.values()) / len(all_results)
    avg_zstd = sum(r['zstd']['ratio'] for r in all_results.values()) / len(all_results)
    avg_snappy = sum(r['snappy']['ratio'] for r in all_results.values()) / len(all_results)
    avg_logsim = sum(r['logsim']['ratio'] for r in all_results.values()) / len(all_results)
    
    print(f"{'-'*80}")
    print(f"{'AVERAGE':<15} {avg_gzip:<10.2f} {avg_lz4:<10.2f} {avg_zstd:<10.2f} {avg_snappy:<10.2f} {avg_logsim:<10.2f}")
    
    print(f"\n{'='*80}")
    print("CONCLUSION")
    print(f"{'='*80}\n")
    
    print(f"LogSim achieves {avg_logsim:.2f}x compression (with MessagePack)")
    print(f"Gzip achieves {avg_gzip:.2f}x compression (pure compression)")
    print(f"Difference: {(avg_logsim / avg_gzip - 1) * 100:+.1f}%\n")
    
    print("LogSim's advantage:")
    print("  ✓ Queryable without full decompression")
    print("  ✓ Columnar storage for fast field access")
    print("  ✓ Semantic understanding of log structure")
    print("  ✓ Template extraction for pattern analysis\n")


if __name__ == '__main__':
    main()
