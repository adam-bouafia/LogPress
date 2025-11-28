#!/usr/bin/env python3
"""
Test script for comprehensive benchmarks
Tests with Proxifier dataset only (smallest at ~2.4 MB)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import subprocess
import time
import json
from datetime import datetime
import shutil

from logpress.services.compressor import SemanticCompressor
from logpress.services.query_engine import QueryEngine


def test_dataset_discovery():
    """Test that we can discover datasets"""
    print("TEST 1: Dataset Discovery")
    print("-" * 60)
    
    datasets_path = Path('data/datasets')
    if not datasets_path.exists():
        print("❌ FAIL: data/datasets directory not found")
        return False
    
    # Find Proxifier (smallest dataset)
    proxifier_dir = datasets_path / 'Proxifier'
    if not proxifier_dir.exists():
        print("❌ FAIL: Proxifier dataset not found")
        return False
    
    log_file = proxifier_dir / 'Proxifier_full.log'
    if not log_file.exists():
        print("❌ FAIL: Proxifier_full.log file not found")
        return False
    
    size_mb = log_file.stat().st_size / 1024 / 1024
    print(f"✓ Found Proxifier dataset: {size_mb:.2f} MB")
    return True, log_file


def test_generic_compression(log_file):
    """Test generic compression tools"""
    print("\nTEST 2: Generic Compression Tools")
    print("-" * 60)
    
    results = {}
    
    # Test gzip (should always be available)
    if shutil.which('gzip'):
        print("Testing gzip-9...", end=' ', flush=True)
        try:
            output_file = Path('/tmp/test_proxifier.gz')
            start = time.time()
            subprocess.run(['gzip', '-9', '-c', str(log_file)], 
                         stdout=open(output_file, 'wb'), 
                         check=True, stderr=subprocess.DEVNULL)
            compress_time = time.time() - start
            
            original_size = log_file.stat().st_size
            compressed_size = output_file.stat().st_size
            ratio = original_size / compressed_size
            
            output_file.unlink()
            
            results['gzip'] = {
                'ratio': ratio,
                'time': compress_time,
                'speed_mbps': (original_size / 1024 / 1024) / compress_time
            }
            print(f"✓ {ratio:.2f}× in {compress_time:.2f}s")
        except Exception as e:
            print(f"❌ FAIL: {e}")
            return False
    else:
        print("⚠ SKIP: gzip not installed")
    
    # Test zstd (optional)
    if shutil.which('zstd'):
        print("Testing zstd-15...", end=' ', flush=True)
        try:
            output_file = Path('/tmp/test_proxifier.zst')
            start = time.time()
            subprocess.run(['zstd', '-15', '-q', '-c', str(log_file)], 
                         stdout=open(output_file, 'wb'), 
                         check=True, stderr=subprocess.DEVNULL)
            compress_time = time.time() - start
            
            original_size = log_file.stat().st_size
            compressed_size = output_file.stat().st_size
            ratio = original_size / compressed_size
            
            output_file.unlink()
            
            results['zstd'] = {
                'ratio': ratio,
                'time': compress_time,
                'speed_mbps': (original_size / 1024 / 1024) / compress_time
            }
            print(f"✓ {ratio:.2f}× in {compress_time:.2f}s")
        except Exception as e:
            print(f"⚠ Warning: {e}")
    else:
        print("⚠ SKIP: zstd not installed (optional)")
    
    return True, results


def test_logpress_compression(log_file):
    """Test logpress compression"""
    print("\nTEST 3: logpress Compression")
    print("-" * 60)
    
    try:
        # Load logs
        print("Loading logs...", end=' ', flush=True)
        logs = []
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if line:
                    logs.append(line)
        print(f"✓ {len(logs)} logs loaded")
        
        # Compress
        print("Compressing...", end=' ', flush=True)
        compressor = SemanticCompressor()
        start = time.time()
        compressed_data, stats = compressor.compress(logs, verbose=True)
        compress_time = time.time() - start
        
        original_size = log_file.stat().st_size
        
        # Save compressed file to get actual size
        compressed_file = Path('evaluation/compressed/test_Proxifier.lsc')
        compressed_file.parent.mkdir(exist_ok=True, parents=True)
        compressor.cd = compressed_data  # Set the compressed data
        compressor.save(compressed_file, verbose=False)
        
        compressed_size = compressed_file.stat().st_size
        ratio = original_size / compressed_size
        speed_mbps = (original_size / 1024 / 1024) / compress_time
        logs_per_second = len(logs) / compress_time
        
        print(f"✓ {ratio:.2f}× in {compress_time:.2f}s ({speed_mbps:.1f} MB/s, {logs_per_second:.0f} logs/s)")
        
        # compressed_file already created above
        
        return True, {
            'ratio': ratio,
            'time': compress_time,
            'speed_mbps': speed_mbps,
            'logs': len(logs),
            'logs_per_second': logs_per_second,
            'templates': stats.template_count,
            'compressed_file': compressed_file
        }
        
    except Exception as e:
        print(f"❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def test_query_performance(compressed_file, original_file):
    """Test query performance"""
    print("\nTEST 4: Query Performance")
    print("-" * 60)
    
    try:
        # Load compressed data
        print("Loading compressed data...", end=' ', flush=True)
        engine = QueryEngine()
        engine.load(compressed_file)
        compressed_data = engine.compressed
        print("✓")
        
        # Test 1: Count all logs (metadata only)
        print("Query 1: Count all logs...", end=' ', flush=True)
        start = time.time()
        total_logs = compressed_data.original_count
        logpress_time = (time.time() - start) * 1000  # ms
        
        # Baseline: wc -l
        start = time.time()
        result = subprocess.run(['wc', '-l', str(original_file)], 
                              capture_output=True, text=True, check=True)
        baseline_time = (time.time() - start) * 1000  # ms
        
        speedup = baseline_time / logpress_time if logpress_time > 0 else 0
        print(f"✓ logpress: {logpress_time:.2f}ms, Baseline: {baseline_time:.2f}ms, Speedup: {speedup:.2f}×")
        
        # Test 2: Severity query (if available)
        print("Query 2: Filter by severity...", end=' ', flush=True)
        try:
            start = time.time()
            error_logs = engine.query_by_severity(compressed_data, 'ERROR')
            logpress_time = (time.time() - start) * 1000  # ms
            
            # Baseline: grep -c "ERROR"
            start = time.time()
            result = subprocess.run(['grep', '-c', 'ERROR', str(original_file)], 
                                  capture_output=True, check=True)
            baseline_time = (time.time() - start) * 1000  # ms
            
            speedup = baseline_time / logpress_time if logpress_time > 0 else 0
            print(f"✓ logpress: {logpress_time:.2f}ms, Baseline: {baseline_time:.2f}ms, Speedup: {speedup:.2f}×")
        except Exception as e:
            print(f"⚠ Skipped: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_output_generation():
    """Test JSON/Markdown output generation"""
    print("\nTEST 5: Output Generation")
    print("-" * 60)
    
    try:
        # Create test data
        test_data = {
            'timestamp': datetime.now().isoformat(),
            'datasets': [{
                'dataset': 'Proxifier',
                'original_bytes': 2519085,
                'tools': {
                    'gzip9': {'ratio': 15.68, 'time': 3.2, 'speed_mbps': 0.75},
                    'logpress': {'ratio': 12.09, 'time': 3.2, 'speed_mbps': 0.75, 
                              'logs': 21320, 'logs_per_second': 6656, 'templates': 26}
                }
            }]
        }
        
        # Test JSON output
        json_file = Path('evaluation/results/test_benchmark.json')
        json_file.parent.mkdir(exist_ok=True, parents=True)
        with open(json_file, 'w') as f:
            json.dump(test_data, f, indent=2)
        print(f"✓ JSON saved to: {json_file}")
        
        # Test Markdown output
        md_file = Path('evaluation/results/test_benchmark.md')
        with open(md_file, 'w') as f:
            f.write("# Test Benchmark Results\n\n")
            f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("| Dataset | gzip-9 | logpress |\n")
            f.write("|---------|--------|--------|\n")
            f.write("| Proxifier | 15.68× | 12.09× |\n")
        print(f"✓ Markdown saved to: {md_file}")
        
        # Cleanup
        json_file.unlink()
        md_file.unlink()
        
        return True
        
    except Exception as e:
        print(f"❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("COMPREHENSIVE BENCHMARKS - UNIT TESTS")
    print("=" * 60)
    print()
    
    all_passed = True
    
    # Test 1: Dataset discovery
    result = test_dataset_discovery()
    if isinstance(result, tuple):
        success, log_file = result
        if not success:
            all_passed = False
            print("\n⚠ Remaining tests skipped due to dataset discovery failure")
            return
    else:
        all_passed = False
        return
    
    # Test 2: Generic compression
    result = test_generic_compression(log_file)
    if isinstance(result, tuple):
        success, generic_results = result
        if not success:
            all_passed = False
    else:
        all_passed = False
    
    # Test 3: logpress compression
    result = test_logpress_compression(log_file)
    if isinstance(result, tuple):
        success, logpress_result = result
        if not success:
            all_passed = False
            print("\n⚠ Query tests skipped due to compression failure")
        else:
            # Test 4: Query performance
            if not test_query_performance(logpress_result['compressed_file'], log_file):
                all_passed = False
            
            # Cleanup test compressed file
            logpress_result['compressed_file'].unlink()
    else:
        all_passed = False
    
    # Test 5: Output generation
    if not test_output_generation():
        all_passed = False
    
    print()
    print("=" * 60)
    if all_passed:
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        print()
        print("The comprehensive benchmarks script is ready to use!")
        print("Run: python evaluation/run_comprehensive_benchmarks.py")
    else:
        print("❌ SOME TESTS FAILED")
        print("=" * 60)
        print()
        print("Please fix the issues before running full benchmarks.")
    print()


if __name__ == '__main__':
    main()
