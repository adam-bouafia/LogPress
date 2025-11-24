#!/usr/bin/env python3
"""
Comprehensive compression and query benchmarks

Compares LogSim against gzip and uncompressed storage:
1. Compression ratio
2. Compression time
3. Query latency
4. Memory usage
"""

import argparse
import time
import gzip
from pathlib import Path
from typing import List, Dict
import json

from logsim.compressor import SemanticCompressor
from logsim.query_engine import QueryEngine


def load_logs(filepath: Path, max_lines: int = None) -> List[str]:
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


def benchmark_compression(logs: List[str], dataset_name: str) -> Dict:
    """Benchmark compression performance"""
    
    print(f"\n{'='*80}")
    print(f"Compression Benchmark: {dataset_name}")
    print(f"{'='*80}")
    
    results = {
        'dataset': dataset_name,
        'log_count': len(logs),
        'methods': {}
    }
    
    # Original size
    original_data = '\n'.join(logs).encode('utf-8')
    original_size = len(original_data)
    results['original_size'] = original_size
    
    print(f"Original: {original_size:,} bytes ({original_size/1024:.1f} KB)")
    
    # 1. LogSim compression
    print(f"\n[1/3] LogSim semantic compression...")
    compressor = SemanticCompressor(min_support=5)
    
    start = time.time()
    compressed, stats = compressor.compress(logs, verbose=False)
    logsim_time = time.time() - start
    
    # Save to file to get actual size
    temp_file = Path(f"compressed/{dataset_name}_temp.lsc")
    compressor.save(temp_file)
    logsim_size = temp_file.stat().st_size
    
    results['methods']['logsim'] = {
        'compressed_size': logsim_size,
        'compression_ratio': original_size / logsim_size,
        'compression_time': logsim_time,
        'throughput_mb_s': (original_size / 1024 / 1024) / logsim_time
    }
    
    print(f"  ✓ Size: {logsim_size:,} bytes ({logsim_size/1024:.1f} KB)")
    print(f"  ✓ Ratio: {original_size/logsim_size:.2f}x")
    print(f"  ✓ Time: {logsim_time:.3f}s ({original_size/1024/1024/logsim_time:.1f} MB/s)")
    
    # 2. gzip -9 compression
    print(f"\n[2/3] gzip -9 compression...")
    start = time.time()
    gzipped = gzip.compress(original_data, compresslevel=9)
    gzip_time = time.time() - start
    gzip_size = len(gzipped)
    
    results['methods']['gzip'] = {
        'compressed_size': gzip_size,
        'compression_ratio': original_size / gzip_size,
        'compression_time': gzip_time,
        'throughput_mb_s': (original_size / 1024 / 1024) / gzip_time
    }
    
    print(f"  ✓ Size: {gzip_size:,} bytes ({gzip_size/1024:.1f} KB)")
    print(f"  ✓ Ratio: {original_size/gzip_size:.2f}x")
    print(f"  ✓ Time: {gzip_time:.3f}s ({original_size/1024/1024/gzip_time:.1f} MB/s)")
    
    # 3. gzip -1 (fast) compression
    print(f"\n[3/3] gzip -1 (fast) compression...")
    start = time.time()
    gzipped_fast = gzip.compress(original_data, compresslevel=1)
    gzip_fast_time = time.time() - start
    gzip_fast_size = len(gzipped_fast)
    
    results['methods']['gzip_fast'] = {
        'compressed_size': gzip_fast_size,
        'compression_ratio': original_size / gzip_fast_size,
        'compression_time': gzip_fast_time,
        'throughput_mb_s': (original_size / 1024 / 1024) / gzip_fast_time
    }
    
    print(f"  ✓ Size: {gzip_fast_size:,} bytes ({gzip_fast_size/1024:.1f} KB)")
    print(f"  ✓ Ratio: {original_size/gzip_fast_size:.2f}x")
    print(f"  ✓ Time: {gzip_fast_time:.3f}s ({original_size/1024/1024/gzip_fast_time:.1f} MB/s)")
    
    # Summary
    print(f"\n📊 Summary:")
    print(f"  LogSim:      {results['methods']['logsim']['compression_ratio']:.2f}x ratio, "
          f"{results['methods']['logsim']['throughput_mb_s']:.1f} MB/s")
    print(f"  gzip -9:     {results['methods']['gzip']['compression_ratio']:.2f}x ratio, "
          f"{results['methods']['gzip']['throughput_mb_s']:.1f} MB/s")
    print(f"  gzip -1:     {results['methods']['gzip_fast']['compression_ratio']:.2f}x ratio, "
          f"{results['methods']['gzip_fast']['throughput_mb_s']:.1f} MB/s")
    
    ratio_vs_gzip = results['methods']['logsim']['compression_ratio'] / results['methods']['gzip']['compression_ratio']
    speed_vs_gzip = results['methods']['logsim']['throughput_mb_s'] / results['methods']['gzip']['throughput_mb_s']
    
    print(f"\n  LogSim vs gzip -9:")
    print(f"    • Compression: {ratio_vs_gzip:.2f}x {'better' if ratio_vs_gzip > 1 else 'worse'}")
    print(f"    • Speed: {speed_vs_gzip:.2f}x {'faster' if speed_vs_gzip > 1 else 'slower'}")
    
    return results


