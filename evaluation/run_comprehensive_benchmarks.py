#!/usr/bin/env python3
"""
Comprehensive Benchmarking Script

Compares logpress against:
1. Generic compression tools (gzip, bzip2, xz, zstd, lz4)
2. Log compression tools (logreduce)
3. Query performance (selective vs full decompression)
4. Compression throughput (logs/second)

Note: We compare COMPRESSION RATIOS only, not schema extraction accuracy.
      LogReducer uses lossy compression (cannot reconstruct exact logs).

Usage:
    python evaluation/run_comprehensive_benchmarks.py
    
Output:
    evaluation/results/comprehensive_benchmarks_YYYY-MM-DD_HH-MM-SS.json
    evaluation/results/comprehensive_benchmarks_YYYY-MM-DD_HH-MM-SS.md
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import subprocess
import time
import json
from datetime import datetime
from collections import defaultdict
import shutil
import tempfile

from logpress.services.compressor import SemanticCompressor
from logpress.services.query_engine import QueryEngine

# Try to import logreduce (optional)
try:
    import logreduce
    LOGREDUCE_AVAILABLE = True
except ImportError:
    LOGREDUCE_AVAILABLE = False


def discover_datasets(data_dir='data/datasets'):
    """Auto-discover all log datasets"""
    datasets_path = Path(data_dir)
    datasets = []
    
    for dataset_dir in datasets_path.iterdir():
        if not dataset_dir.is_dir():
            continue
            
        # Try multiple naming patterns
        patterns = [
            f"{dataset_dir.name}_full.log",
            f"{dataset_dir.name}.log",
            f"{dataset_dir.name.lower()}_full.log",
            f"{dataset_dir.name.lower()}.log"
        ]
        
        for pattern in patterns:
            log_file = dataset_dir / pattern
            if log_file.exists():
                datasets.append({
                    'name': dataset_dir.name,
                    'path': log_file,
                    'size': log_file.stat().st_size
                })
                break
    
    return sorted(datasets, key=lambda d: d['name'])


def measure_generic_compression(tool, level, log_file):
    """
    Measure generic compression tool performance
    
    Args:
        tool: Command name (gzip, bzip2, xz, zstd, lz4)
        level: Compression level string (e.g., '-9')
        log_file: Path to log file
    
    Returns:
        dict with ratio, time, speed_mbps
    """
    print(f"  Testing {tool} {level}...", end=' ', flush=True)
    
    # Check if tool is available
    if not shutil.which(tool):
        print(f"❌ NOT INSTALLED")
        return None
    
    output_file = Path(f"/tmp/{log_file.name}.{tool}")
    
    try:
        # Compress
        start = time.time()
        if tool == 'gzip':
            subprocess.run(['gzip', level, '-c', str(log_file)], 
                         stdout=open(output_file, 'wb'), check=True, stderr=subprocess.DEVNULL)
        elif tool == 'bzip2':
            subprocess.run(['bzip2', level, '-c', str(log_file)], 
                         stdout=open(output_file, 'wb'), check=True, stderr=subprocess.DEVNULL)
        elif tool == 'xz':
            subprocess.run(['xz', level, '-c', str(log_file)], 
                         stdout=open(output_file, 'wb'), check=True, stderr=subprocess.DEVNULL)
        elif tool == 'zstd':
            subprocess.run(['zstd', level, '-q', '-c', str(log_file)], 
                         stdout=open(output_file, 'wb'), check=True, stderr=subprocess.DEVNULL)
        elif tool == 'lz4':
            subprocess.run(['lz4', level, '-c', str(log_file)], 
                         stdout=open(output_file, 'wb'), check=True, stderr=subprocess.DEVNULL)
        else:
            raise ValueError(f"Unknown tool: {tool}")
        
        compress_time = time.time() - start
        
        # Get sizes
        original_size = log_file.stat().st_size
        compressed_size = output_file.stat().st_size
        ratio = original_size / compressed_size
        speed_mbps = (original_size / 1024 / 1024) / compress_time
        
        # Cleanup
        output_file.unlink()
        
        print(f"✓ {ratio:.2f}× in {compress_time:.2f}s ({speed_mbps:.1f} MB/s)")
        
        return {
            'ratio': ratio,
            'time': compress_time,
            'speed_mbps': speed_mbps,
            'compressed_bytes': compressed_size
        }
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return None


def measure_logreduce_compression(log_file, dataset_name):
    """
    Measure LogReducer compression performance
    
    Note: LogReducer is LOSSY compression - it removes duplicate/similar log lines.
          We measure compression ratio only, not reconstruction accuracy.
    """
    print(f"  Testing logreduce...", end=' ', flush=True)
    
    if not LOGREDUCE_AVAILABLE:
        print(f"❌ NOT INSTALLED (pip install logreduce)")
        return None
    
    try:
        # Create temporary output file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as tmp_out:
            output_file = Path(tmp_out.name)
        
        # Run logreduce (it processes logs and outputs reduced version)
        start = time.time()
        
        # LogReduce CLI: logreduce diff <baseline> <target>
        # For compression benchmark, we use the file as both baseline and target
        # This measures how much logreduce can compress by removing similar lines
        result = subprocess.run(
            ['logreduce', 'diff', '--html', 'none', str(log_file), str(log_file)],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        compress_time = time.time() - start
        
        # LogReduce output goes to stdout, count lines
        reduced_lines = result.stdout.strip().split('\n') if result.stdout.strip() else []
        reduced_size = len(result.stdout.encode('utf-8'))
        
        original_size = log_file.stat().st_size
        ratio = original_size / reduced_size if reduced_size > 0 else 0
        speed_mbps = (original_size / 1024 / 1024) / compress_time if compress_time > 0 else 0
        
        # Cleanup
        if output_file.exists():
            output_file.unlink()
        
        print(f"✓ {ratio:.2f}× in {compress_time:.2f}s ({speed_mbps:.1f} MB/s) [LOSSY]")
        
        return {
            'ratio': ratio,
            'time': compress_time,
            'speed_mbps': speed_mbps,
            'compressed_bytes': reduced_size,
            'reduced_lines': len(reduced_lines),
            'lossy': True  # Mark as lossy compression
        }
        
    except subprocess.TimeoutExpired:
        print(f"❌ TIMEOUT (>5 minutes)")
        return None
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return None


def measure_logpress_compression(log_file, dataset_name):
    """Measure logpress compression performance"""
    print(f"  Testing logpress...", end=' ', flush=True)
    
    # Load logs
    logs = []
    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if line:
                logs.append(line)
    
    # Compress
    compressor = SemanticCompressor()
    start = time.time()
    compressed_data, stats = compressor.compress(logs, verbose=False)
    compress_time = time.time() - start
    
    # Save to file to get actual compressed size
    compressed_file = Path('evaluation/compressed') / f"{dataset_name}.lsc"
    compressed_file.parent.mkdir(exist_ok=True, parents=True)
    compressor.cd = compressed_data  # Set the compressed data
    compressor.save(compressed_file, verbose=False)
    
    # Get stats
    original_size = log_file.stat().st_size
    compressed_size = compressed_file.stat().st_size
    ratio = original_size / compressed_size
    speed_mbps = (original_size / 1024 / 1024) / compress_time
    logs_per_second = len(logs) / compress_time
    
    print(f"✓ {ratio:.2f}× in {compress_time:.2f}s ({speed_mbps:.1f} MB/s, {logs_per_second:.0f} logs/s)")
    
    return {
        'ratio': ratio,
        'time': compress_time,
        'speed_mbps': speed_mbps,
        'compressed_bytes': compressed_size,
        'logs': len(logs),
        'logs_per_second': logs_per_second,
        'templates': stats.template_count
    }


def benchmark_queries(compressed_file, original_file, dataset_name):
    """
    Benchmark query performance: logpress vs grep baseline
    
    Returns:
        dict mapping query_name to {logpress_ms, baseline_ms, speedup}
    """
    print(f"  Benchmarking queries...")
    
    # Load compressed data
    engine = QueryEngine()
    engine.load(compressed_file)
    compressed_data = engine.compressed
    
    # Count all logs (no decompression needed - metadata only)
    start = time.time()
    total_logs = compressed_data.original_count
    logpress_count_time = (time.time() - start) * 1000  # ms
    
    # Baseline: wc -l
    start = time.time()
    result = subprocess.run(['wc', '-l', str(original_file)], 
                          capture_output=True, text=True, check=True)
    baseline_count_time = (time.time() - start) * 1000  # ms
    
    results = {
        'count_all': {
            'logpress_ms': logpress_count_time,
            'baseline_ms': baseline_count_time,
            'speedup': baseline_count_time / logpress_count_time if logpress_count_time > 0 else 0
        }
    }
    
    # Query by severity (if available)
    try:
        start = time.time()
        error_logs = engine.query_by_severity(compressed_data, 'ERROR')
        logpress_severity_time = (time.time() - start) * 1000  # ms
        
        # Baseline: grep -c "ERROR"
        start = time.time()
        subprocess.run(['grep', '-c', 'ERROR', str(original_file)], 
                      capture_output=True, check=True)
        baseline_severity_time = (time.time() - start) * 1000  # ms
        
        results['severity_error'] = {
            'logpress_ms': logpress_severity_time,
            'baseline_ms': baseline_severity_time,
            'speedup': baseline_severity_time / logpress_severity_time if logpress_severity_time > 0 else 0,
            'results_count': len(error_logs)
        }
        print(f"    ✓ Severity query: {baseline_severity_time/logpress_severity_time:.2f}× speedup")
    except Exception as e:
        print(f"    ⚠ Severity query skipped: {e}")
    
    # Query by IP (if available)
    try:
        # Find an IP in the logs first
        with open(original_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                import re
                ip_match = re.search(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', line)
                if ip_match:
                    test_ip = ip_match.group()
                    break
            else:
                raise ValueError("No IP found in logs")
        
        start = time.time()
        ip_logs = engine.query_by_ip(compressed_data, test_ip)
        logpress_ip_time = (time.time() - start) * 1000  # ms
        
        # Baseline: grep -c "IP"
        start = time.time()
        subprocess.run(['grep', '-c', test_ip, str(original_file)], 
                      capture_output=True, check=True)
        baseline_ip_time = (time.time() - start) * 1000  # ms
        
        results['ip_filter'] = {
            'logpress_ms': logpress_ip_time,
            'baseline_ms': baseline_ip_time,
            'speedup': baseline_ip_time / logpress_ip_time if logpress_ip_time > 0 else 0,
            'results_count': len(ip_logs),
            'test_ip': test_ip
        }
        print(f"    ✓ IP query: {baseline_ip_time/logpress_ip_time:.2f}× speedup")
    except Exception as e:
        print(f"    ⚠ IP query skipped: {e}")
    
    return results


def main():
    """Run comprehensive benchmarks"""
    print("=" * 80)
    print("COMPREHENSIVE BENCHMARKING")
    print("=" * 80)
    print()
    
    # Discover datasets
    datasets = discover_datasets()
    print(f"Found {len(datasets)} datasets:")
    for ds in datasets:
        print(f"  • {ds['name']}: {ds['size']/1024/1024:.2f} MB")
    print()
    
    all_results = []
    
    for ds in datasets:
        print(f"📊 Benchmarking: {ds['name']}")
        print("-" * 80)
        
        result = {
            'dataset': ds['name'],
            'original_bytes': ds['size'],
            'tools': {}
        }
        
        # Test generic compression tools
        tools = [
            ('gzip', '-9'),
            ('bzip2', '-9'),
            ('xz', '-9'),
            ('zstd', '-15'),
            ('lz4', '-9')
        ]
        
        for tool, level in tools:
            tool_result = measure_generic_compression(tool, level, ds['path'])
            if tool_result:
                result['tools'][f"{tool}{level.replace('-', '')}"] = tool_result
        
        # Test LogReducer (lossy compression)
        logreduce_result = measure_logreduce_compression(ds['path'], ds['name'])
        if logreduce_result:
            result['tools']['logreduce'] = logreduce_result
        
        # Test logpress
        logpress_result = measure_logpress_compression(ds['path'], ds['name'])
        result['tools']['logpress'] = logpress_result
        
        # Benchmark queries (if logpress compression succeeded)
        compressed_file = Path('evaluation/compressed') / f"{ds['name']}.lsc"
        if compressed_file.exists():
            query_results = benchmark_queries(compressed_file, ds['path'], ds['name'])
            result['queries'] = query_results
        
        all_results.append(result)
        print()
    
    # Save results
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    results_dir = Path('evaluation/results')
    results_dir.mkdir(exist_ok=True, parents=True)
    
    # JSON output
    json_file = results_dir / f"comprehensive_benchmarks_{timestamp}.json"
    with open(json_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'datasets': all_results
        }, f, indent=2)
    print(f"✓ JSON results saved to: {json_file}")
    
    # Markdown output
    md_file = results_dir / f"comprehensive_benchmarks_{timestamp}.md"
    with open(md_file, 'w') as f:
        f.write("# Comprehensive Benchmark Results\n\n")
        f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Compression comparison table
        f.write("## Compression Ratio Comparison\n\n")
        f.write("**Note**: LogReducer uses lossy compression (cannot reconstruct exact logs). All other tools are lossless.\n\n")
        f.write("| Dataset | gzip-9 | bzip2-9 | xz-9 | zstd-15 | lz4-9 | logreduce | **logpress** | Best Lossless |\n")
        f.write("|---------|--------|---------|------|---------|-------|-----------|------------|---------------|\n")
        
        for r in all_results:
            tools = r['tools']
            row = [r['dataset']]
            ratios = []
            
            for tool_name in ['gzip9', 'bzip29', 'xz9', 'zstd15', 'lz49', 'logreduce', 'logpress']:
                if tool_name in tools:
                    ratio = tools[tool_name]['ratio']
                    lossy_marker = " ⚠️" if tools[tool_name].get('lossy', False) else ""
                    row.append(f"{ratio:.2f}×{lossy_marker}")
                    if not tools[tool_name].get('lossy', False):  # Only lossless tools compete for "best"
                        ratios.append((ratio, tool_name))
                else:
                    row.append("—")
            
            best_ratio, best_tool = max(ratios) if ratios else (0, "—")
            row.append(best_tool.upper())
            
            f.write("| " + " | ".join(row) + " |\n")
        
        # Speed comparison table
        f.write("\n## Compression Speed Comparison (MB/s)\n\n")
        f.write("| Dataset | gzip-9 | bzip2-9 | xz-9 | zstd-15 | lz4-9 | logreduce | **logpress** |\n")
        f.write("|---------|--------|---------|------|---------|-------|-----------|------------|\n")
        
        for r in all_results:
            tools = r['tools']
            row = [r['dataset']]
            
            for tool_name in ['gzip9', 'bzip29', 'xz9', 'zstd15', 'lz49', 'logreduce', 'logpress']:
                if tool_name in tools:
                    speed = tools[tool_name]['speed_mbps']
                    row.append(f"{speed:.1f}")
                else:
                    row.append("—")
            
            f.write("| " + " | ".join(row) + " |\n")
        
        # Query performance
        f.write("\n## Query Performance\n\n")
        f.write("Comparison: logpress selective decompression vs grep on uncompressed logs\n\n")
        
        for r in all_results:
            if 'queries' not in r:
                continue
            
            f.write(f"### {r['dataset']}\n\n")
            f.write("| Query | logpress (ms) | Baseline (ms) | Speedup |\n")
            f.write("|-------|-------------|---------------|----------|\n")
            
            for query_name, query_result in r['queries'].items():
                f.write(f"| {query_name} | {query_result['logpress_ms']:.2f} | "
                       f"{query_result['baseline_ms']:.2f} | "
                       f"{query_result['speedup']:.2f}× |\n")
            f.write("\n")
    
    print(f"✓ Markdown results saved to: {md_file}")
    print()
    print("=" * 80)
    print("✅ COMPREHENSIVE BENCHMARKING COMPLETE")
    print("=" * 80)


if __name__ == '__main__':
    main()
