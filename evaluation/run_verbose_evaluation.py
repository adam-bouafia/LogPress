#!/usr/bin/env python3
"""
Verbose Evaluation Script - Shows Real-Time Progress

Runs evaluation with detailed progress output on a subset of datasets
for quick testing and demonstration purposes.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import time
import gzip
from datetime import datetime
from logpress.services.compressor import SemanticCompressor


def evaluate_dataset(name, log_file, max_logs=None):
    """Evaluate a single dataset with verbose output"""
    
    print("=" * 80)
    print(f"📊 DATASET: {name}")
    print("=" * 80)
    print()
    
    # Load logs
    print(f"📂 Loading logs from: {log_file.name}")
    logs = []
    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        for i, line in enumerate(f):
            if max_logs and i >= max_logs:
                break
            line = line.strip()
            if line:
                logs.append(line)
    
    print(f"✓ Loaded {len(logs):,} log entries")
    print()
    
    # Original size
    original_data = '\n'.join(logs).encode('utf-8')
    original_bytes = len(original_data)
    original_mb = original_bytes / 1024 / 1024
    
    print(f"📏 Original size: {original_bytes:,} bytes ({original_mb:.2f} MB)")
    print()
    
    # Baseline: gzip
    print("🗜️  Baseline compression (gzip -9)...")
    gzip_start = time.time()
    gzipped = gzip.compress(original_data, compresslevel=9)
    gzip_time = time.time() - gzip_start
    gzip_bytes = len(gzipped)
    gzip_ratio = original_bytes / gzip_bytes
    
    print(f"   Size: {gzip_bytes:,} bytes ({gzip_bytes/1024:.2f} KB)")
    print(f"   Ratio: {gzip_ratio:.2f}x")
    print(f"   Time: {gzip_time:.3f}s")
    print()
    
    # logpress compression
    print("🚀 logpress Semantic Compression Pipeline:")
    print()
    print("   Stage 1: Tokenization (FSM-based)")
    print("   Stage 2: Template Extraction (log alignment)")
    print("   Stage 3: Semantic Classification (pattern matching)")
    print("   Stage 4: Columnar Encoding (delta, varint, RLE)")
    print("   Stage 5: Binary Serialization (MessagePack + Zstandard)")
    print()
    
    compressor = SemanticCompressor(min_support=3)
    
    compress_start = time.time()
    print("⚙️  Compressing...")
    compressed, stats = compressor.compress(logs, verbose=True)
    compress_time = time.time() - compress_start
    
    print()
    print(f"✓ Compression completed in {compress_time:.3f}s")
    print()
    
    # Save compressed file
    output_dir = Path("evaluation/compressed")
    output_dir.mkdir(exist_ok=True, parents=True)
    output_path = output_dir / f"{name.lower()}_test.lsc"
    
    print(f"💾 Saving to: {output_path.name}")
    compressor.save(output_path, verbose=False)
    compressed_bytes = output_path.stat().st_size
    compressed_kb = compressed_bytes / 1024
    compression_ratio = original_bytes / compressed_bytes
    
    print(f"   Size: {compressed_bytes:,} bytes ({compressed_kb:.2f} KB)")
    print(f"   Ratio: {compression_ratio:.2f}x")
    print()
    
    # Decompression test
    print("🔄 Testing decompression...")
    decompress_start = time.time()
    decompressed = compressor.decompress()
    decompress_time = time.time() - decompress_start
    
    # Verify
    matches = sum(1 for o, d in zip(logs, decompressed) if o == d)
    accuracy = (matches / len(logs)) * 100
    
    print(f"✓ Decompressed {len(decompressed):,} logs in {decompress_time:.3f}s")
    print(f"✓ Lossless accuracy: {matches}/{len(logs)} ({accuracy:.1f}%)")
    print()
    
    # Results summary
    print("=" * 80)
    print("📈 RESULTS SUMMARY")
    print("=" * 80)
    print()
    print(f"Dataset:             {name}")
    print(f"Log entries:         {len(logs):,}")
    print(f"Original size:       {original_bytes:,} bytes ({original_mb:.2f} MB)")
    print()
    print(f"gzip-9:              {gzip_bytes:,} bytes ({gzip_ratio:.2f}x)")
    print(f"logpress:              {compressed_bytes:,} bytes ({compression_ratio:.2f}x)")
    print()
    print(f"Improvement:         {(compression_ratio/gzip_ratio)*100:.1f}% of gzip efficiency")
    print()
    print(f"Compression speed:   {original_mb/compress_time:.2f} MB/s")
    print(f"Decompression speed: {original_mb/decompress_time:.2f} MB/s")
    print()
    print(f"Templates found:     {len(compressed.templates)}")
    print(f"Unique tokens:       {len(compressed.token_pool)}")
    print(f"Timestamp entries:   {compressed.timestamp_count}")
    print()
    
    return {
        'name': name,
        'logs': len(logs),
        'original_bytes': original_bytes,
        'compressed_bytes': compressed_bytes,
        'gzip_bytes': gzip_bytes,
        'compression_ratio': compression_ratio,
        'gzip_ratio': gzip_ratio,
        'compress_time': compress_time,
        'decompress_time': decompress_time,
        'templates': len(compressed.templates)
    }


def main():
    """Run verbose evaluation on selected datasets"""
    
    print()
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 78 + "║")
    print("║" + "logpress VERBOSE EVALUATION".center(78) + "║")
    print("║" + "Real-Time Progress Display".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("╚" + "═" * 78 + "╝")
    print()
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Auto-discover datasets (use sample for large ones)
    dataset_dir = Path("data/datasets")
    folder_names = ["Apache", "BGL", "HDFS", "HPC", "HealthApp", "Linux", "Mac", "OpenStack", "Proxifier", "Zookeeper"]
    test_cases = []

    for folder_name in folder_names:
        folder = dataset_dir / folder_name
        if not folder.exists():
            continue

        # Try different log filename patterns
        log_file = None
        for pattern in [f"{folder_name}_full.log", f"{folder_name}.log", f"{folder_name.lower()}.log"]:
            candidate = folder / pattern
            if candidate.exists():
                log_file = candidate
                break

        if not log_file:
            continue

        sample = None
        if folder_name in ["HDFS", "BGL"]:
            sample = 100000

        test_cases.append((folder_name, log_file, sample))

    results = []

    for name, log_file, max_logs in test_cases:
        if not log_file.exists():
            print(f"⚠️  Skipping {name}: File not found ({log_file})")
            print()
            continue
        
        try:
            result = evaluate_dataset(name, log_file, max_logs)
            results.append(result)
        except Exception as e:
            print(f"❌ Error processing {name}: {e}")
            import traceback
            traceback.print_exc()
            print()
            continue
    
    # Final summary
    if results:
        print()
        print("=" * 80)
        print("🏆 OVERALL SUMMARY")
        print("=" * 80)
        print()
        print(f"{'Dataset':<12} | {'Logs':>10} | {'Original':>10} | {'Compressed':>10} | {'Ratio':>7} | {'vs gzip':>8}")
        print("-" * 80)
        
        total_original = sum(r['original_bytes'] for r in results)
        total_compressed = sum(r['compressed_bytes'] for r in results)
        total_gzip = sum(r['gzip_bytes'] for r in results)
        
        for r in results:
            vs_gzip = (r['compression_ratio'] / r['gzip_ratio']) * 100
            print(f"{r['name']:<12} | {r['logs']:>10,} | "
                  f"{r['original_bytes']/1024/1024:>8.2f} MB | "
                  f"{r['compressed_bytes']/1024:>8.2f} KB | "
                  f"{r['compression_ratio']:>6.2f}x | "
                  f"{vs_gzip:>7.1f}%")
        
        print("-" * 80)
        avg_ratio = total_original / total_compressed
        avg_gzip = total_original / total_gzip
        avg_vs_gzip = (avg_ratio / avg_gzip) * 100
        
        print(f"{'AVERAGE':<12} | {sum(r['logs'] for r in results):>10,} | "
              f"{total_original/1024/1024:>8.2f} MB | "
              f"{total_compressed/1024:>8.2f} KB | "
              f"{avg_ratio:>6.2f}x | "
              f"{avg_vs_gzip:>7.1f}%")
        print()
    
    # Save results to files
    if results:
        import json
        
        # Create results directory
        results_dir = Path("evaluation/results")
        results_dir.mkdir(exist_ok=True, parents=True)
        
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        
        # Save as JSON for programmatic access
        json_file = results_dir / f"evaluation_results_{timestamp}.json"
        json_data = {
            'timestamp': datetime.now().isoformat(),
            'total_datasets': len(results),
            'total_logs': sum(r['logs'] for r in results),
            'total_original_bytes': total_original,
            'total_compressed_bytes': total_compressed,
            'total_gzip_bytes': total_gzip,
            'average_compression_ratio': avg_ratio,
            'average_gzip_ratio': avg_gzip,
            'average_vs_gzip_percent': avg_vs_gzip,
            'datasets': results
        }
        
        with open(json_file, 'w') as f:
            json.dump(json_data, f, indent=2)
        
        print(f"✓ JSON results saved to: {json_file}")
        
        # Save as Markdown for thesis/reports
        md_file = results_dir / f"evaluation_results_{timestamp}.md"
        with open(md_file, 'w') as f:
            f.write("# logpress Evaluation Results\n\n")
            f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**Total Datasets**: {len(results)}\n")
            f.write(f"**Total Logs**: {sum(r['logs'] for r in results):,}\n")
            f.write(f"**Total Original Size**: {total_original/1024/1024:.2f} MB\n")
            f.write(f"**Total Compressed Size**: {total_compressed/1024:.2f} KB\n")
            f.write(f"**Average Compression Ratio**: {avg_ratio:.2f}×\n")
            f.write(f"**vs gzip-9**: {avg_vs_gzip:.1f}%\n\n")
            
            f.write("## Summary Table\n\n")
            f.write("| Dataset | Logs | Original Size | Compressed Size | Ratio | vs gzip | Compression Speed | Decompression Speed | Templates |\n")
            f.write("|---------|------|---------------|-----------------|-------|---------|-------------------|---------------------|----------|\n")
            
            for r in results:
                vs_gzip = (r['compression_ratio'] / r['gzip_ratio']) * 100
                comp_speed = r['original_bytes'] / r['compress_time'] / 1024 / 1024
                decomp_speed = r['original_bytes'] / r['decompress_time'] / 1024 / 1024
                
                f.write(f"| {r['name']} | {r['logs']:,} | "
                       f"{r['original_bytes']/1024/1024:.2f} MB | "
                       f"{r['compressed_bytes']/1024:.2f} KB | "
                       f"{r['compression_ratio']:.2f}× | "
                       f"{vs_gzip:.1f}% | "
                       f"{comp_speed:.2f} MB/s | "
                       f"{decomp_speed:.2f} MB/s | "
                       f"{r['templates']} |\n")
            
            f.write(f"\n**Average** | {sum(r['logs'] for r in results):,} | "
                   f"{total_original/1024/1024:.2f} MB | "
                   f"{total_compressed/1024:.2f} KB | "
                   f"{avg_ratio:.2f}× | "
                   f"{avg_vs_gzip:.1f}% | — | — | — |\n\n")
            
            f.write("## Per-Dataset Details\n\n")
            for r in results:
                f.write(f"### {r['name']}\n\n")
                f.write(f"- **Log Entries**: {r['logs']:,}\n")
                f.write(f"- **Original Size**: {r['original_bytes']:,} bytes ({r['original_bytes']/1024/1024:.2f} MB)\n")
                f.write(f"- **Compressed Size**: {r['compressed_bytes']:,} bytes ({r['compressed_bytes']/1024:.2f} KB)\n")
                f.write(f"- **Compression Ratio**: {r['compression_ratio']:.2f}×\n")
                f.write(f"- **gzip-9 Size**: {r['gzip_bytes']:,} bytes ({r['gzip_bytes']/1024:.2f} KB)\n")
                f.write(f"- **gzip-9 Ratio**: {r['gzip_ratio']:.2f}×\n")
                f.write(f"- **vs gzip-9**: {(r['compression_ratio']/r['gzip_ratio'])*100:.1f}%\n")
                f.write(f"- **Compression Time**: {r['compress_time']:.3f}s ({r['original_bytes']/r['compress_time']/1024/1024:.2f} MB/s)\n")
                f.write(f"- **Decompression Time**: {r['decompress_time']:.3f}s ({r['original_bytes']/r['decompress_time']/1024/1024:.2f} MB/s)\n")
                f.write(f"- **Templates Extracted**: {r['templates']}\n\n")
        
        print(f"✓ Markdown results saved to: {md_file}")
        print()
        
        # Also save a "latest" version for easy reference
        latest_json = results_dir / "evaluation_results_latest.json"
        latest_md = results_dir / "evaluation_results_latest.md"
        
        with open(latest_json, 'w') as f:
            json.dump(json_data, f, indent=2)
        
        with open(latest_md, 'w') as f:
            f.write("# logpress Evaluation Results (Latest)\n\n")
            f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**Total Datasets**: {len(results)}\n")
            f.write(f"**Total Logs**: {sum(r['logs'] for r in results):,}\n")
            f.write(f"**Total Original Size**: {total_original/1024/1024:.2f} MB\n")
            f.write(f"**Total Compressed Size**: {total_compressed/1024:.2f} KB\n")
            f.write(f"**Average Compression Ratio**: {avg_ratio:.2f}×\n")
            f.write(f"**vs gzip-9**: {avg_vs_gzip:.1f}%\n\n")
            
            f.write("## Summary Table\n\n")
            f.write("| Dataset | Logs | Original Size | Compressed Size | Ratio | vs gzip | Compression Speed | Decompression Speed | Templates |\n")
            f.write("|---------|------|---------------|-----------------|-------|---------|-------------------|---------------------|----------|\n")
            
            for r in results:
                vs_gzip = (r['compression_ratio'] / r['gzip_ratio']) * 100
                comp_speed = r['original_bytes'] / r['compress_time'] / 1024 / 1024
                decomp_speed = r['original_bytes'] / r['decompress_time'] / 1024 / 1024
                
                f.write(f"| {r['name']} | {r['logs']:,} | "
                       f"{r['original_bytes']/1024/1024:.2f} MB | "
                       f"{r['compressed_bytes']/1024:.2f} KB | "
                       f"{r['compression_ratio']:.2f}× | "
                       f"{vs_gzip:.1f}% | "
                       f"{comp_speed:.2f} MB/s | "
                       f"{decomp_speed:.2f} MB/s | "
                       f"{r['templates']} |\n")
            
            f.write(f"\n**Average** | {sum(r['logs'] for r in results):,} | "
                   f"{total_original/1024/1024:.2f} MB | "
                   f"{total_compressed/1024:.2f} KB | "
                   f"{avg_ratio:.2f}× | "
                   f"{avg_vs_gzip:.1f}% | — | — | — |\n\n")
            
            f.write("## Per-Dataset Details\n\n")
            for r in results:
                f.write(f"### {r['name']}\n\n")
                f.write(f"- **Log Entries**: {r['logs']:,}\n")
                f.write(f"- **Original Size**: {r['original_bytes']:,} bytes ({r['original_bytes']/1024/1024:.2f} MB)\n")
                f.write(f"- **Compressed Size**: {r['compressed_bytes']:,} bytes ({r['compressed_bytes']/1024:.2f} KB)\n")
                f.write(f"- **Compression Ratio**: {r['compression_ratio']:.2f}×\n")
                f.write(f"- **gzip-9 Size**: {r['gzip_bytes']:,} bytes ({r['gzip_bytes']/1024:.2f} KB)\n")
                f.write(f"- **gzip-9 Ratio**: {r['gzip_ratio']:.2f}×\n")
                f.write(f"- **vs gzip-9**: {(r['compression_ratio']/r['gzip_ratio'])*100:.1f}%\n")
                f.write(f"- **Compression Time**: {r['compress_time']:.3f}s ({r['original_bytes']/r['compress_time']/1024/1024:.2f} MB/s)\n")
                f.write(f"- **Decompression Time**: {r['decompress_time']:.3f}s ({r['original_bytes']/r['decompress_time']/1024/1024:.2f} MB/s)\n")
                f.write(f"- **Templates Extracted**: {r['templates']}\n\n")
        
        print(f"✓ Latest results also saved to:")
        print(f"  • {latest_json}")
        print(f"  • {latest_md}")
    
    print()
    print("=" * 80)
    print("✅ EVALUATION COMPLETE")
    print("=" * 80)
    print()


if __name__ == '__main__':
    main()
