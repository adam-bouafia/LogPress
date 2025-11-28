#!/usr/bin/env python3
"""
Query Performance Benchmarking

Tests selective decompression performance against full decompression baseline.
Measures speedup achieved by columnar access and predicate pushdown.
"""

import sys
import time
import gzip
import json
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Any
from datetime import datetime

# Ensure project root is on sys.path so imports like `logpress.*` work
sys.path.insert(0, str(Path(__file__).parent.parent))

from logpress.services.query_engine import QueryEngine


@dataclass
class QueryBenchmark:
    """Results for a single query"""
    query_name: str
    query_description: str
    logpress_time_ms: float
    baseline_time_ms: float
    speedup: float
    rows_matched: int
    total_rows: int
    bytes_decompressed: int
    total_bytes: int


def benchmark_query(query_engine: QueryEngine, query_name: str, query_desc: str,
                   query_func, baseline_func, total_rows: int = 0) -> QueryBenchmark:
    """
    Benchmark a single query
    
    Args:
        query_engine: QueryEngine instance
        query_name: Short name (e.g., "severity_filter")
        query_desc: Description (e.g., "WHERE severity='ERROR'")
        query_func: Function that executes query on QueryEngine
        baseline_func: Function that executes same query on raw decompressed data
    """
    print(f"  Testing: {query_name}")
    print(f"    {query_desc}")
    
    # Warm-up run
    _ = query_func(query_engine)
    
    # logpress query (3 runs, take average)
    logpress_times = []
    for _ in range(3):
        start = time.perf_counter()
        result = query_func(query_engine)
        end = time.perf_counter()
        logpress_times.append((end - start) * 1000)  # Convert to ms
    
    logpress_time = sum(logpress_times) / len(logpress_times)
    rows_matched = len(result) if isinstance(result, list) else (result.matched_count if hasattr(result, 'matched_count') else 1)
    
    # Baseline (full decompression + filter)
    baseline_times = []
    for _ in range(3):
        start = time.perf_counter()
        baseline_result = baseline_func()
        end = time.perf_counter()
        baseline_times.append((end - start) * 1000)
    
    baseline_time = sum(baseline_times) / len(baseline_times)
    
    speedup = baseline_time / logpress_time if logpress_time > 0 else 0
    
    print(f"    logpress:   {logpress_time:.2f} ms ({rows_matched:,} rows)")
    print(f"    Baseline: {baseline_time:.2f} ms")
    print(f"    Speedup:  {speedup:.1f}x")
    print()
    
    return QueryBenchmark(
        query_name=query_name,
        query_description=query_desc,
        logpress_time_ms=logpress_time,
        baseline_time_ms=baseline_time,
        speedup=speedup,
        rows_matched=rows_matched,
        total_rows=total_rows,
        bytes_decompressed=0,  # TODO: Track bytes
        total_bytes=0
    )


