#!/usr/bin/env python3
"""
Fixed Drain comparison with proper log format specifications
"""

import sys
import json
import time
from pathlib import Path
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from logparser.Drain import LogParser as DrainParser
except ImportError:
    print("❌ logparser not installed. Run: pip install git+https://github.com/logpai/logparser.git")
    sys.exit(1)

from logsim.template_generator import TemplateGenerator


# Proper log format specifications for each dataset
LOG_FORMATS = {
    'Apache': {
        'log_format': '<Content>',  # Generic - Apache has varied formats
        'depth': 4,
        'st': 0.5
    },
    'HealthApp': {
        'log_format': '<Timestamp>|<Component>|<PID>|<Content>',
        'depth': 4,
        'st': 0.5
    },
    'Zookeeper': {
        'log_format': '<Timestamp> - <Level>  [<Node>] - <Content>',
        'depth': 5,
        'st': 0.4
    },
    'Proxifier': {
        'log_format': '[<Timestamp>] <Program> - <Content>',
        'depth': 3,
        'st': 0.5
    },
    'OpenStack': {
        'log_format': '<Logrecord> <Timestamp> <Pid> <Level> <Component> [<ADDR>] <Content>',
        'depth': 5,
        'st': 0.4
    }
}


def run_drain_fixed(dataset_path: str, dataset_name: str, sample_size: int = 5000) -> Dict[str, Any]:
    """Run Drain with proper configuration"""
    
    print(f"\n{'='*80}")
    print(f"Running Drain on {dataset_name} (fixed configuration)")
    print(f"{'='*80}\n")
    
    # Load logs
    with open(dataset_path, 'r', encoding='utf-8', errors='replace') as f:
        logs = [line.strip() for line in f if line.strip()][:sample_size]
    
    print(f"📊 Loaded {len(logs):,} logs\n")
    
    # Get configuration
    if dataset_name not in LOG_FORMATS:
        print(f"⚠️  No format configuration for {dataset_name}, using generic")
        log_format = '<Content>'
        depth = 4
        st = 0.5
    else:
        config = LOG_FORMATS[dataset_name]
        log_format = config['log_format']
        depth = config['depth']
        st = config['st']
    
    print(f"🔧 Drain Configuration:")
    print(f"   Log format: {log_format}")
    print(f"   Depth: {depth}")
    print(f"   Similarity threshold: {st}\n")
    
    # Create temp file for Drain (it needs file input)
    temp_file = Path(f'temp_{dataset_name}_drain.log')
    temp_file.write_text('\n'.join(logs))
    
    try:
        # Run Drain
        start_time = time.time()
        
        parser = DrainParser(
            log_format=log_format,
            indir=str(temp_file.parent),
            outdir='results/comparison/drain_output',
            depth=depth,
            st=st,
            rex=[],  # Use log_format instead of regex
            keep_para=True
        )
        
        parser.parse(temp_file.name)
        
        parse_time = time.time() - start_time
        
        # Load results
        template_file = Path('results/comparison/drain_output') / f'{temp_file.stem}_templates.csv'
        
        if template_file.exists():
            with open(template_file, 'r') as f:
                lines = f.readlines()[1:]  # Skip header
                templates = [line.strip() for line in lines if line.strip()]
        else:
            templates = []
        
        print(f"✅ Drain completed in {parse_time:.2f}s")
        print(f"📋 Templates found: {len(templates)}\n")
        
        if templates:
            print(f"Example templates:")
            for i, template in enumerate(templates[:5], 1):
                parts = template.split(',', 1)
                if len(parts) >= 2:
                    print(f"   {i}. {parts[1][:80]}...")
        
        result = {
            'dataset': dataset_name,
            'parser': 'Drain',
            'templates_found': len(templates),
            'parse_time': parse_time,
            'logs_processed': len(logs),
            'configuration': {
                'log_format': log_format,
                'depth': depth,
                'st': st
            }
        }
        
    finally:
        # Cleanup
        if temp_file.exists():
            temp_file.unlink()
    
    return result


def compare_with_logsim(dataset_path: str, dataset_name: str, sample_size: int = 5000) -> Dict[str, Any]:
    """Compare Drain vs LogSim"""
    
    # Run Drain
    drain_result = run_drain_fixed(dataset_path, dataset_name, sample_size)
    
    # Run LogSim
    print(f"\n{'='*80}")
    print(f"Running LogSim on {dataset_name}")
    print(f"{'='*80}\n")
    
    with open(dataset_path, 'r', encoding='utf-8', errors='replace') as f:
        logs = [line.strip() for line in f if line.strip()][:sample_size]
    
    start_time = time.time()
    generator = TemplateGenerator(min_support=5)
    templates = generator.extract_schemas(logs)
    logsim_time = time.time() - start_time
    
    print(f"✅ LogSim completed in {logsim_time:.2f}s")
    print(f"📋 Templates found: {len(templates)}\n")
    
    if templates:
        print(f"Example templates:")
        for i, template in enumerate(templates[:5], 1):
            print(f"   {i}. {template.pattern[:80]}...")
    
    # Comparison
    print(f"\n{'='*80}")
    print(f"📊 COMPARISON: {dataset_name}")
    print(f"{'='*80}\n")
    
    print(f"   Metric              | Drain    | LogSim   | Winner")
    print(f"   --------------------|----------|----------|--------")
    print(f"   Templates found     | {drain_result['templates_found']:>8} | {len(templates):>8} | {'Drain' if drain_result['templates_found'] > len(templates) else 'LogSim' if len(templates) > drain_result['templates_found'] else 'Tie'}")
    print(f"   Parse time (s)      | {drain_result['parse_time']:>8.2f} | {logsim_time:>8.2f} | {'Drain' if drain_result['parse_time'] < logsim_time else 'LogSim'}")
    print(f"   Throughput (logs/s) | {len(logs)/drain_result['parse_time']:>8.0f} | {len(logs)/logsim_time:>8.0f} | {'Drain' if len(logs)/drain_result['parse_time'] > len(logs)/logsim_time else 'LogSim'}")
    print()
    
    return {
        'drain': drain_result,
        'logsim': {
            'dataset': dataset_name,
            'parser': 'LogSim',
            'templates_found': len(templates),
            'parse_time': logsim_time,
            'logs_processed': len(logs)
        }
    }


def main():
    """Run fixed Drain comparison"""
    
    datasets = {
        'Apache': 'datasets/Apache/Apache_full.log',
        'HealthApp': 'datasets/HealthApp/HealthApp_full.log',
        'Zookeeper': 'datasets/Zookeeper/Zookeeper_full.log',
        'Proxifier': 'datasets/Proxifier/Proxifier_full.log'
    }
    
    results = {}
    
    for name, path in datasets.items():
        if Path(path).exists():
            try:
                result = compare_with_logsim(path, name, sample_size=5000)
                results[name] = result
            except Exception as e:
                print(f"❌ Error processing {name}: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"⚠️  Dataset not found: {path}")
    
    # Save results
    output_path = Path('results/comparison/drain_vs_logsim_fixed.json')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📊 Results saved to: {output_path}")


if __name__ == '__main__':
    main()
