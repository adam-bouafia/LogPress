"""
Intrinsic evaluation metrics that don't require ground truth annotations.

These metrics validate schema extraction quality without manual labeling:
1. Template Coverage: % of logs matching extracted templates
2. Field Type Consistency: % of fields conforming to semantic types
3. Template Stability: Similarity between independent extraction runs
"""

import re
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Any
from collections import defaultdict

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def calculate_template_coverage(templates: List, logs: List[str]) -> Tuple[float, int, int]:
    """
    Calculate percentage of logs that match at least one template.
    
    Args:
        templates: List of LogTemplate objects
        logs: Original log lines
        
    Returns:
        Tuple of (coverage percentage, matched count, total count)
    """
    matched = 0
    for log in logs:
        tokens = log.split()
        for template in templates:
            # Access pattern attribute directly (LogTemplate is a dataclass)
            pattern = template.pattern if hasattr(template, 'pattern') else []
            if len(tokens) == len(pattern):
                # Simple matching: check if variable positions align
                match = True
                for token, pattern_part in zip(tokens, pattern):
                    if not (pattern_part.startswith('[') and pattern_part.endswith(']')):
                        # Constant token - must match exactly
                        if token != pattern_part:
                            match = False
                            break
                if match:
                    matched += 1
                    break
    
    coverage = matched / len(logs) if logs else 0.0
    return coverage, matched, len(logs)


def is_valid_timestamp(value: str) -> bool:
    """Check if value parses as a timestamp using common formats"""
    timestamp_formats = [
        "%Y-%m-%d %H:%M:%S",           # 2005-06-09 06:07:04
        "%a %b %d %H:%M:%S %Y",        # Thu Jun 09 06:07:04 2005
        "%Y-%m-%d %H:%M:%S,%f",        # 2015-07-29 17:41:41,536
        "%Y%m%d-%H:%M:%S:%f",          # 20171223-22:15:29:606
        "[%a %b %d %H:%M:%S %Y]",      # [Thu Jun 09 06:07:04 2005]
    ]
    
    # Remove brackets if present
    clean_value = value.strip('[]')
    
    for fmt in timestamp_formats:
        try:
            datetime.strptime(clean_value, fmt)
            return True
        except (ValueError, TypeError):
            continue
    
    # Try Unix timestamp (milliseconds or seconds)
    try:
        ts = float(clean_value)
        return 1000000000 < ts < 2000000000000  # 2001-2033 range (ms or sec)
    except (ValueError, TypeError):
        return False


def is_valid_ip(value: str) -> bool:
    """Check if value is a valid IPv4 or IPv6 address"""
    ipv4_pattern = r"^(\d{1,3}\.){3}\d{1,3}$"
    ipv6_pattern = r"^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$"
    
    if re.match(ipv4_pattern, value):
        octets = [int(x) for x in value.split(".")]
        return all(0 <= octet <= 255 for octet in octets)
    
    return bool(re.match(ipv6_pattern, value))


def is_valid_severity(value: str) -> bool:
    """Check if value is a known severity level"""
    known_severities = {
        "info", "warn", "warning", "error", "err", "debug", "fatal",
        "notice", "critical", "crit", "alert", "emerg", "emergency",
        "trace", "verbose"
    }
    return value.lower() in known_severities


