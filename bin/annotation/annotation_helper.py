#!/usr/bin/env python3
"""
Interactive annotation helper for ground truth generation
Speeds up annotation process by suggesting templates and allowing quick review
"""

import sys
import json
from pathlib import Path
from typing import List, Dict, Any
import random

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from logsim.template_generator import TemplateGenerator
from logsim.tokenizer import LogTokenizer


def suggest_annotations(logs: List[str], num_samples: int = 100) -> List[Dict[str, Any]]:
    """Generate annotation suggestions using LogSim"""
    
    print(f"\n🤖 Generating template suggestions for {len(logs)} logs...\n")
    
    # Extract templates
    generator = TemplateGenerator(min_support=5)
    templates = generator.extract_schemas(logs)
    
    print(f"✅ Found {len(templates)} templates\n")
    
    # Sample logs for annotation
    sampled_logs = random.sample(logs, min(num_samples, len(logs)))
    
    annotations = []
    
    for log in sampled_logs:
        # Tokenize
        tokenizer = LogTokenizer()
        token_objs = tokenizer.tokenize(log)
        tokens = [t.value for t in token_objs if t.value.strip()]
        
        # Find matching template
        best_match = None
        best_score = 0
        
        for template in templates:
            # Token matching: count token overlap
            template_tokens = set(' '.join(template.pattern).split())
            log_tokens = set(tokens)
            
            overlap = len(template_tokens & log_tokens)
            score = overlap / max(len(template_tokens), 1)
            
            if score > best_score:
                best_score = score
                best_match = template
        
        annotations.append({
            'log': log,
            'suggested_template': ' '.join(best_match.pattern) if best_match else '<UNKNOWN>',
            'confidence': best_score,
            'tokens': tokens,
            'verified': False
        })
    
    return annotations


def interactive_annotation(dataset_path: str, dataset_name: str, num_samples: int = 100):
    """Interactive annotation mode - review each annotation"""
    
    print(f"\n{'='*80}")
    print(f"🎯 Interactive Annotation: {dataset_name}")
    print(f"{'='*80}\n")
    
    # Load logs
    with open(dataset_path, 'r', encoding='utf-8', errors='replace') as f:
        logs = [line.strip() for line in f if line.strip()]
    
    print(f"📊 Loaded {len(logs):,} logs")
    
    # Generate suggestions
    annotations = suggest_annotations(logs, num_samples)
    
    print(f"\n{'='*80}")
    print(f"📝 Review Suggestions (Enter 'y' to accept, 'n' to reject, 'q' to quit)")
    print(f"{'='*80}\n")
    
    accepted = []
    
    for i, annotation in enumerate(annotations, 1):
        print(f"\n[{i}/{len(annotations)}]")
        print(f"Log: {annotation['log'][:100]}...")
        print(f"Template: {annotation['suggested_template'][:100]}...")
        print(f"Confidence: {annotation['confidence']:.2%}")
        
        response = input(f"\nAccept? (y/n/q): ").strip().lower()
        
        if response == 'q':
            print("\n⏹️  Stopping annotation")
            break
        elif response == 'y':
            annotation['verified'] = True
            accepted.append(annotation)
            print("✅ Accepted")
        else:
            print("❌ Rejected")
    
    # Save results
    output_path = Path(f'ground_truth/{dataset_name.lower()}/annotations_interactive.json')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump({
            'dataset': dataset_name,
            'total_reviewed': i,
            'accepted': len(accepted),
            'annotations': accepted
        }, f, indent=2)
    
    print(f"\n✅ Saved {len(accepted)} annotations to: {output_path}")
    print(f"📊 Acceptance rate: {len(accepted)/i:.1%}")


def batch_generate_suggestions(dataset_path: str, dataset_name: str, num_samples: int = 100):
    """Batch mode - generate suggestions for manual review"""
    
    print(f"\n{'='*80}")
    print(f"🤖 Batch Annotation: {dataset_name}")
    print(f"{'='*80}\n")
    
    # Load logs
    with open(dataset_path, 'r', encoding='utf-8', errors='replace') as f:
        logs = [line.strip() for line in f if line.strip()]
    
    print(f"📊 Loaded {len(logs):,} logs")
    
    # Generate suggestions
    annotations = suggest_annotations(logs, num_samples)
    
    # Group by template for easier review
    by_template = {}
    for annotation in annotations:
        template = annotation['suggested_template']
        if template not in by_template:
            by_template[template] = []
        by_template[template].append(annotation)
    
    print(f"\n📊 Summary:")
    print(f"   {len(annotations)} annotations generated")
    print(f"   {len(by_template)} unique templates")
    print(f"   Avg confidence: {sum(a['confidence'] for a in annotations)/len(annotations):.1%}")
    
    # Save results
    output_path = Path(f'ground_truth/{dataset_name.lower()}/annotations_batch.json')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump({
            'dataset': dataset_name,
            'total_generated': len(annotations),
            'unique_templates': len(by_template),
            'annotations': annotations,
            'by_template': {
                template: {
                    'count': len(logs),
                    'examples': logs[:3]  # First 3 examples
                }
                for template, logs in by_template.items()
            }
        }, f, indent=2)
    
    print(f"\n✅ Saved suggestions to: {output_path}")
    print(f"📝 Review the file and mark 'verified': true for correct annotations")


def main():
    """Main entry point"""
    
    datasets = {
        'Apache': 'datasets/Apache/Apache_full.log',
        'HealthApp': 'datasets/HealthApp/HealthApp_full.log',
        'Zookeeper': 'datasets/Zookeeper/Zookeeper_full.log',
        'Proxifier': 'datasets/Proxifier/Proxifier_full.log'
    }
    
    print(f"\n{'='*80}")
    print(f"🎯 Annotation Helper")
    print(f"{'='*80}\n")
    print(f"Modes:")
    print(f"  1. Interactive - Review each annotation (slower, higher quality)")
    print(f"  2. Batch - Generate suggestions for manual review (faster)")
    print()
    
    mode = input("Select mode (1/2): ").strip()
    
    print(f"\nDatasets:")
    for i, name in enumerate(datasets.keys(), 1):
        print(f"  {i}. {name}")
    print()
    
    dataset_idx = int(input("Select dataset (1-4): ").strip()) - 1
    dataset_name = list(datasets.keys())[dataset_idx]
    dataset_path = datasets[dataset_name]
    
    num_samples = int(input("Number of samples (default 100): ").strip() or "100")
    
    if not Path(dataset_path).exists():
        print(f"❌ Dataset not found: {dataset_path}")
        return
    
    if mode == '1':
        interactive_annotation(dataset_path, dataset_name, num_samples)
    elif mode == '2':
        batch_generate_suggestions(dataset_path, dataset_name, num_samples)
    else:
        print("❌ Invalid mode")


if __name__ == '__main__':
    main()
