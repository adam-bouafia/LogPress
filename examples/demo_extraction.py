#!/usr/bin/env python3
"""
Demo: Schema Extraction from Real Logs

This script demonstrates schema extraction on the actual datasets:
- Apache (52K logs)
- HealthApp (212K logs)
- Zookeeper (74K logs)
- OpenStack (137K logs)
- Proxifier (21K logs)

Usage:
    python demo_extraction.py [--dataset DATASET] [--sample-size SIZE]
    
Examples:
    python demo_extraction.py --dataset Apache --sample-size 1000
    python demo_extraction.py --dataset HealthApp --sample-size 5000
    python demo_extraction.py  # Process all datasets with 1000 samples each
"""

import argparse
import sys
import json
from pathlib import Path
from typing import List, Dict
import time

from logsim.template_generator import TemplateGenerator


def load_log_file(filepath: Path, max_lines: int = None) -> List[str]:
    """Load log entries from file"""
    logs = []
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for i, line in enumerate(f):
            if max_lines and i >= max_lines:
                break
            line = line.strip()
            if line:
                logs.append(line)
    return logs


def process_dataset(dataset_name: str, sample_size: int = 1000):
    """Process a single dataset and extract schemas"""
    
    datasets_dir = Path("datasets")
    dataset_path = datasets_dir / dataset_name / f"{dataset_name}_full.log"
    
    if dataset_name == "OpenStack":
        dataset_path = datasets_dir / dataset_name / "openstack.log"
    
    if not dataset_path.exists():
        print(f"❌ Dataset not found: {dataset_path}")
        return None
    
    print(f"\n{'='*80}")
    print(f"📂 Processing: {dataset_name}")
    print(f"{'='*80}")
    print(f"File: {dataset_path}")
    
    # Load logs
    print(f"Loading {sample_size} log entries...")
    start_time = time.time()
    logs = load_log_file(dataset_path, max_lines=sample_size)
    load_time = time.time() - start_time
    
    print(f"✓ Loaded {len(logs)} logs in {load_time:.2f}s")
    
    # Show first few logs
    print(f"\n📋 Sample logs:")
    for i, log in enumerate(logs[:3], 1):
        print(f"  {i}. {log[:100]}{'...' if len(log) > 100 else ''}")
    
    # Extract schemas
    print(f"\n🔍 Extracting schemas (min_support=5)...")
    start_time = time.time()
    generator = TemplateGenerator(min_support=5, similarity_threshold=0.7)
    templates = generator.extract_schemas(logs)
    extract_time = time.time() - start_time
    
    print(f"✓ Extracted {len(templates)} templates in {extract_time:.2f}s")
    
    # Show results
    print(f"\n📊 Extracted Schema Templates:")
    print(f"{'─'*80}")
    
    total_matched = sum(t.match_count for t in templates)
    coverage = (total_matched / len(logs) * 100) if logs else 0
    
    for i, template in enumerate(templates[:10], 1):  # Show top 10
        percent = (template.match_count / len(logs) * 100) if logs else 0
        print(f"\n{i}. {template.template_id} (matches: {template.match_count}, {percent:.1f}%)")
        print(f"   Pattern: {template.to_string()}")
        print(f"   Example: {template.example_logs[0][:100]}{'...' if len(template.example_logs[0]) > 100 else ''}")
    
    if len(templates) > 10:
        print(f"\n   ... and {len(templates) - 10} more templates")
    
    print(f"\n📈 Summary:")
    print(f"   • Total logs: {len(logs)}")
    print(f"   • Unique templates: {len(templates)}")
    print(f"   • Coverage: {coverage:.1f}% of logs matched to templates")
    print(f"   • Processing speed: {len(logs)/extract_time:.0f} logs/sec")
    
    # Save results
    output_dir = Path("annotations") / dataset_name
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / f"extracted_schemas_{sample_size}.json"
    
    result = {
        'dataset': dataset_name,
        'sample_size': len(logs),
        'template_count': len(templates),
        'coverage': coverage,
        'processing_time': extract_time,
        'templates': [
            {
                'id': t.template_id,
                'pattern': t.to_string(),
                'matches': t.match_count,
                'coverage_percent': (t.match_count / len(logs) * 100) if logs else 0,
                'field_types': {pos: ftype.value for pos, ftype in t.field_types.items()},
                'examples': t.example_logs[:3]
            }
            for t in templates
        ]
    }
    
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"\n💾 Results saved to: {output_file}")
    
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Extract schemas from log datasets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --dataset Apache --sample-size 1000
  %(prog)s --dataset HealthApp --sample-size 5000
  %(prog)s  # Process all datasets
        """
    )
    
    parser.add_argument(
        '--dataset',
        choices=['Apache', 'HealthApp', 'Zookeeper', 'OpenStack', 'Proxifier', 'all'],
        default='all',
        help='Dataset to process (default: all)'
    )
    
    parser.add_argument(
        '--sample-size',
        type=int,
        default=1000,
        help='Number of logs to sample from each dataset (default: 1000)'
    )
    
    args = parser.parse_args()
    
    print("🚀 LogSim Schema Extraction Demo")
    print("="*80)
    print(f"Configuration:")
    print(f"  • Dataset: {args.dataset}")
    print(f"  • Sample size: {args.sample_size} logs per dataset")
    
    # Process datasets
    if args.dataset == 'all':
        datasets = ['Apache', 'HealthApp', 'Zookeeper', 'OpenStack', 'Proxifier']
    else:
        datasets = [args.dataset]
    
    results = []
    for dataset in datasets:
        result = process_dataset(dataset, args.sample_size)
        if result:
            results.append(result)
    
    # Overall summary
    if len(results) > 1:
        print(f"\n{'='*80}")
        print("🎯 Overall Summary")
        print(f"{'='*80}")
        
        for result in results:
            print(f"\n{result['dataset']:12s}: {result['template_count']:3d} templates, "
                  f"{result['coverage']:5.1f}% coverage, "
                  f"{result['sample_size']/result['processing_time']:6.0f} logs/sec")
        
        total_logs = sum(r['sample_size'] for r in results)
        total_templates = sum(r['template_count'] for r in results)
        avg_coverage = sum(r['coverage'] for r in results) / len(results)
        
        print(f"\n{'─'*80}")
        print(f"Total: {total_logs} logs processed")
        print(f"Total: {total_templates} unique templates extracted")
        print(f"Average coverage: {avg_coverage:.1f}%")
    
    print(f"\n✅ Done! Check annotations/ directory for detailed results.")


if __name__ == "__main__":
    main()
