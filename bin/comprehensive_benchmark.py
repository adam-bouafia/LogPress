#!/usr/bin/env python3
"""
Comprehensive benchmark across all datasets
Tests improved compression with varint + pattern RLE
"""

import sys
from pathlib import Path
import gzip
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from logsim.compressor import SemanticCompressor


def benchmark_dataset(dataset_name: str, dataset_path: str, sample_size: int = 5000):
    """Benchmark single dataset"""
    print(f"\n{'='*80}")
    print(f"Benchmarking: {dataset_name}")
    print(f"{'='*80}")
    
    # Load logs
    logs = []
    with open(dataset_path, 'r', encoding='utf-8', errors='ignore') as f:
        logs = [line.strip() for line in f if line.strip()][:sample_size]
    
    print(f"Loaded {len(logs)} logs\n")
    
    # LogSim compression
    compressor = SemanticCompressor()
    compressed, stats = compressor.compress(logs, verbose=False)
    
    output_path = Path(f'compressed/{dataset_name.lower()}_benchmark.lsc')
    compressor.save(output_path, verbose=False)
    
    logsim_size = output_path.stat().st_size
    logsim_ratio = stats.original_size / logsim_size
    
    # Gzip baseline
    original_data = '\n'.join(logs).encode('utf-8')
    gzipped = gzip.compress(original_data, compresslevel=9)
    gzip_ratio = len(original_data) / len(gzipped)
    
    # Results
    print(f"Original size: {stats.original_size:,} bytes ({stats.original_size/1024:.1f} KB)")
    print(f"LogSim:        {logsim_size:,} bytes ({logsim_size/1024:.1f} KB) → {logsim_ratio:.2f}x")
    print(f"Gzip -9:       {len(gzipped):,} bytes ({len(gzipped)/1024:.1f} KB) → {gzip_ratio:.2f}x")
    print(f"Gap:           {(logsim_ratio/gzip_ratio)*100:.1f}% of gzip")
    print(f"Templates:     {stats.template_count}")
    print(f"Time:          {stats.compression_time:.2f}s")
    
    return {
        'dataset': dataset_name,
        'sample_size': len(logs),
        'original_size': stats.original_size,
        'logsim_size': logsim_size,
        'gzip_size': len(gzipped),
        'logsim_ratio': round(logsim_ratio, 2),
        'gzip_ratio': round(gzip_ratio, 2),
        'gap_percent': round((logsim_ratio/gzip_ratio)*100, 1),
        'templates': stats.template_count,
        'compression_time': round(stats.compression_time, 2)
    }


def main():
    datasets = [
        ('Apache', 'datasets/Apache/Apache_full.log'),
        ('HealthApp', 'datasets/HealthApp/HealthApp_full.log'),
        ('Zookeeper', 'datasets/Zookeeper/Zookeeper_full.log'),
        ('Proxifier', 'datasets/Proxifier/Proxifier_full.log'),
        ('OpenStack', 'datasets/OpenStack/OpenStack_full.log'),
    ]
    
    results = []
    
    for dataset_name, dataset_path in datasets:
        if Path(dataset_path).exists():
            try:
                result = benchmark_dataset(dataset_name, dataset_path, sample_size=5000)
                results.append(result)
            except Exception as e:
                print(f"\n❌ Error benchmarking {dataset_name}: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"\n⚠️  Dataset not found: {dataset_path}")
    
    # Summary table
    print(f"\n\n{'='*80}")
    print("SUMMARY: LogSim v1.0 with Varint + Pattern RLE")
    print(f"{'='*80}\n")
    
    print(f"{'Dataset':<15} {'Original':<12} {'LogSim':<20} {'Gzip':<20} {'Gap':<10}")
    print(f"{'':15} {'Size':<12} {'Ratio':<10} {'Size':<10} {'Ratio':<10} {'Size':<10} {'% of Gzip':<10}")
    print("-" * 80)
    
    for r in results:
        orig_kb = r['original_size'] / 1024
        logsim_kb = r['logsim_size'] / 1024
        gzip_kb = r['gzip_size'] / 1024
        
        print(f"{r['dataset']:<15} {orig_kb:>6.1f} KB    "
              f"{r['logsim_ratio']:>5.2f}x     {logsim_kb:>6.1f} KB  "
              f"{r['gzip_ratio']:>5.2f}x     {gzip_kb:>6.1f} KB  "
              f"{r['gap_percent']:>6.1f}%")
    
    # Calculate averages
    if results:
        avg_logsim = sum(r['logsim_ratio'] for r in results) / len(results)
        avg_gzip = sum(r['gzip_ratio'] for r in results) / len(results)
        avg_gap = (avg_logsim / avg_gzip) * 100
        
        print("-" * 80)
        print(f"{'AVERAGE':<15} {'':12} {avg_logsim:>5.2f}x              "
              f"{avg_gzip:>5.2f}x              {avg_gap:>6.1f}%")
        
        print(f"\n✅ Average compression: {avg_logsim:.2f}x ({avg_gap:.1f}% of gzip)")
        print(f"   Improvement needed: {(100 - avg_gap):.1f}% to match gzip")
    
    # Save results
    output_path = Path('results/benchmark_comprehensive.json')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump({
            'version': '1.0',
            'improvements': ['varint_full', 'pattern_rle', 'zstd_dict'],
            'results': results,
            'summary': {
                'avg_logsim_ratio': round(avg_logsim, 2),
                'avg_gzip_ratio': round(avg_gzip, 2),
                'gap_percent': round(avg_gap, 1)
            }
        }, f, indent=2)
    
    print(f"\n💾 Results saved to {output_path}")


if __name__ == '__main__':
    main()
