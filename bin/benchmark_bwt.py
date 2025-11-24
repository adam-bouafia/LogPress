#!/usr/bin/env python
"""
Quick BWT benchmark to test compression improvement potential

This script tests BWT preprocessing on MessagePack data before Zstd compression
to estimate the potential gain from Phase 2 implementation.
"""

import sys
import time
from pathlib import Path
import zstandard as zstd
import msgpack

# Add logsim to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from logsim.compressor import LogCompressionEngine
from logsim.bwt import bwt_transform, bwt_inverse


def benchmark_bwt_on_dataset(dataset_path: Path, dataset_name: str):
    """Benchmark BWT preprocessing on a single dataset"""
    print(f"\n{'='*60}")
    print(f"Testing: {dataset_name}")
    print(f"{'='*60}")
    
    # Load raw logs
    with open(dataset_path, 'r', encoding='utf-8', errors='ignore') as f:
        logs = [line.rstrip('\n') for line in f if line.strip()]
    
    print(f"Logs: {len(logs):,}")
    
    # Compress with LogSim
    engine = LogCompressionEngine()
    compressed_data, stats = engine.compress(logs)
    
    # Get MessagePack representation
    output = {
        'version': compressed_data.version,
        'templates': compressed_data.templates,
        'token_pool': compressed_data.token_pool,
        'template_token_refs': compressed_data.template_token_refs,
        'timestamps_varint': compressed_data.timestamps_varint,
        'timestamp_base': compressed_data.timestamp_base,
        'timestamp_count': compressed_data.timestamp_count,
        'severities_varint': compressed_data.severities_varint,
        'severity_count': compressed_data.severity_count,
        'ip_addresses_varint': compressed_data.ip_addresses_varint,
        'ip_count': compressed_data.ip_count,
        'messages_varint': compressed_data.messages_varint,
        'message_count': compressed_data.message_count,
        'severity_list': compressed_data.severity_list,
        'ip_list': compressed_data.ip_list,
        'message_list': compressed_data.message_list,
        'log_index_templates_rle': compressed_data.log_index_templates_rle,
        'log_index_fields_varint': compressed_data.log_index_fields_varint,
        'log_index_field_counts': compressed_data.log_index_field_counts,
        'original_count': compressed_data.original_count,
        'compressed_at': compressed_data.compressed_at
    }
    
    msgpack_data = msgpack.packb(output, use_bin_type=True)
    print(f"MessagePack size: {len(msgpack_data):,} bytes ({len(msgpack_data)/1024:.1f} KB)")
    
    # Load universal dictionary
    universal_dict_path = Path(__file__).parent.parent / "logsim" / "universal_dict.zstd"
    if universal_dict_path.exists():
        with open(universal_dict_path, 'rb') as f:
            universal_dict = f.read()
        print(f"Using universal dictionary: {len(universal_dict):,} bytes")
    else:
        universal_dict = None
        print("No universal dictionary found")
    
    # Baseline: MessagePack + Zstd (current approach)
    print("\n--- Baseline (no BWT) ---")
    start = time.time()
    if universal_dict:
        zdict = zstd.ZstdCompressionDict(universal_dict)
        cctx = zstd.ZstdCompressor(level=15, dict_data=zdict)
        baseline_compressed = cctx.compress(msgpack_data)
    else:
        baseline_compressed = zstd.compress(msgpack_data, level=15)
    baseline_time = time.time() - start
    
    print(f"Compressed size: {len(baseline_compressed):,} bytes ({len(baseline_compressed)/1024:.1f} KB)")
    print(f"Compression time: {baseline_time:.3f}s")
    print(f"Compression ratio: {len(msgpack_data) / len(baseline_compressed):.2f}x")
    
    # With BWT: MessagePack -> BWT -> Zstd
    print("\n--- With BWT preprocessing ---")
    start = time.time()
    bwt_data = bwt_transform(msgpack_data, block_size=1024*1024)  # 1MB blocks
    bwt_transform_time = time.time() - start
    
    print(f"BWT output: {len(bwt_data):,} bytes ({len(bwt_data)/1024:.1f} KB)")
    print(f"BWT time: {bwt_transform_time:.3f}s")
    
    start = time.time()
    if universal_dict:
        zdict = zstd.ZstdCompressionDict(universal_dict)
        cctx = zstd.ZstdCompressor(level=15, dict_data=zdict)
        bwt_compressed = cctx.compress(bwt_data)
    else:
        bwt_compressed = zstd.compress(bwt_data, level=15)
    zstd_time = time.time() - start
    
    total_time = bwt_transform_time + zstd_time
    
    print(f"Compressed size: {len(bwt_compressed):,} bytes ({len(bwt_compressed)/1024:.1f} KB)")
    print(f"Zstd time: {zstd_time:.3f}s")
    print(f"Total time: {total_time:.3f}s")
    print(f"Compression ratio: {len(msgpack_data) / len(bwt_compressed):.2f}x")
    
    # Compare
    print("\n--- Improvement ---")
    size_improvement = (len(baseline_compressed) - len(bwt_compressed)) / len(baseline_compressed) * 100
    ratio_improvement = (len(msgpack_data) / len(bwt_compressed)) / (len(msgpack_data) / len(baseline_compressed)) - 1
    time_overhead = (total_time / baseline_time - 1) * 100
    
    print(f"Size reduction: {size_improvement:+.2f}% (smaller is better)")
    print(f"Ratio improvement: {ratio_improvement*100:+.2f}% ({len(msgpack_data)/len(baseline_compressed):.2f}x → {len(msgpack_data)/len(bwt_compressed):.2f}x)")
    print(f"Time overhead: {time_overhead:+.1f}%")
    
    # Verify round-trip
    if universal_dict:
        dctx = zstd.ZstdDecompressor(dict_data=zdict)
        decompressed_bwt = dctx.decompress(bwt_compressed)
    else:
        decompressed_bwt = zstd.decompress(bwt_compressed)
    
    reconstructed = bwt_inverse(decompressed_bwt)
    assert reconstructed == msgpack_data, "BWT round-trip failed!"
    print("✅ BWT round-trip verified")
    
    return {
        'dataset': dataset_name,
        'logs': len(logs),
        'msgpack_size': len(msgpack_data),
        'baseline_size': len(baseline_compressed),
        'bwt_size': len(bwt_compressed),
        'baseline_ratio': len(msgpack_data) / len(baseline_compressed),
        'bwt_ratio': len(msgpack_data) / len(bwt_compressed),
        'improvement_pct': size_improvement,
        'baseline_time': baseline_time,
        'bwt_time': total_time
    }


