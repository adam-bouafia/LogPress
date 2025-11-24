#!/usr/bin/env python3
"""
Quick benchmark: Test BWT preprocessing impact on compression ratio

This tests BWT as a preprocessing step before compression to measure
the impact on final compression ratio. Tests with sample datasets.
"""

import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from logsim.compressor import SemanticCompressor
from logsim.bwt import bwt_transform, bwt_inverse
import msgpack
import zstandard as zstd


def benchmark_with_bwt(dataset_name: str, dataset_path: str, block_size: int = 256 * 1024):
    """
    Benchmark compression with BWT preprocessing
    
    Tests BWT by intercepting the MessagePack → Zstd step
    """
    print(f"\n{'='*60}")
    print(f"Testing BWT on {dataset_name}")
    print(f"{'='*60}")
    
    # Load logs
    print("\n1. Loading logs...")
    with open(dataset_path, 'r', encoding='utf-8', errors='ignore') as f:
        logs = [line.strip() for line in f if line.strip()][:5000]  # 5K logs
    
    print(f"   Loaded {len(logs)} logs")
    original_size = sum(len(log.encode('utf-8')) for log in logs)
    
    # Compress with LogSim
    print("\n2. LogSim compression...")
    start = time.time()
    
    compressor = SemanticCompressor()
    compressed_log, stats = compressor.compress(logs, verbose=False)
    
    compress_time = time.time() - start
    print(f"   Templates: {stats.template_count}")
    print(f"   Time: {compress_time:.2f}s")
    
    # Save baseline (current method)
    print("\n3. Baseline: Current compression (no BWT)")
    baseline_path = Path(f"compressed/{dataset_name.lower()}_nobwt.lsc")
    compressor.save(baseline_path, verbose=False)
    baseline_size = baseline_path.stat().st_size
    baseline_ratio = original_size / baseline_size
    
    print(f"   Compressed: {baseline_size:,} bytes")
    print(f"   Ratio: {baseline_ratio:.2f}x")
    
    # Now test with BWT
    # We need to intercept at the MessagePack level
    print("\n4. With BWT: MessagePack → BWT → Zstd")
    
    # Manually create the output dict (same as in save())
    cd = compressed_log
    output = {
        'version': cd.version,
        'templates': cd.templates,
        'token_pool': cd.token_pool,
        'template_token_refs': cd.template_token_refs,
        'timestamps_varint': cd.timestamps_varint,
        'timestamp_base': cd.timestamp_base,
        'timestamp_count': cd.timestamp_count,
        'severities_varint': cd.severities_varint,
        'severity_count': cd.severity_count,
        'ip_addresses_varint': cd.ip_addresses_varint,
        'ip_count': cd.ip_count,
        'messages_varint': cd.messages_varint,
        'message_count': cd.message_count,
        'severity_list': cd.severity_list,
        'ip_list': cd.ip_list,
        'message_list': cd.message_list,
        'log_index_templates_rle': cd.log_index_templates_rle,
        'log_index_fields_varint': cd.log_index_fields_varint,
        'log_index_field_counts': cd.log_index_field_counts,
        'original_count': cd.original_count,
        'compressed_at': cd.compressed_at
    }
    
    msgpack_data = msgpack.packb(output, use_bin_type=True)
    msgpack_size = len(msgpack_data)
    print(f"   MessagePack: {msgpack_size:,} bytes")
    
    # Apply BWT
    start = time.time()
    bwt_data = bwt_transform(msgpack_data, block_size=block_size)
    bwt_time = time.time() - start
    print(f"   BWT: {len(bwt_data):,} bytes in {bwt_time:.3f}s")
    
    # Compress with Zstd (same settings as baseline)
    start = time.time()
    universal_dict_path = Path("logsim/universal_dict.zstd")
    universal_dict = None
    if universal_dict_path.exists():
        with open(universal_dict_path, 'rb') as f:
            universal_dict = f.read()
    
    if universal_dict:
        zdict = zstd.ZstdCompressionDict(universal_dict)
        cctx = zstd.ZstdCompressor(level=15, dict_data=zdict)
    else:
        cctx = zstd.ZstdCompressor(level=15)
    
    bwt_compressed = cctx.compress(bwt_data)
    zstd_time = time.time() - start
    bwt_size = len(bwt_compressed)
    
    print(f"   Zstd: {bwt_size:,} bytes in {zstd_time:.3f}s")
    print(f"   Total time: {bwt_time + zstd_time:.3f}s")
    
    # Save BWT version for verification
    bwt_path = Path(f"compressed/{dataset_name.lower()}_bwt.lsc")
    bwt_path.parent.mkdir(parents=True, exist_ok=True)
    with open(bwt_path, 'wb') as f:
        f.write(bwt_compressed)
    
    # Calculate improvement
    improvement = (baseline_size - bwt_size) / baseline_size * 100
    bwt_ratio = original_size / bwt_size
    ratio_improvement = (bwt_ratio / baseline_ratio - 1) * 100
    
    # Compare
    print("\n" + "="*60)
    print("RESULTS:")
    print("="*60)
    print(f"\nOriginal size:      {original_size:,} bytes")
    print(f"Baseline (no BWT):  {baseline_size:,} bytes ({baseline_ratio:.2f}x)")
    print(f"With BWT:           {bwt_size:,} bytes ({bwt_ratio:.2f}x)")
    print(f"\nImprovement:        {improvement:+.1f}% smaller")
    print(f"Ratio gain:         {ratio_improvement:+.1f}%")
    
    # Test decompression
    print("\n5. Verifying round-trip...")
    if universal_dict:
        zdict = zstd.ZstdCompressionDict(universal_dict)
        dctx = zstd.ZstdDecompressor(dict_data=zdict)
    else:
        dctx = zstd.ZstdDecompressor()
    
    decompressed_bwt = dctx.decompress(bwt_compressed)
    reconstructed_msgpack = bwt_inverse(decompressed_bwt)
    
    if reconstructed_msgpack == msgpack_data:
        print("   ✅ Round-trip successful!")
    else:
        print(f"   ❌ Round-trip FAILED!")
        print(f"   Original size: {len(msgpack_data)}")
        print(f"   Reconstructed size: {len(reconstructed_msgpack)}")
    
    return {
        'dataset': dataset_name,
        'original_size': original_size,
        'baseline_size': baseline_size,
        'bwt_size': bwt_size,
        'improvement_pct': improvement,
        'ratio_improvement_pct': ratio_improvement,
        'baseline_ratio': baseline_ratio,
        'bwt_ratio': bwt_ratio
    }


