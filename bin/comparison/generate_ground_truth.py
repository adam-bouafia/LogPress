#!/usr/bin/env python3
"""
Generate ground truth annotation template

This script helps create structured annotation files by:
1. Extracting N random logs from a dataset
2. Running LogSim's semantic parser to get initial suggestions
3. Creating a JSON template that you can manually correct

Usage:
    python bin/comparison/generate_ground_truth.py --dataset Apache --count 100
"""

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from logsim.semantic_types import SemanticTypeDetector
from logsim.tokenizer import LogTokenizer


def generate_ground_truth_template(dataset_name: str, count: int = 100):
    """Generate ground truth template with LogSim suggestions"""
    
    input_dir = Path(f'datasets/{dataset_name}')
    output_dir = Path(f'ground_truth/{dataset_name.lower()}')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = f'{dataset_name}_full.log'
    log_path = input_dir / log_file
    
    if not log_path.exists():
        print(f"ERROR: Log file not found: {log_path}")
        return None
    
    print(f"Generating ground truth template for {dataset_name}")
    print(f"Sampling {count} logs...\n")
    
    # Load all logs
    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        all_logs = [line.strip() for line in f if line.strip()]
    
    # Sample random logs
    sampled_logs = random.sample(all_logs, min(count, len(all_logs)))
    
    # Initialize LogSim components
    tokenizer = LogTokenizer()
    detector = SemanticTypeDetector()
    
    ground_truth = {
        'dataset': dataset_name,
        'description': f'Ground truth annotations for {dataset_name} logs',
        'total_logs': len(sampled_logs),
        'annotation_date': '2025-11-23',
        'semantic_types': [
            'TIMESTAMP',
            'SEVERITY',
            'IP_ADDRESS',
            'PROCESS_ID',
            'FUNCTION_CALL',
            'MODULE',
            'USER_ID',
            'STATUS_CODE',
            'ERROR_CODE',
            'METRIC',
            'MESSAGE'
        ],
        'logs': [],
        'notes': [
            'This file was auto-generated with LogSim suggestions',
            'PLEASE MANUALLY REVIEW AND CORRECT EACH ANNOTATION',
            'Check field boundaries (start/end positions)',
            'Verify semantic type classifications',
            'Adjust confidence scores based on your judgment'
        ]
    }
    
    # Process each log
    for idx, log_line in enumerate(sampled_logs, start=1):
        # Tokenize
        tokens = tokenizer.tokenize(log_line)
        
        # Detect semantic types
        fields = []
        for token in tokens:
            semantic_type, confidence = detector.detect_type(token, log_line)
            if semantic_type != 'UNKNOWN':
                fields.append({
                    'type': semantic_type,
                    'value': token,
                    'start': log_line.find(token),
                    'end': log_line.find(token) + len(token),
                    'confidence': round(confidence, 2),
                    'note': 'AUTO-GENERATED - PLEASE VERIFY'
                })
        
        ground_truth['logs'].append({
            'id': idx,
            'raw': log_line,
            'fields': fields,
            'verified': False
        })
        
        if idx % 10 == 0:
            print(f"Processed {idx}/{len(sampled_logs)} logs...")
    
    # Save to file
    output_file = output_dir / f'{dataset_name.lower()}_ground_truth_draft.json'
    with open(output_file, 'w') as f:
        json.dump(ground_truth, f, indent=2)
    
    print(f"\nGenerated ground truth template: {output_file}")
    print(f"\n{'='*60}")
    print("NEXT STEPS:")
    print("1. Open the generated JSON file")
    print("2. Manually review EACH log annotation")
    print("3. Correct any wrong semantic type classifications")
    print("4. Adjust field boundaries if needed")
    print("5. Set 'verified': true for each reviewed log")
    print("6. Save as final ground truth file (remove '_draft' from filename)")
    print(f"{'='*60}\n")
    
    # Print sample
    print("\nSample annotation (first log):")
    print(json.dumps(ground_truth['logs'][0], indent=2))
    
    return output_file


def main():
    parser = argparse.ArgumentParser(description='Generate ground truth annotation template')
    parser.add_argument('--dataset', type=str, required=True,
                      choices=['Apache', 'HealthApp', 'Zookeeper', 'OpenStack', 'Proxifier'],
                      help='Dataset to process')
    parser.add_argument('--count', type=int, default=100,
                      help='Number of logs to annotate (default: 100)')
    parser.add_argument('--seed', type=int, default=42,
                      help='Random seed for reproducibility (default: 42)')
    
    args = parser.parse_args()
    
    # Set random seed
    random.seed(args.seed)
    
    generate_ground_truth_template(args.dataset, args.count)


if __name__ == '__main__':
    main()