def main():
    """Run BWT benchmark on all datasets"""
    datasets = [
        ('datasets/Apache/Apache_2k.log', 'Apache'),
        ('datasets/HealthApp/HealthApp_2k.log', 'HealthApp'),
        ('datasets/Zookeeper/Zookeeper_2k.log', 'Zookeeper'),
        ('datasets/Proxifier/Proxifier_2k.log', 'Proxifier'),
    ]
    
    results = []
    for path_str, name in datasets:
        path = Path(__file__).parent.parent / path_str
        if not path.exists():
            print(f"⚠️  Skipping {name}: {path} not found")
            continue
        
        result = benchmark_bwt_on_dataset(path, name)
        results.append(result)
    
    # Summary table
    print(f"\n{'='*80}")
    print("SUMMARY: BWT Preprocessing Impact")
    print(f"{'='*80}")
    print(f"{'Dataset':<15} {'Baseline':<10} {'With BWT':<10} {'Improvement':<12} {'Time':<10}")
    print(f"{'':<15} {'Ratio':<10} {'Ratio':<10} {'(%)':<12} {'Overhead':<10}")
    print("-" * 80)
    
    for r in results:
        time_overhead = (r['bwt_time'] / r['baseline_time'] - 1) * 100
        print(f"{r['dataset']:<15} {r['baseline_ratio']:<10.2f} {r['bwt_ratio']:<10.2f} "
              f"{r['improvement_pct']:<12.2f} {time_overhead:<10.1f}%")
    
    # Average
    avg_baseline = sum(r['baseline_ratio'] for r in results) / len(results)
    avg_bwt = sum(r['bwt_ratio'] for r in results) / len(results)
    avg_improvement = (avg_bwt / avg_baseline - 1) * 100
    avg_time_overhead = sum((r['bwt_time'] / r['baseline_time'] - 1) * 100 for r in results) / len(results)
    
    print("-" * 80)
    print(f"{'Average':<15} {avg_baseline:<10.2f} {avg_bwt:<10.2f} "
          f"{avg_improvement:<12.2f} {avg_time_overhead:<10.1f}%")
    
    print(f"\n📊 Expected gain from Phase 2 (BWT): +{avg_improvement:.1f}%")
    print(f"⏱️  Expected time overhead: +{avg_time_overhead:.0f}% (acceptable for archival)")


if __name__ == '__main__':
    main()