def calculate_field_type_consistency(logs: List[str], templates: List) -> Dict[str, Dict[str, Any]]:
    """
    Validate that extracted fields conform to their assigned semantic types.
    
    Args:
        logs: Original log lines
        templates: List of LogTemplate objects
    
    Returns:
        Dict mapping field type to validation results
    """
    from logpress.semantic_types import classify_token
    
    field_stats = defaultdict(lambda: {"total": 0, "valid": 0, "examples": []})
    
    # Sample logs for validation (take up to 1000 for speed)
    sample_logs = logs[:min(1000, len(logs))]
    
    for log in sample_logs:
        # Simple tokenization (space-separated)
        tokens = log.split()
        
        for token in tokens:
            field_type = classify_token(token)
            
            if field_type == "TIMESTAMP":
                field_stats["TIMESTAMP"]["total"] += 1
                if is_valid_timestamp(token):
                    field_stats["TIMESTAMP"]["valid"] += 1
                if len(field_stats["TIMESTAMP"]["examples"]) < 5:
                    field_stats["TIMESTAMP"]["examples"].append(token)
            
            elif field_type == "IP_ADDRESS":
                field_stats["IP_ADDRESS"]["total"] += 1
                if is_valid_ip(token):
                    field_stats["IP_ADDRESS"]["valid"] += 1
                if len(field_stats["IP_ADDRESS"]["examples"]) < 5:
                    field_stats["IP_ADDRESS"]["examples"].append(token)
            
            elif field_type == "SEVERITY":
                field_stats["SEVERITY"]["total"] += 1
                if is_valid_severity(token):
                    field_stats["SEVERITY"]["valid"] += 1
                if len(field_stats["SEVERITY"]["examples"]) < 5:
                    field_stats["SEVERITY"]["examples"].append(token)
    
    # Calculate accuracy percentages
    results = {}
    for field_type, stats in field_stats.items():
        if stats["total"] > 0:
            accuracy = stats["valid"] / stats["total"]
            results[field_type] = {
                "accuracy": accuracy,
                "total": stats["total"],
                "valid": stats["valid"],
                "examples": stats["examples"][:3]  # Keep only 3 examples
            }
    
    return results


def calculate_template_stability(dataset_path: str, num_runs: int = 3) -> Tuple[float, Dict]:
    """
    Run template extraction multiple times and measure similarity.
    
    Args:
        dataset_path: Path to log file
        num_runs: Number of independent extraction runs (default 3)
        
    Returns:
        Tuple of (Jaccard similarity, detailed stats)
    """
    from logpress.template_generator import TemplateGenerator
    
    # Load logs once
    with open(dataset_path, 'r', encoding='utf-8', errors='ignore') as f:
        logs = [line.rstrip('\n\r') for line in f if line.strip()]
    
    template_sets = []
    template_counts = []
    
    for run in range(num_runs):
        generator = TemplateGenerator()
        templates = generator.extract_schemas(logs)
        
        # Create signature for each template (pattern as tuple)
        signatures = set()
        for template in templates:
            # Access pattern attribute directly (LogTemplate is a dataclass)
            pattern = tuple(template.pattern if hasattr(template, 'pattern') else [])
            signatures.add(pattern)
        
        template_sets.append(signatures)
        template_counts.append(len(signatures))
    
    # Calculate pairwise Jaccard similarities
    similarities = []
    for i in range(len(template_sets)):
        for j in range(i + 1, len(template_sets)):
            intersection = len(template_sets[i] & template_sets[j])
            union = len(template_sets[i] | template_sets[j])
            similarity = intersection / union if union > 0 else 1.0
            similarities.append(similarity)
    
    avg_similarity = sum(similarities) / len(similarities) if similarities else 1.0
    
    stats = {
        "avg_similarity": avg_similarity,
        "template_counts": template_counts,
        "min_templates": min(template_counts),
        "max_templates": max(template_counts),
        "avg_templates": sum(template_counts) / len(template_counts),
        "num_runs": num_runs
    }
    
    return avg_similarity, stats


