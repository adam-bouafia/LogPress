#!/usr/bin/env python3
"""
Quick compression test: Compare improved LogSim vs Gzip baseline
"""

import sys
import gzip
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from logsim.compressor import SemanticCompressor


def test_compression(dataset_name: str, dataset_path: str, sample_size: int = 5000):
    """Test improved compression vs gzip baseline"""
    
    print(f"\n{'='*80}")
    print(f"Testing {dataset_name}")
    print(f"{'='*80}\n")
    
    # Load logs
    with open(dataset_path, 'r', encoding='utf-8', errors='replace') as f:
        logs = [line.strip() for line in f if line.strip()][:sample_size]
    
    original_data = '\n'.join(logs).encode('utf-8')
    original_size = len(original_data)
    
    print(f"📊 Original: {original_size:,} bytes ({original_size/1024:.1f} KB)")
    
    # Baseline: Gzip
    gzip_compressed = gzip.compress(original_data, compresslevel=9)
    gzip_size = len(gzip_compressed)
    gzip_ratio = original_size / gzip_size
    
    print(f"🗜️  Gzip: {gzip_size:,} bytes ({gzip_size/1024:.1f} KB) → {gzip_ratio:.2f}x")
    
    # LogSim with improved compression
    compressor = SemanticCompressor()
    compressed, stats = compressor.compress(logs, verbose=False)
    
    output_path = Path(f'compressed/{dataset_name.lower()}_improved.lsc')
    compressor.save(output_path)
    
    # Get actual file size
    logsim_size = output_path.stat().st_size
    logsim_ratio = original_size / logsim_size
    
    # Comparison
    print(f"\n📈 Comparison:")
    print(f"   Gzip:   {gzip_ratio:.2f}x")
    print(f"   LogSim: {logsim_ratio:.2f}x")
    
    if logsim_ratio > gzip_ratio:
        improvement = ((logsim_ratio / gzip_ratio) - 1) * 100
        print(f"   ✅ LogSim WINS by {improvement:.1f}%")
    elif logsim_ratio > gzip_ratio * 0.8:
        gap = ((gzip_ratio / logsim_ratio) - 1) * 100
        print(f"   ⚠️  LogSim close, {gap:.1f}% behind")
    else:
        gap = ((gzip_ratio / logsim_ratio) - 1) * 100
        print(f"   ❌ Gzip wins by {gap:.1f}%")
    
    return {
        'dataset': dataset_name,
        'original_size': original_size,
        'gzip_size': gzip_size,
        'gzip_ratio': gzip_ratio,
        'logsim_size': logsim_size,
        'logsim_ratio': logsim_ratio,
        'templates': len(compressed.templates) if hasattr(compressed, 'templates') else 0
    }


def main():
    """Test all datasets"""
    
    datasets = {
        'Apache': 'datasets/Apache/Apache_full.log',
        'HealthApp': 'datasets/HealthApp/HealthApp_full.log',
        'Zookeeper': 'datasets/Zookeeper/Zookeeper_full.log',
        'Proxifier': 'datasets/Proxifier/Proxifier_full.log'
    }
    
    results = []
    
    for name, path in datasets.items():
        if Path(path).exists():
            result = test_compression(name, path, sample_size=5000)
            results.append(result)
        else:
            print(f"⚠️  {name} not found")
    
    # Summary table
    print(f"\n{'='*80}")
    print(f"📊 FINAL RESULTS SUMMARY")
    print(f"{'='*80}\n")
    
    print(f"Dataset      | Gzip    | LogSim  | Winner")
    print(f"-------------|---------|---------|-------------")
    for r in results:
        winner = "✅ LogSim" if r['logsim_ratio'] > r['gzip_ratio'] else "⚠️ Close" if r['logsim_ratio'] > r['gzip_ratio'] * 0.8 else "❌ Gzip"
        print(f"{r['dataset']:<12} | {r['gzip_ratio']:>6.2f}x | {r['logsim_ratio']:>6.2f}x | {winner}")
    
    avg_gzip = sum(r['gzip_ratio'] for r in results) / len(results)
    avg_logsim = sum(r['logsim_ratio'] for r in results) / len(results)
    
    print(f"-------------|---------|---------|-------------")
    print(f"{'Average':<12} | {avg_gzip:>6.2f}x | {avg_logsim:>6.2f}x |")
    print()


if __name__ == '__main__':
    main()
