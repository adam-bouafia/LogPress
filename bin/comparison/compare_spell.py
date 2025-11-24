#!/usr/bin/env python3
"""
Compare LogSim against Spell parser

Usage:
    python bin/comparison/compare_spell.py --dataset Apache --sample-size 1000
"""

import argparse
import json
import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from logparser.Spell import LogParser as SpellParser
except ImportError:
    print("ERROR: logparser library not installed!")
    print("Install with: pip install git+https://github.com/logpai/logparser.git")
    sys.exit(1)


def run_spell(dataset_name: str, sample_size: int = None):
    """Run Spell parser on specified dataset"""
    
    # Dataset configurations
    log_formats = {
        'Apache': '<Month> <Day> <Time> <Level> <Content>',
        'HealthApp': '<Time>|<Component>|<PID>|<Content>',
        'Zookeeper': '<Date> <Time> - <Level>  [<Node>:<Component>@<Id>] - <Content>',
        'OpenStack': '<Logrecord> <Date> <Time> <Pid> <Level> <Component> <Content>',
        'Proxifier': '<Time> <Program> - <Content>',
    }
    
    # Regex patterns for each dataset
    regex_patterns = {
        'Apache': r'\[(\w+)\s+(\w+\s+\d+)\s+([\d:]+)\s+(\d{4})\]\s+\[(\w+)\]\s+(.*)',
        'HealthApp': r'(\d{8}-[\d:]+)\|([^|]+)\|(\d+)\|(.*)',
        'Zookeeper': r'(\d{4}-\d{2}-\d{2})\s+([\d:,]+)\s+-\s+(\w+)\s+\[([^\]]+)\]\s+-\s+(.*)',
        'OpenStack': r'([\w\.-]+)\s+(\d{4}-\d{2}-\d{2})\s+([\d:\.]+)\s+(\d+)\s+(\w+)\s+([\w\.]+)\s+(.*)',
        'Proxifier': r'\[([\d\.]+\s+[\d:]+)\]\s+(\S+)\s+-\s+(.*)',
    }
    
    input_dir = Path(f'datasets/{dataset_name}')
    output_dir = Path(f'results/comparison/spell_{dataset_name.lower()}')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = f'{dataset_name}_full.log'
    
    print(f"\n{'='*60}")
    print(f"Running Spell on {dataset_name}")
    print(f"{'='*60}")
    
    # Load logs
    log_path = input_dir / log_file
    if not log_path.exists():
        print(f"ERROR: Log file not found: {log_path}")
        return None
    
    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        all_logs = f.readlines()
    
    # Sample if needed
    if sample_size and sample_size < len(all_logs):
        logs = all_logs[:sample_size]
        print(f"Sampling {sample_size} logs from {len(all_logs)} total")
    else:
        logs = all_logs
        print(f"Processing all {len(logs)} logs")
    
    # Write sampled logs to temp file
    temp_log_file = output_dir / f'{dataset_name}_sample.log'
    with open(temp_log_file, 'w', encoding='utf-8') as f:
        f.writelines(logs)
    
    # Initialize Spell parser
    parser = SpellParser(
        log_format=log_formats.get(dataset_name, '<Content>'),
        indir=str(output_dir),
        outdir=str(output_dir),
        tau=0.5,  # Similarity threshold
        rex=[regex_patterns.get(dataset_name, [])]
    )
    
    # Run Spell
    start_time = time.time()
    try:
        parser.parse(temp_log_file.name)
        parse_time = time.time() - start_time
    except Exception as e:
        print(f"ERROR: Spell parsing failed: {e}")
        return None
    
    # Load results
    structured_file = output_dir / f'{temp_log_file.stem}_structured.csv'
    templates_file = output_dir / f'{temp_log_file.stem}_templates.csv'
    
    templates = []
    if templates_file.exists():
        with open(templates_file, 'r') as f:
            lines = f.readlines()[1:]  # Skip header
            for line in lines:
                parts = line.strip().split(',', 1)
                if len(parts) == 2:
                    templates.append({
                        'event_id': parts[0],
                        'template': parts[1]
                    })
    
    # Collect statistics
    results = {
        'dataset': dataset_name,
        'total_logs': len(logs),
        'templates_found': len(templates),
        'parse_time_seconds': round(parse_time, 4),
        'throughput_logs_per_sec': round(len(logs) / parse_time, 2) if parse_time > 0 else 0,
        'templates': templates[:20],  # Store first 20 templates as samples
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # Save results
    output_file = output_dir / 'spell_results.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n{'='*60}")
    print(f"Spell Results for {dataset_name}")
    print(f"{'='*60}")
    print(f"Total logs:          {results['total_logs']:,}")
    print(f"Templates found:     {results['templates_found']:,}")
    print(f"Parse time:          {results['parse_time_seconds']:.4f}s")
    print(f"Throughput:          {results['throughput_logs_per_sec']:,.0f} logs/sec")
    print(f"\nResults saved to:    {output_file}")
    print(f"{'='*60}\n")
    
    return results


def main():
    parser = argparse.ArgumentParser(description='Run Spell parser comparison')
    parser.add_argument('--dataset', type=str, required=True,
                      choices=['Apache', 'HealthApp', 'Zookeeper', 'OpenStack', 'Proxifier'],
                      help='Dataset to process')
    parser.add_argument('--sample-size', type=int, default=None,
                      help='Number of logs to sample (default: all)')
    parser.add_argument('--output', type=str, default=None,
                      help='Output JSON file path (default: auto-generated)')
    
    args = parser.parse_args()
    
    results = run_spell(args.dataset, args.sample_size)
    
    if results and args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"Results also saved to: {args.output}")


if __name__ == '__main__':
    main()