def benchmark_queries(compressed_file: Path, dataset_name: str) -> Dict:
    """Benchmark query performance"""
    
    print(f"\n{'='*80}")
    print(f"Query Benchmark: {dataset_name}")
    print(f"{'='*80}")
    
    engine = QueryEngine(compressed_file)
    
    results = {
        'dataset': dataset_name,
        'queries': {}
    }
    
    # 1. Count query
    print(f"\n[1/3] COUNT query...")
    result = engine.count_all()
    results['queries']['count'] = {
        'time': result.execution_time,
        'matched': result.matched_count,
        'scanned': result.scanned_count
    }
    print(f"  ✓ Matched: {result.matched_count:,} logs")
    print(f"  ✓ Time: {result.execution_time*1000:.3f}ms")
    
    # 2. Severity filter
    print(f"\n[2/3] WHERE severity='ERROR' query...")
    result = engine.query_by_severity('ERROR')
    results['queries']['severity_filter'] = {
        'time': result.execution_time,
        'matched': result.matched_count,
        'scanned': result.scanned_count,
        'throughput': result.scanned_count / result.execution_time if result.execution_time > 0 else 0
    }
    print(f"  ✓ Matched: {result.matched_count:,} logs")
    print(f"  ✓ Scanned: {result.scanned_count:,} entries")
    print(f"  ✓ Time: {result.execution_time*1000:.3f}ms")
    print(f"  ✓ Throughput: {result.scanned_count/result.execution_time:,.0f} entries/sec")
    
    # 3. Stats query
    print(f"\n[3/3] Statistics query...")
    start = time.time()
    stats = engine.get_statistics()
    stats_time = time.time() - start
    results['queries']['stats'] = {
        'time': stats_time,
        'unique_severities': stats['unique_severities'],
        'unique_ips': stats['unique_ips'],
        'unique_messages': stats['unique_messages']
    }
    print(f"  ✓ Unique severities: {stats['unique_severities']}")
    print(f"  ✓ Unique IPs: {stats['unique_ips']}")
    print(f"  ✓ Unique messages: {stats['unique_messages']}")
    print(f"  ✓ Time: {stats_time*1000:.3f}ms")
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Comprehensive benchmark suite")
    parser.add_argument('--dataset', required=True, 
                       choices=['Apache', 'HealthApp', 'Zookeeper', 'OpenStack', 'Proxifier', 'all'])
    parser.add_argument('--sample-size', type=int, default=5000)
    parser.add_argument('--output', default='benchmarks.json', help='Output results file')
    
    args = parser.parse_args()
    
    print("🚀 LogSim Comprehensive Benchmark Suite")
    print("="*80)
    
    datasets = ['Apache', 'HealthApp', 'Zookeeper', 'OpenStack', 'Proxifier'] if args.dataset == 'all' else [args.dataset]
    
    all_results = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'sample_size': args.sample_size,
        'datasets': []
    }
    
    for dataset in datasets:
        # Load dataset
        if dataset == 'OpenStack':
            log_file = Path(f"datasets/{dataset}/openstack.log")
        else:
            log_file = Path(f"datasets/{dataset}/{dataset}_full.log")
        
        if not log_file.exists():
            print(f"⚠️  Skipping {dataset} - file not found")
            continue
        
        print(f"\n📂 Loading {dataset}...")
        logs = load_logs(log_file, args.sample_size)
        print(f"✓ Loaded {len(logs):,} logs")
        
        # Run compression benchmark
        compression_results = benchmark_compression(logs, dataset)
        
        # Run query benchmark
        compressed_file = Path(f"compressed/{dataset}_temp.lsc")
        query_results = benchmark_queries(compressed_file, dataset)
        
        # Combine results
        dataset_results = {
            **compression_results,
            **query_results
        }
        all_results['datasets'].append(dataset_results)
    
    # Save results
    output_file = Path(args.output)
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\n{'='*80}")
    print(f"✅ Benchmark complete! Results saved to {output_file}")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
