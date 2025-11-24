#!/usr/bin/env python3
"""
Analyze why gzip is outperforming LogSim compression
This script investigates the compression pipeline and identifies bottlenecks
"""

import json
import gzip
import sys
from pathlib import Path
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from logsim.compressor import SemanticCompressor
from logsim.template_generator import TemplateGenerator


def analyze_compression_pipeline(dataset_path: str, sample_size: int = 5000):
    """Analyze each compression stage"""
    
    print(f"\n{'='*80}")
    print(f"COMPRESSION ANALYSIS: {Path(dataset_path).stem}")
    print(f"{'='*80}\n")
    
    # Load logs
    with open(dataset_path, 'r', encoding='utf-8', errors='replace') as f:
        logs = [line.strip() for line in f if line.strip()][:sample_size]
    
    original_text = '\n'.join(logs)
    original_size = len(original_text.encode('utf-8'))
    
    print(f"📊 Original Data:")
    print(f"   Logs: {len(logs):,}")
    print(f"   Size: {original_size:,} bytes ({original_size / 1024:.2f} KB)")
    print(f"   Avg log size: {original_size / len(logs):.1f} bytes/log\n")
    
    # Test raw gzip
    gzipped = gzip.compress(original_text.encode('utf-8'))
    gzip_size = len(gzipped)
    gzip_ratio = original_size / gzip_size
    
    print(f"🗜️  Baseline Gzip:")
    print(f"   Compressed: {gzip_size:,} bytes ({gzip_size / 1024:.2f} KB)")
    print(f"   Ratio: {gzip_ratio:.2f}x")
    print(f"   Savings: {((1 - gzip_size/original_size) * 100):.1f}%\n")
    
    # Analyze LogSim stages
    print(f"🔍 LogSim Compression Pipeline:\n")
    
    # Stage 1: Template extraction
    generator = TemplateGenerator(min_support=5)
    templates = generator.extract_schemas(logs)
    
    print(f"   Stage 1 - Template Extraction:")
    print(f"      Templates found: {len(templates)}")
    
    if templates:
        # Estimate template storage size
        template_data = json.dumps([{'pattern': ' '.join(t.pattern), 'match_count': t.match_count} for t in templates])
        template_size = len(template_data.encode('utf-8'))
        print(f"      Template storage: {template_size:,} bytes")
        
        # Show template examples
        print(f"      Examples:")
        for i, template in enumerate(templates[:5], 1):
            pattern_str = ' '.join(template.pattern)
            print(f"         {i}. {pattern_str[:80]}... (matches: {template.match_count})")
    else:
        print(f"      ⚠️  WARNING: No templates found!")
        template_size = 0
    
    # Stage 2: Semantic compression
    compressor = SemanticCompressor(min_support=5)
    compressed_output, stats = compressor.compress(logs)
    
    # Calculate compressed size (this is the issue - we're storing Python objects, not bytes!)
    compressed_json = json.dumps(compressed_output)
    logsim_uncompressed = len(compressed_json.encode('utf-8'))
    
    print(f"\n   Stage 2 - Semantic Compression:")
    print(f"      Compressed records: {len(compressed_output.get('entries', []))}")
    print(f"      JSON size (uncompressed): {logsim_uncompressed:,} bytes")
    print(f"      ⚠️  This JSON is NOT gzipped yet!")
    
    # Stage 3: Apply gzip to LogSim output (MISSING STEP!)
    logsim_gzipped = gzip.compress(compressed_json.encode('utf-8'))
    logsim_final_size = len(logsim_gzipped)
    logsim_ratio = original_size / logsim_final_size
    
    print(f"\n   Stage 3 - Apply Gzip to LogSim Output:")
    print(f"      Final compressed: {logsim_final_size:,} bytes ({logsim_final_size / 1024:.2f} KB)")
    print(f"      Final ratio: {logsim_ratio:.2f}x")
    print(f"      Savings: {((1 - logsim_final_size/original_size) * 100):.1f}%\n")
    
    # Comparison
    print(f"{'='*80}")
    print(f"📈 COMPARISON:")
    print(f"{'='*80}\n")
    
    print(f"   Method                 | Size (KB)  | Ratio  | Winner")
    print(f"   -----------------------|------------|--------|--------")
    print(f"   Original               | {original_size/1024:>9.2f}  | 1.00x  | -")
    print(f"   Gzip only              | {gzip_size/1024:>9.2f}  | {gzip_ratio:>5.2f}x | {'✓' if gzip_ratio > logsim_ratio else ''}")
    print(f"   LogSim (no gzip)       | {logsim_uncompressed/1024:>9.2f}  | {original_size/logsim_uncompressed:>5.2f}x | ❌")
    print(f"   LogSim + Gzip          | {logsim_final_size/1024:>9.2f}  | {logsim_ratio:>5.2f}x | {'✓' if logsim_ratio > gzip_ratio else ''}")
    print()
    
    if logsim_ratio > gzip_ratio:
        improvement = ((logsim_ratio / gzip_ratio - 1) * 100)
        print(f"   ✅ LogSim+Gzip is {improvement:.1f}% better than Gzip!")
    else:
        deficit = ((gzip_ratio / logsim_ratio - 1) * 100)
        print(f"   ⚠️  Gzip is {deficit:.1f}% better than LogSim+Gzip")
    
    print(f"\n{'='*80}")
    print(f"🔍 ROOT CAUSE ANALYSIS:")
    print(f"{'='*80}\n")
    
    # Identify issues
    issues = []
    
    if len(templates) == 0:
        issues.append("❌ No templates extracted - parser not finding patterns")
    
    if logsim_uncompressed > original_size * 0.8:
        issues.append("❌ JSON overhead too high - semantic compression not effective")
    
    if logsim_ratio < gzip_ratio:
        issues.append("⚠️  Even with gzip, LogSim underperforms - need better semantic compression")
    
    if template_size > original_size * 0.1:
        issues.append("⚠️  Template storage too large - need better template representation")
    
    if issues:
        for issue in issues:
            print(f"   {issue}")
    else:
        print(f"   ✅ No major issues detected")
    
    print(f"\n{'='*80}\n")
    
    return {
        'original_size': original_size,
        'gzip_size': gzip_size,
        'gzip_ratio': gzip_ratio,
        'logsim_uncompressed': logsim_uncompressed,
        'logsim_final_size': logsim_final_size,
        'logsim_ratio': logsim_ratio,
        'templates_count': len(templates),
        'template_size': template_size,
        'issues': issues
    }


def main():
    """Run analysis on all datasets"""
    
    datasets = [
        'datasets/Apache/Apache_full.log',
        'datasets/HealthApp/HealthApp_full.log',
        'datasets/Zookeeper/Zookeeper_full.log',
        'datasets/Proxifier/Proxifier_full.log'
    ]
    
    results = {}
    
    for dataset in datasets:
        if Path(dataset).exists():
            try:
                result = analyze_compression_pipeline(dataset, sample_size=5000)
                results[Path(dataset).stem] = result
            except Exception as e:
                print(f"❌ Error analyzing {dataset}: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"⚠️  Dataset not found: {dataset}")
    
    # Save results
    output_path = Path('results/analysis/compression_analysis.json')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"📊 Full results saved to: {output_path}")


if __name__ == '__main__':
    main()