def run_intrinsic_evaluation(dataset_path: str, output_path: str = None) -> Dict:
    """
    Run all intrinsic metrics on a dataset.
    
    Args:
        dataset_path: Path to log file
        output_path: Optional path to save JSON results
        
    Returns:
        Dict with all evaluation metrics
    """
    from logpress.template_generator import TemplateGenerator
    
    dataset_name = Path(dataset_path).parent.name
    print(f"\n{'='*80}")
    print(f"INTRINSIC EVALUATION: {dataset_name}")
    print(f"{'='*80}\n")
    
    # Load logs
    print(f"📂 Loading logs from {dataset_path}")
    with open(dataset_path, 'r', encoding='utf-8', errors='ignore') as f:
        logs = [line.rstrip('\n\r') for line in f if line.strip()]
    print(f"✓ Loaded {len(logs):,} logs\n")
    
    # Extract templates
    print("🔍 Extracting templates...")
    generator = TemplateGenerator()
    templates = generator.extract_schemas(logs)
    print(f"✓ Extracted {len(templates)} templates\n")
    
    # Metric 1: Template Coverage
    print("📊 Calculating template coverage...")
    coverage, matched, total = calculate_template_coverage(templates, logs)
    print(f"✓ Coverage: {coverage:.1%} ({matched:,} / {total:,} logs matched)\n")
    
    # Metric 2: Field Type Consistency (SKIPPED - not critical for thesis)
    consistency = {}  # Skip for now
    
    # Metric 3: Template Stability
    print("🔄 Measuring template stability (3 independent runs)...")
    stability, stability_stats = calculate_template_stability(dataset_path, num_runs=3)
    print(f"✓ Stability: {stability:.1%} (Jaccard similarity)")
    print(f"  • Template counts: {stability_stats['template_counts']}")
    print(f"  • Average: {stability_stats['avg_templates']:.1f} templates\n")
    
    # Compile results
    results = {
        "dataset": dataset_name,
        "dataset_path": str(dataset_path),
        "log_count": len(logs),
        "template_count": len(templates),
        "metrics": {
            "template_coverage": {
                "percentage": coverage,
                "matched_logs": matched,
                "total_logs": total
            },
            "field_type_consistency": consistency,
            "template_stability": {
                "jaccard_similarity": stability,
                "runs": stability_stats["num_runs"],
                "template_counts": stability_stats["template_counts"],
                "avg_templates": stability_stats["avg_templates"]
            }
        }
    }
    
    # Save results if output path provided
    if output_path:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"💾 Results saved to {output_path}\n")
    
    # Print summary
    print(f"{'='*80}")
    print(f"SUMMARY: {dataset_name}")
    print(f"{'='*80}")
    print(f"Template Coverage:     {coverage:.1%}")
    print(f"Field Consistency:     {sum(s['accuracy'] for s in consistency.values()) / len(consistency):.1%} (avg)" if consistency else "N/A")
    print(f"Template Stability:    {stability:.1%}")
    print(f"{'='*80}\n")
    
    return results


def main():
    """Run intrinsic evaluation on all datasets"""
    import sys
    
    datasets = [
        "datasets/Apache/Apache_full.log",
        "datasets/HealthApp/HealthApp_full.log",
        "datasets/Proxifier/Proxifier_full.log",
        "datasets/Zookeeper/Zookeeper_full.log"
    ]
    
    all_results = []
    
    for dataset in datasets:
        dataset_path = Path(dataset)
        if not dataset_path.exists():
            print(f"⚠️  Skipping {dataset} (not found)")
            continue
        
        dataset_name = dataset_path.parent.name
        output_path = f"results/intrinsic_{dataset_name.lower()}.json"
        
        try:
            results = run_intrinsic_evaluation(str(dataset_path), output_path)
            all_results.append(results)
        except Exception as e:
            print(f"❌ Error evaluating {dataset_name}: {e}")
            import traceback
            traceback.print_exc()
    
    # Generate summary table
    if all_results:
        print("\n" + "="*80)
        print("OVERALL SUMMARY: INTRINSIC METRICS")
        print("="*80)
        print(f"{'Dataset':<15} {'Coverage':<12} {'Stability':<12} {'Templates':<12}")
        print("-"*80)
        
        for result in all_results:
            dataset = result['dataset']
            coverage = result['metrics']['template_coverage']['percentage']
            stability = result['metrics']['template_stability']['jaccard_similarity']
            templates = result['template_count']
            
            print(f"{dataset:<15} {coverage:>10.1%}  {stability:>10.1%}  {templates:>10}")
        
        print("="*80)
        
        # Calculate averages
        avg_coverage = sum(r['metrics']['template_coverage']['percentage'] for r in all_results) / len(all_results)
        avg_stability = sum(r['metrics']['template_stability']['jaccard_similarity'] for r in all_results) / len(all_results)
        
        print(f"\nAverage Coverage:  {avg_coverage:.1%}")
        print(f"Average Stability: {avg_stability:.1%}")
        print()


if __name__ == "__main__":
    main()
