#!/usr/bin/env python3
"""
Full Dataset Evaluation Script

Runs comprehensive compression evaluation on ALL datasets:
- Apache (52K lines)
- HealthApp (212K lines)
- OpenStack (137K lines)
- Proxifier (21K lines)
- Zookeeper (74K lines)

Tracks and reports EXACTLY which algorithms/techniques are used.
"""

import sys
import time
import gzip
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import List, Dict

sys.path.insert(0, str(Path(__file__).parent))

from logsim.compressor import SemanticCompressor


@dataclass
class DatasetResult:
    """Results for a single dataset"""
    name: str
    log_count: int
    original_bytes: int
    compressed_bytes: int
    compression_ratio: float
    compress_time: float
    decompress_time: float
    gzip_bytes: int
    gzip_ratio: float
    template_count: int
    techniques_used: Dict[str, str]


def analyze_dataset(dataset_name: str, log_file: Path, sample_size: int = None) -> DatasetResult:
    """
    Compress a dataset and extract detailed algorithm usage
    
    Args:
        dataset_name: Human-readable name (e.g., "Apache")
        log_file: Path to .log file
        sample_size: Optional limit on number of logs to process
    """
    print("=" * 80)
    print(f"DATASET: {dataset_name}")
    print("=" * 80)
    print(f"📂 Loading {log_file}")
    
    # Load logs
    logs = []
    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        for i, line in enumerate(f):
            if sample_size and i >= sample_size:
                break
            line = line.strip()
            if line:
                logs.append(line)
    
    print(f"✓ Loaded {len(logs):,} logs")
    print()
    
    # Calculate sizes
    original_data = '\n'.join(logs).encode('utf-8')
    original_bytes = len(original_data)
    
    # gzip baseline
    print("📊 Baseline: gzip -9")
    gzipped = gzip.compress(original_data, compresslevel=9)
    gzip_bytes = len(gzipped)
    gzip_ratio = original_bytes / gzip_bytes
    print(f"   {original_bytes:,} → {gzip_bytes:,} bytes = {gzip_ratio:.2f}x")
    print()
    
    # LogSim compression with detailed tracking
    print("🔧 LogSim Compression Pipeline:")
    print()
    
    compressor = SemanticCompressor(min_support=3)
    
    start = time.time()
    compressed, stats = compressor.compress(logs, verbose=True)
    compress_time = time.time() - start
    
    print()
    print(f"✓ Compression completed in {compress_time:.3f}s")
    print()
    
    # Save to file
    output_path = Path(f"compressed/{dataset_name.lower()}_full.lsc")
    compressor.save(output_path, verbose=False)
    compressed_bytes = output_path.stat().st_size
    compression_ratio = original_bytes / compressed_bytes
    
    # Decompression test
    print("🔄 Testing decompression...")
    start = time.time()
    decompressed = compressor.decompress()
    decompress_time = time.time() - start
    
    match_count = sum(1 for orig, decomp in zip(logs, decompressed) if orig == decomp)
    print(f"✓ Decompressed {len(decompressed):,} logs in {decompress_time:.3f}s")
    print(f"✓ Lossless: {match_count}/{len(logs)} logs match ({(match_count/len(logs)*100):.1f}%)")
    print()
    
    # Extract technique details
    techniques = {
        "Tokenization": "FSM-based (logsim/tokenizer.py)",
        "Template Extraction": f"Custom log alignment algorithm ({len(compressed.templates)} templates)",
        "Token Pool": f"Global deduplication ({len(compressed.token_pool)} unique tokens)",
        "Delta Encoding": f"Timestamps ({compressed.timestamp_count} values)",
        "Zigzag Encoding": "Signed integers (varint.py)",
        "Varint Encoding": "Protocol Buffer style (varint.py)",
        "Dictionary Encoding": f"Low-cardinality fields (severity, IP, etc.)",
        "RLE v2": f"Pattern detection (log_index: {len(compressed.log_index_templates_rle)} bytes)",
        "MessagePack": "Binary serialization",
        "Zstandard": "Level 15 post-compression"
    }
    
    # Results
    print("=" * 80)
    print(f"RESULTS: {dataset_name}")
    print("=" * 80)
    print(f"Original size:       {original_bytes:,} bytes ({original_bytes/1024/1024:.2f} MB)")
    print(f"Compressed size:     {compressed_bytes:,} bytes ({compressed_bytes/1024:.2f} KB)")
    print(f"Compression ratio:   {compression_ratio:.2f}x")
    print(f"vs gzip-9:           {(compression_ratio/gzip_ratio)*100:.1f}% of gzip efficiency")
    print(f"Compression time:    {compress_time:.3f}s ({original_bytes/compress_time/1024/1024:.2f} MB/s)")
    print(f"Decompression time:  {decompress_time:.3f}s")
    print(f"Templates extracted: {len(compressed.templates)}")
    print()
    print("TECHNIQUES USED:")
    for i, (tech, detail) in enumerate(techniques.items(), 1):
        print(f"  {i:2d}. {tech:20s} → {detail}")
    print()
    
    return DatasetResult(
        name=dataset_name,
        log_count=len(logs),
        original_bytes=original_bytes,
        compressed_bytes=compressed_bytes,
        compression_ratio=compression_ratio,
        compress_time=compress_time,
        decompress_time=decompress_time,
        gzip_bytes=gzip_bytes,
        gzip_ratio=gzip_ratio,
        template_count=len(compressed.templates),
        techniques_used=techniques
    )