def benchmark_dataset(dataset_name: str, compressed_file: Path, 
                     original_file: Path) -> List[QueryBenchmark]:
    """Run all query benchmarks on a dataset"""
    
    print("=" * 80)
    print(f"QUERY BENCHMARKS: {dataset_name}")
    print("=" * 80)
    print()
    
    # Load compressed data
    print(f"📂 Loading compressed data: {compressed_file}")
    query_engine = QueryEngine(str(compressed_file))
    log_count = query_engine.compressed.original_count if query_engine.compressed else 0
    print()
    
    # Load original data for baseline
    print(f"📂 Loading original logs for baseline: {original_file}")
    original_logs = []
    with open(original_file, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if line:
                original_logs.append(line)
    print(f"✓ Loaded {len(original_logs):,} logs")
    print()
    
    benchmarks = []
    
    # Query 1: Count all logs (metadata only)
    print("🔍 Query 1: COUNT(*)")
    benchmarks.append(benchmark_query(
        query_engine,
        "count_all",
        "SELECT COUNT(*)",
        lambda qe: qe.count_all(),
        lambda: len(original_logs),
        log_count
    ))
    
    # Query 2: Filter by severity (if Apache/Zookeeper)
    if dataset_name in ['Apache', 'Zookeeper']:
        print("🔍 Query 2: Severity Filter")
        benchmarks.append(benchmark_query(
            query_engine,
            "severity_error",
            "SELECT * WHERE severity='error' OR severity='ERROR'",
            lambda qe: qe.query_by_severity(['error', 'ERROR']),
            lambda: [log for log in original_logs if 'error' in log.lower() or 'ERROR' in log],
            log_count
        ))
    
    # Query 3: IP address filter (if applicable)
    if dataset_name in ['Apache', 'Proxifier', 'Zookeeper']:
        print("🔍 Query 3: IP Address Filter")
        # Extract common IP from first 1000 logs
        sample_ips = set()
        for log in original_logs[:1000]:
            import re
            ips = re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', log)
            sample_ips.update(ips)
        
        if sample_ips:
            target_ip = list(sample_ips)[0]
            print(f"    Target IP: {target_ip}")
            benchmarks.append(benchmark_query(
                query_engine,
                "ip_filter",
                f"SELECT * WHERE ip='{target_ip}'",
                lambda qe: qe.query_by_ip(target_ip),
                lambda: [log for log in original_logs if target_ip in log],
                log_count
            ))
    
    # Query 4: Timestamp range (if timestamps present)
    print("🔍 Query 4: Timestamp Range")
    # This would require parsing timestamps from logs - skip for now
    print("    (Skipped - requires timestamp parsing)")
    print()
    
    # Query 5: Combined filter (severity + keyword search)
    if dataset_name in ['Apache', 'Zookeeper']:
        print("🔍 Query 5: Combined Filter (Severity + Keyword)")
        keyword = "connection" if dataset_name == "Zookeeper" else "notice"
        benchmarks.append(benchmark_query(
            query_engine,
            "combined_filter",
            f"SELECT * WHERE severity contains '{keyword}'",
            lambda qe: qe.query_by_severity([keyword]),
            lambda: [log for log in original_logs if keyword.lower() in log.lower()],
            log_count
        ))
    
    return benchmarks


def main():
    """Run query benchmarks on all compressed datasets"""
    
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 78 + "║")
    print("║" + "logpress QUERY PERFORMANCE BENCHMARKS".center(78) + "║")
    print("║" + "Selective Decompression vs Full Decompression".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("╚" + "═" * 78 + "╝")
    print()
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Auto-discover compressed files and corresponding originals
    datasets = []
    compressed_dir = Path("evaluation/compressed")
    original_base = Path("data/datasets")
    possible_names = ["Apache", "BGL", "HDFS", "HPC", "HealthApp", "Linux", "Mac", "OpenStack", "Proxifier", "Zookeeper"]

    for name in possible_names:
        comp = compressed_dir / f"{name.lower()}_full.lsc"
        # also accept test naming
        if not comp.exists():
            comp = compressed_dir / f"{name.lower()}_test.lsc"
        if not comp.exists():
            continue

        # find original log
        orig = None
        for pattern in [f"{name}_full.log", f"{name}.log", f"{name.lower()}.log"]:
            candidate = original_base / name / pattern
            if candidate.exists():
                orig = candidate
                break

        if not orig:
            continue

        datasets.append((name, comp, orig))
    
    all_results = {}
    
    for dataset_name, compressed_file, original_file in datasets:
        if not compressed_file.exists():
            print(f"⚠ Skipping {dataset_name}: Compressed file not found ({compressed_file})")
            print()
            continue
        
        if not original_file.exists():
            print(f"⚠ Skipping {dataset_name}: Original file not found ({original_file})")
            print()
            continue
        
        try:
            benchmarks = benchmark_dataset(dataset_name, compressed_file, original_file)
            all_results[dataset_name] = benchmarks
        except Exception as e:
            print(f"❌ Error benchmarking {dataset_name}: {e}")
            import traceback
            traceback.print_exc()
            print()
    
    # Summary table
    print()
    print("╔" + "═" * 78 + "╗")
    print("║" + "SUMMARY: QUERY PERFORMANCE".center(78) + "║")
    print("╚" + "═" * 78 + "╝")
    print()
    
    print(f"{'Dataset':<12} | {'Query':<20} | {'logpress (ms)':>12} | {'Baseline (ms)':>14} | {'Speedup':>8}")
    print("-" * 80)
    
    for dataset_name, benchmarks in all_results.items():
        for i, bench in enumerate(benchmarks):
            ds = dataset_name if i == 0 else ""
            print(f"{ds:<12} | {bench.query_name:<20} | "
                  f"{bench.logpress_time_ms:>12.2f} | "
                  f"{bench.baseline_time_ms:>14.2f} | "
                  f"{bench.speedup:>7.1f}x")
    
    print()
    
    # Calculate averages
    all_speedups = [b.speedup for benchmarks in all_results.values() for b in benchmarks]
    if all_speedups:
        avg_speedup = sum(all_speedups) / len(all_speedups)
        min_speedup = min(all_speedups)
        max_speedup = max(all_speedups)
        
        print(f"Overall Query Performance:")
        print(f"  • Average speedup: {avg_speedup:.1f}x")
        print(f"  • Range: {min_speedup:.1f}x - {max_speedup:.1f}x")
        print()
    
    # Save results
    results_file = Path("results/query_performance.json")
    results_file.parent.mkdir(exist_ok=True)
    
    # Convert to serializable format
    results_dict = {}
    for dataset_name, benchmarks in all_results.items():
        results_dict[dataset_name] = [
            {
                'query_name': b.query_name,
                'query_description': b.query_description,
                'logpress_time_ms': b.logpress_time_ms,
                'baseline_time_ms': b.baseline_time_ms,
                'speedup': b.speedup,
                'rows_matched': b.rows_matched,
                'total_rows': b.total_rows
            }
            for b in benchmarks
        ]
    
    with open(results_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'datasets': results_dict,
            'summary': {
                'avg_speedup': avg_speedup if all_speedups else 0,
                'min_speedup': min_speedup if all_speedups else 0,
                'max_speedup': max_speedup if all_speedups else 0,
                'total_queries': len(all_speedups)
            }
        }, f, indent=2)
    
    print(f"✓ Results saved to {results_file}")
    print()
    print("=" * 80)
    print("QUERY BENCHMARKS COMPLETE")
    print("=" * 80)


if __name__ == '__main__':
    main()
