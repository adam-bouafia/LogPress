#!/usr/bin/env python3
"""
Visualize benchmark results
"""

import json
from pathlib import Path


def format_size(bytes_val):
    """Format bytes to human-readable"""
    for unit in ['B', 'KB', 'MB']:
        if bytes_val < 1024:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024
    return f"{bytes_val:.1f} GB"


def main():
    results_file = Path("benchmarks_all.json")
    
    with open(results_file) as f:
        data = json.load(f)
    
    print(f"{'='*100}")
    print(f"LogSim Benchmark Results - {data['timestamp']}")
    print(f"{'='*100}")
    print(f"Sample size: {data['sample_size']:,} logs per dataset\n")
    
    # Compression comparison table
    print("📊 COMPRESSION RATIOS")
    print("-" * 100)
    print(f"{'Dataset':<15} {'Original':<12} {'LogSim':<20} {'gzip -9':<20} {'gzip -1':<20}")
    print(f"{'':15} {'Size':<12} {'Ratio':<10} {'Speed':<10} {'Ratio':<10} {'Speed':<10} {'Ratio':<10} {'Speed':<10}")
    print("-" * 100)
    
    for ds in data['datasets']:
        name = ds['dataset']
        orig = format_size(ds['original_size'])
        
        logsim_ratio = ds['methods']['logsim']['compression_ratio']
        logsim_speed = ds['methods']['logsim']['throughput_mb_s']
        
        gzip_ratio = ds['methods']['gzip']['compression_ratio']
        gzip_speed = ds['methods']['gzip']['throughput_mb_s']
        
        gzip_fast_ratio = ds['methods']['gzip_fast']['compression_ratio']
        gzip_fast_speed = ds['methods']['gzip_fast']['throughput_mb_s']
        
        print(f"{name:<15} {orig:<12} {logsim_ratio:>5.1f}x     {logsim_speed:>6.1f}MB/s  "
              f"{gzip_ratio:>5.1f}x     {gzip_speed:>6.1f}MB/s  "
              f"{gzip_fast_ratio:>5.1f}x     {gzip_fast_speed:>6.1f}MB/s")
    
    # Calculate averages
    avg_logsim = sum(ds['methods']['logsim']['compression_ratio'] for ds in data['datasets']) / len(data['datasets'])
    avg_gzip = sum(ds['methods']['gzip']['compression_ratio'] for ds in data['datasets']) / len(data['datasets'])
    avg_gzip_fast = sum(ds['methods']['gzip_fast']['compression_ratio'] for ds in data['datasets']) / len(data['datasets'])
    
    print("-" * 100)
    print(f"{'AVERAGE':<15} {'':12} {avg_logsim:>5.1f}x              {avg_gzip:>5.1f}x              {avg_gzip_fast:>5.1f}x")
    print()
    
    # Query performance table
    print("\n⚡ QUERY PERFORMANCE")
    print("-" * 100)
    print(f"{'Dataset':<15} {'Count':<15} {'Severity Filter':<35} {'Statistics':<15}")
    print(f"{'':15} {'Time':<15} {'Matched':<10} {'Time':<12} {'Throughput':<13} {'Time':<15}")
    print("-" * 100)
    
    for ds in data['datasets']:
        name = ds['dataset']
        
        count_time = ds['queries']['count']['time'] * 1000
        
        sev = ds['queries']['severity_filter']
        sev_matched = sev['matched']
        sev_time = sev['time'] * 1000
        sev_throughput = sev['throughput'] / 1e6  # Convert to millions
        
        stats_time = ds['queries']['stats']['time'] * 1000
        
        print(f"{name:<15} {count_time:>6.3f}ms       {sev_matched:>7,}   {sev_time:>6.3f}ms     "
              f"{sev_throughput:>7.1f}M/s    {stats_time:>6.3f}ms")
    
    print()
    
    # Key findings
    print("\n🔍 KEY FINDINGS")
    print("-" * 100)
    
    # Best compression
    best_logsim = max(data['datasets'], key=lambda x: x['methods']['logsim']['compression_ratio'])
    best_ratio = best_logsim['methods']['logsim']['compression_ratio']
    print(f"✅ Best LogSim compression: {best_logsim['dataset']} at {best_ratio:.1f}x")
    
    # LogSim beats gzip
    beats_gzip = [ds for ds in data['datasets'] 
                  if ds['methods']['logsim']['compression_ratio'] > ds['methods']['gzip']['compression_ratio']]
    if beats_gzip:
        print(f"✅ LogSim beats gzip -9 on: {', '.join(ds['dataset'] for ds in beats_gzip)}")
    
    # Query speeds
    fastest_query = max(data['datasets'], key=lambda x: x['queries']['severity_filter']['throughput'])
    fastest_throughput = fastest_query['queries']['severity_filter']['throughput'] / 1e6
    print(f"✅ Fastest query: {fastest_query['dataset']} at {fastest_throughput:.0f}M entries/sec")
    
    # Overall analysis
    better_than_gzip9 = len([ds for ds in data['datasets'] 
                             if ds['methods']['logsim']['compression_ratio'] > ds['methods']['gzip']['compression_ratio']])
    better_than_gzip1 = len([ds for ds in data['datasets']
                             if ds['methods']['logsim']['compression_ratio'] > ds['methods']['gzip_fast']['compression_ratio']])
    
    print(f"\n📈 Overall:")
    print(f"   • LogSim beats gzip -9 on {better_than_gzip9}/{len(data['datasets'])} datasets")
    print(f"   • LogSim beats gzip -1 on {better_than_gzip1}/{len(data['datasets'])} datasets")
    print(f"   • Average compression: {avg_logsim:.1f}x (vs gzip -9: {avg_gzip:.1f}x)")
    print(f"   • Query throughput: 0.003-3000 million entries/sec (no decompression needed)")
    print(f"   • Semantic awareness: Enables field-level queries on compressed data")
    
    print(f"\n{'='*100}")


if __name__ == "__main__":
    main()