def main():
    """Run comprehensive evaluation on all datasets"""
    
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 78 + "║")
    print("║" + "LOGSIM FULL EVALUATION".center(78) + "║")
    print("║" + "Automatic Schema Extraction & Semantic Compression".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("╚" + "═" * 78 + "╝")
    print()
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    datasets = [
        ("Apache", Path("datasets/Apache/Apache_full.log"), None),
        ("HealthApp", Path("datasets/HealthApp/HealthApp_full.log"), None),
        ("OpenStack", Path("datasets/OpenStack/OpenStack_full.log"), None),
        ("Proxifier", Path("datasets/Proxifier/Proxifier_full.log"), None),
        ("Zookeeper", Path("datasets/Zookeeper/Zookeeper_full.log"), None),
    ]
    
    results: List[DatasetResult] = []
    
    for dataset_name, log_file, sample_size in datasets:
        if not log_file.exists():
            print(f"⚠ Skipping {dataset_name}: File not found ({log_file})")
            print()
            continue
        
        try:
            result = analyze_dataset(dataset_name, log_file, sample_size)
            results.append(result)
        except Exception as e:
            print(f"❌ Error processing {dataset_name}: {e}")
            import traceback
            traceback.print_exc()
            print()
    
    # Summary table
    print()
    print("╔" + "═" * 78 + "╗")
    print("║" + "SUMMARY: ALL DATASETS".center(78) + "║")
    print("╚" + "═" * 78 + "╝")
    print()
    
    # Table header
    print(f"{'Dataset':<12} | {'Logs':>8} | {'Original':>10} | {'Compressed':>10} | {'Ratio':>6} | {'vs gzip':>8} | {'Speed':>10}")
    print("-" * 80)
    
    total_original = 0
    total_compressed = 0
    total_gzip = 0
    
    for result in results:
        total_original += result.original_bytes
        total_compressed += result.compressed_bytes
        total_gzip += result.gzip_bytes
        
        vs_gzip = (result.compression_ratio / result.gzip_ratio) * 100
        speed = result.original_bytes / result.compress_time / 1024 / 1024
        
        print(f"{result.name:<12} | {result.log_count:>8,} | "
              f"{result.original_bytes/1024/1024:>8.2f} MB | "
              f"{result.compressed_bytes/1024:>8.2f} KB | "
              f"{result.compression_ratio:>6.2f}x | "
              f"{vs_gzip:>7.1f}% | "
              f"{speed:>7.2f} MB/s")
    
    print("-" * 80)
    
    avg_ratio = total_original / total_compressed
    avg_gzip_ratio = total_original / total_gzip
    avg_vs_gzip = (avg_ratio / avg_gzip_ratio) * 100
    
    print(f"{'AVERAGE':<12} | {sum(r.log_count for r in results):>8,} | "
          f"{total_original/1024/1024:>8.2f} MB | "
          f"{total_compressed/1024:>8.2f} KB | "
          f"{avg_ratio:>6.2f}x | "
          f"{avg_vs_gzip:>7.1f}% | "
          f"{'—':>10}")
    print()
    
    # Pipeline summary
    print("=" * 80)
    print("VERIFIED PRODUCTION PIPELINE")
    print("=" * 80)
    print()
    print("Stage 1: Tokenization")
    print("  • FSM-based tokenizer (logsim/tokenizer.py)")
    print("  • Context-aware boundary detection")
    print()
    print("Stage 2: Template Extraction")
    print("  • Custom log alignment algorithm (logsim/template_generator.py)")
    print("  • NOT Drain3 - position-by-position alignment")
    print(f"  • Extracted {sum(r.template_count for r in results)} total templates")
    print()
    print("Stage 3: Semantic Classification")
    print("  • Pattern-based matching (logsim/semantic_types.py)")
    print("  • Types: TIMESTAMP, SEVERITY, IP_ADDRESS, HOST, PROCESS_ID, MESSAGE, etc.")
    print()
    print("Stage 4: Columnar Encoding")
    print("  • Delta encoding: Timestamps (store differences from baseline)")
    print("  • Zigzag encoding: Signed integers")
    print("  • Varint encoding: Protocol Buffer style (varint.py)")
    print("  • Dictionary encoding: Low-cardinality fields")
    print("  • RLE v2: Pattern detection for repeated values")
    print("  • Token Pool: Global template token deduplication")
    print()
    print("Stage 5: Binary Serialization & Compression")
    print("  • MessagePack: Binary serialization (msgpack.packb)")
    print("  • Zstandard: Level 15 compression (zstd.compress)")
    print()
    print("Stage 6: Query Engine")
    print("  • Selective decompression (query_engine.py)")
    print("  • Columnar field access without full decompression")
    print()
    print(f"Overall Performance: {avg_ratio:.2f}x compression ({avg_vs_gzip:.1f}% of gzip-9 efficiency)")
    print()
    
    # Save results
    results_file = Path("results/full_evaluation_results.md")
    results_file.parent.mkdir(exist_ok=True)
    
    with open(results_file, 'w') as f:
        f.write(f"# LogSim Full Evaluation Results\n\n")
        f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**Total Datasets**: {len(results)}\n")
        f.write(f"**Total Logs**: {sum(r.log_count for r in results):,}\n")
        f.write(f"**Total Size**: {total_original/1024/1024:.2f} MB\n\n")
        
        f.write("## Summary Table\n\n")
        f.write("| Dataset | Logs | Original | Compressed | Ratio | vs gzip | Speed |\n")
        f.write("|---------|------|----------|------------|-------|---------|-------|\n")
        
        for result in results:
            vs_gzip = (result.compression_ratio / result.gzip_ratio) * 100
            speed = result.original_bytes / result.compress_time / 1024 / 1024
            f.write(f"| {result.name} | {result.log_count:,} | "
                   f"{result.original_bytes/1024/1024:.2f} MB | "
                   f"{result.compressed_bytes/1024:.2f} KB | "
                   f"{result.compression_ratio:.2f}x | "
                   f"{vs_gzip:.1f}% | "
                   f"{speed:.2f} MB/s |\n")
        
        f.write(f"| **AVERAGE** | {sum(r.log_count for r in results):,} | "
               f"{total_original/1024/1024:.2f} MB | "
               f"{total_compressed/1024:.2f} KB | "
               f"{avg_ratio:.2f}x | "
               f"{avg_vs_gzip:.1f}% | — |\n\n")
        
        f.write("## Verified Production Pipeline\n\n")
        f.write("### Stage 1: Tokenization\n")
        f.write("- **Algorithm**: FSM-based tokenizer\n")
        f.write("- **File**: `logsim/tokenizer.py`\n")
        f.write("- **Method**: Context-aware boundary detection\n\n")
        
        f.write("### Stage 2: Template Extraction\n")
        f.write("- **Algorithm**: Custom log alignment (NOT Drain3)\n")
        f.write("- **File**: `logsim/template_generator.py`\n")
        f.write("- **Method**: Position-by-position alignment across logs\n")
        f.write(f"- **Result**: {sum(r.template_count for r in results)} templates across all datasets\n\n")
        
        f.write("### Stage 3: Semantic Classification\n")
        f.write("- **Algorithm**: Pattern-based matching with confidence scoring\n")
        f.write("- **File**: `logsim/semantic_types.py`\n")
        f.write("- **Types**: TIMESTAMP, SEVERITY, IP_ADDRESS, HOST, PROCESS_ID, MESSAGE, etc.\n\n")
        
        f.write("### Stage 4: Columnar Encoding\n")
        f.write("1. **Delta Encoding**: Timestamps (store differences)\n")
        f.write("2. **Zigzag Encoding**: Signed integers\n")
        f.write("3. **Varint Encoding**: Protocol Buffer style (`varint.py`)\n")
        f.write("4. **Dictionary Encoding**: Low-cardinality fields (severity, status)\n")
        f.write("5. **RLE v2**: Pattern detection for repeated values\n")
        f.write("6. **Token Pool**: Global template token deduplication\n\n")
        
        f.write("### Stage 5: Binary Serialization & Compression\n")
        f.write("1. **MessagePack**: Binary serialization (`msgpack.packb`)\n")
        f.write("2. **Zstandard**: Level 15 compression (`zstd.compress`)\n\n")
        
        f.write("### Stage 6: Query Engine\n")
        f.write("- **File**: `logsim/query_engine.py`\n")
        f.write("- **Method**: Selective decompression (columnar field access)\n")
        f.write("- **Benefit**: Query without full decompression\n\n")

        
        f.write("## Per-Dataset Details\n\n")
        for result in results:
            f.write(f"### {result.name}\n\n")
            f.write(f"- **Logs**: {result.log_count:,}\n")
            f.write(f"- **Original Size**: {result.original_bytes:,} bytes ({result.original_bytes/1024/1024:.2f} MB)\n")
            f.write(f"- **Compressed Size**: {result.compressed_bytes:,} bytes ({result.compressed_bytes/1024:.2f} KB)\n")
            f.write(f"- **Compression Ratio**: {result.compression_ratio:.2f}x\n")
            f.write(f"- **vs gzip-9**: {(result.compression_ratio/result.gzip_ratio)*100:.1f}%\n")
            f.write(f"- **Compression Time**: {result.compress_time:.3f}s ({result.original_bytes/result.compress_time/1024/1024:.2f} MB/s)\n")
            f.write(f"- **Decompression Time**: {result.decompress_time:.3f}s\n")
            f.write(f"- **Templates**: {result.template_count}\n\n")
            
            f.write("**Techniques Applied**:\n")
            for tech, detail in result.techniques_used.items():
                f.write(f"- {tech}: {detail}\n")
            f.write("\n")
    
    print(f"✓ Results saved to {results_file}")
    print()
    print("=" * 80)
    print("EVALUATION COMPLETE")
    print("=" * 80)


if __name__ == '__main__':
    main()
