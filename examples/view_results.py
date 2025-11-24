#!/usr/bin/env python3
"""
Visualize extracted schema results

Shows summary statistics and top templates from each dataset
"""

import json
from pathlib import Path
from typing import Dict, List


def load_results(dataset: str) -> Dict:
    """Load extracted schema results for a dataset"""
    results_file = Path("annotations") / dataset / "extracted_schemas_1000.json"
    
    if not results_file.exists():
        return None
    
    with open(results_file, 'r') as f:
        return json.load(f)


def print_summary():
    """Print summary of all extracted schemas"""
    
    datasets = ['Apache', 'HealthApp', 'Zookeeper', 'OpenStack', 'Proxifier']
    
    print("="*90)
    print("LogSim Schema Extraction Results Summary".center(90))
    print("="*90)
    print()
    
    # Table header
    print(f"{'Dataset':<15} {'Logs':<8} {'Templates':<12} {'Coverage':<10} {'Top Template':<40}")
    print("-"*90)
    
    all_results = []
    
    for dataset in datasets:
        result = load_results(dataset)
        if not result:
            continue
        
        all_results.append(result)
        
        # Get top template
        top_template = result['templates'][0] if result['templates'] else None
        top_pattern = top_template['pattern'][:37] + "..." if top_template and len(top_template['pattern']) > 40 else top_template['pattern'] if top_template else "N/A"
        
        print(f"{dataset:<15} "
              f"{result['sample_size']:<8} "
              f"{result['template_count']:<12} "
              f"{result['coverage']:.1f}%{'':<6} "
              f"{top_pattern:<40}")
    
    print("-"*90)
    
    # Overall statistics
    total_logs = sum(r['sample_size'] for r in all_results)
    total_templates = sum(r['template_count'] for r in all_results)
    avg_coverage = sum(r['coverage'] for r in all_results) / len(all_results) if all_results else 0
    
    print(f"\nTotal: {total_logs:,} logs processed, {total_templates} templates extracted")
    print(f"Average coverage: {avg_coverage:.1f}%")
    print()
    
    # Detailed view for each dataset
    for dataset in datasets:
        result = load_results(dataset)
        if not result:
            continue
        
        print("="*90)
        print(f" {dataset} - Top 5 Templates ".center(90, "="))
        print("="*90)
        print()
        
        for i, template in enumerate(result['templates'][:5], 1):
            print(f"{i}. {template['id']} ({template['matches']} matches, {template['coverage_percent']:.1f}%)")
            print(f"   Pattern: {template['pattern']}")
            print(f"   Example: {template['examples'][0][:85]}...")
            print()


if __name__ == "__main__":
    print_summary()