if __name__ == '__main__':
    datasets = [
        ('Apache', 'datasets/Apache/Apache_full.log'),
        ('HealthApp', 'datasets/HealthApp/HealthApp_full.log'),
        ('Zookeeper', 'datasets/Zookeeper/Zookeeper_full.log'),
        ('Proxifier', 'datasets/Proxifier/Proxifier_full.log'),
    ]
    
    results = []
    
    for dataset_name, dataset_path in datasets:
        if Path(dataset_path).exists():
            result = benchmark_with_bwt(dataset_name, dataset_path, block_size=256*1024)  # 256KB blocks
            results.append(result)
        else:
            print(f"\n⚠️  Dataset not found: {dataset_path}")
    
    # Summary
    if results:
        print("\n\n" + "="*60)
        print("SUMMARY ACROSS ALL DATASETS")
        print("="*60)
        
        avg_improvement = sum(r['improvement_pct'] for r in results) / len(results)
        avg_ratio_gain = sum(r['ratio_improvement_pct'] for r in results) / len(results)
        avg_baseline_ratio = sum(r['baseline_ratio'] for r in results) / len(results)
        avg_bwt_ratio = sum(r['bwt_ratio'] for r in results) / len(results)
        
        print(f"\n{'Dataset':<15} {'Baseline':<15} {'With BWT':<15} {'Gain':<10}")
        print("-" * 55)
        for r in results:
            print(f"{r['dataset']:<15} {r['baseline_ratio']:>6.2f}x         {r['bwt_ratio']:>6.2f}x         {r['ratio_improvement_pct']:>+6.1f}%")
        
        print("-" * 55)
        print(f"{'AVERAGE':<15} {avg_baseline_ratio:>6.2f}x         {avg_bwt_ratio:>6.2f}x         {avg_ratio_gain:>+6.1f}%")
        
        print(f"\nAverage baseline ratio:  {avg_baseline_ratio:.2f}x")
        print(f"Average with BWT:        {avg_bwt_ratio:.2f}x")
        print(f"Average ratio gain:      {avg_ratio_gain:+.1f}%")
        
        if avg_ratio_gain >= 8:
            print("\n✅ BWT achieves target +8-12% compression improvement!")
        elif avg_ratio_gain > 0:
            print(f"\n⚠️  BWT improves compression but below +8% target ({avg_ratio_gain:.1f}%)")
        else:
            print(f"\n❌ BWT reduces compression ratio ({avg_ratio_gain:.1f}%)")
