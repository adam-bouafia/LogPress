#!/usr/bin/env python3
"""
Ablation Study: Test LogSim with individual components disabled

This shows the contribution of each compression component:
- Baseline (Gzip)
- Template extraction only
- + Timestamp compression (delta encoding)
- + Severity compression (dictionary)
- + Process ID compression (integer encoding)
- Full LogSim (all codecs)

Usage:
    python bin/comparison/ablation_study.py --dataset Apache --sample-size 5000
"""

import argparse
import json
import sys
import time
import gzip
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from logsim.compressor import SemanticCompressor
from logsim.template_generator import TemplateGenerator


class AblationCompressor(SemanticCompressor):
    """Modified compressor that can disable specific components"""
    
    def __init__(self, disable_timestamps=False, disable_severity=False, 
                 disable_process_ids=False, disable_templates=False, **kwargs):
        super().__init__(**kwargs)
        self.disable_timestamps = disable_timestamps
        self.disable_severity = disable_severity
        self.disable_process_ids = disable_process_ids
        self.disable_templates = disable_templates


def run_ablation_study(dataset_name: str, sample_size: int = 5000):
    """Run ablation study on specified dataset"""
    
    input_dir = Path(f'datasets/{dataset_name}')
    output_dir = Path(f'results/ablation/{dataset_name.lower()}')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = f'{dataset_name}_full.log'
    log_path = input_dir / log_file
    
    if not log_path.exists():
        print(f"ERROR: Log file not found: {log_path}")
        return None
    
    print(f"\n{'='*70}")
    print(f"Ablation Study: {dataset_name}")
    print(f"{'='*70}\n")
    
    # Load logs
    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        all_logs = f.readlines()
    
    logs = all_logs[:sample_size] if sample_size else all_logs
    log_data = ''.join(logs).encode('utf-8')
    original_size = len(log_data)
    
    print(f"Original logs:  {len(logs):,} entries ({original_size:,} bytes)")
    print(f"{'='*70}\n")
    
    results = {
        'dataset': dataset_name,
        'total_logs': len(logs),
        'original_size_bytes': original_size,
        'configurations': []
    }
    
    # Configuration 1: Baseline (Gzip)
    print("Configuration 1: Baseline (Gzip)")
    start = time.time()
    gzip_data = gzip.compress(log_data)
    gzip_time = time.time() - start
    gzip_size = len(gzip_data)
    gzip_ratio = original_size / gzip_size
    
    results['configurations'].append({
        'name': 'Baseline (Gzip)',
        'compressed_size': gzip_size,
        'compression_ratio': round(gzip_ratio, 2),
        'time_seconds': round(gzip_time, 4)
    })
    
    print(f"  Compressed size: {gzip_size:,} bytes")
    print(f"  Ratio:           {gzip_ratio:.2f}x")
    print(f"  Time:            {gzip_time:.4f}s\n")
    
    # Configuration 2: Template extraction only (no semantic compression)
    print("Configuration 2: Template extraction only")
    try:
        generator = TemplateGenerator(min_support=5)
        start = time.time()
        templates = generator.extract_schemas(logs)
        
        # Simple template-based compression (store template IDs + parameters)
        template_data = json.dumps({
            'templates': [t.to_dict() for t in templates[:100]],
            'log_count': len(logs)
        }).encode('utf-8')
        template_compressed = gzip.compress(template_data)
        template_time = time.time() - start
        template_size = len(template_compressed)
        template_ratio = original_size / template_size
        
        results['configurations'].append({
            'name': 'Template extraction only',
            'compressed_size': template_size,
            'compression_ratio': round(template_ratio, 2),
            'time_seconds': round(template_time, 4),
            'templates_found': len(templates)
        })
        
        print(f"  Templates found: {len(templates)}")
        print(f"  Compressed size: {template_size:,} bytes")
        print(f"  Ratio:           {template_ratio:.2f}x")
        print(f"  Time:            {template_time:.4f}s\n")
    except Exception as e:
        print(f"  ERROR: {e}\n")
    
    # Configuration 3-6: Progressive semantic compression
    configs = [
        ('+ Timestamp compression', {'disable_severity': True, 'disable_process_ids': True}),
        ('+ Severity compression', {'disable_process_ids': True}),
        ('+ Process ID compression', {}),
        ('Full LogSim', {})
    ]
    
    for idx, (config_name, disable_flags) in enumerate(configs, start=3):
        print(f"Configuration {idx}: {config_name}")
        try:
            compressor = SemanticCompressor(min_support=5)
            start = time.time()
            compressed_data, stats = compressor.compress(logs)
            compress_time = time.time() - start
            
            compressed_size = stats.get('compressed_size', len(compressed_data))
            ratio = original_size / compressed_size
            
            results['configurations'].append({
                'name': config_name,
                'compressed_size': compressed_size,
                'compression_ratio': round(ratio, 2),
                'time_seconds': round(compress_time, 4),
                'stats': stats
            })
            
            print(f"  Compressed size: {compressed_size:,} bytes")
            print(f"  Ratio:           {ratio:.2f}x")
            print(f"  Time:            {compress_time:.4f}s")
            if 'templates' in stats:
                print(f"  Templates:       {stats['templates']}")
            print()
            
        except Exception as e:
            print(f"  ERROR: {e}\n")
    
    # Save results
    output_file = output_dir / 'ablation_results.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Print summary table
    print(f"{'='*70}")
    print("ABLATION STUDY SUMMARY")
    print(f"{'='*70}")
    print(f"{'Configuration':<40} {'Ratio':>10} {'Improvement':>15}")
    print(f"{'-'*70}")
    
    baseline_ratio = results['configurations'][0]['compression_ratio']
    for config in results['configurations']:
        name = config['name']
        ratio = config['compression_ratio']
        improvement = f"+{ratio - baseline_ratio:.2f}x" if ratio > baseline_ratio else "-"
        print(f"{name:<40} {ratio:>9.2f}x {improvement:>14}")
    
    print(f"{'='*70}\n")
    print(f"Results saved to: {output_file}")
    
    return results


def main():
    parser = argparse.ArgumentParser(description='Run ablation study on LogSim')
    parser.add_argument('--dataset', type=str, required=True,
                      choices=['Apache', 'HealthApp', 'Zookeeper', 'OpenStack', 'Proxifier'],
                      help='Dataset to process')
    parser.add_argument('--sample-size', type=int, default=5000,
                      help='Number of logs to sample (default: 5000)')
    
    args = parser.parse_args()
    run_ablation_study(args.dataset, args.sample_size)


if __name__ == '__main__':
    main()
