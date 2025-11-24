#!/usr/bin/env python3
"""
Train a universal Zstandard dictionary from all datasets

This script collects samples from Apache, HealthApp, Zookeeper, and Proxifier
datasets and trains a 64KB dictionary that can be used across all log types
for improved compression.

Expected gain: +2-3% (16.46x → 16.9x)
"""

import sys
from pathlib import Path
import zstandard as zstd
import json

# Add logsim to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from logsim.compressor import SemanticCompressor


def collect_samples_from_dataset(dataset_path: Path, sample_size: int = 2000) -> list:
    """Collect sample logs from a dataset"""
    log_file = list(dataset_path.glob("*_full.log"))
    
    if not log_file:
        # Try alternative naming
        log_file = list(dataset_path.glob("*.log"))
    
    if not log_file:
        print(f"⚠️  No log file found in {dataset_path}")
        return []
    
    log_file = log_file[0]
    
    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        logs = [line.strip() for line in f if line.strip()][:sample_size]
    
    print(f"   Collected {len(logs)} samples from {dataset_path.name}")
    return logs


def train_universal_dictionary(output_path: Path, dict_size: int = 65536):
    """
    Train a universal Zstandard dictionary from all datasets
    
    Args:
        output_path: Path to save the trained dictionary
        dict_size: Dictionary size in bytes (default 64KB)
    """
    print("🎓 Training universal Zstandard dictionary from all datasets")
    print(f"   Target size: {dict_size:,} bytes")
    print()
    
    # Dataset paths
    datasets_dir = Path("datasets")
    datasets = ["Apache", "HealthApp", "Zookeeper", "Proxifier"]
    
    # Collect samples from each dataset
    all_samples = []
    
    print("📊 Collecting training samples...")
    for dataset_name in datasets:
        dataset_path = datasets_dir / dataset_name
        if dataset_path.exists():
            samples = collect_samples_from_dataset(dataset_path, sample_size=2000)
            all_samples.extend(samples)
        else:
            print(f"⚠️  Dataset {dataset_name} not found at {dataset_path}")
    
    if not all_samples:
        print("❌ No samples collected. Cannot train dictionary.")
        return None
    
    print(f"\n✓ Total samples collected: {len(all_samples):,} logs")
    print(f"  Corpus size: {sum(len(s) for s in all_samples):,} bytes")
    
    # Compress and parse logs to extract field values
    print("\n🔍 Extracting semantic fields from samples...")
    compressor = SemanticCompressor()
    compressed, stats = compressor.compress(all_samples, verbose=False)
    
    # Build training corpus from extracted fields
    training_corpus = []
    
    # Add messages (most diverse content)
    if compressed.message_list:
        training_corpus.extend([msg for msg in compressed.message_list if msg])
        print(f"   Added {len(compressed.message_list):,} unique messages")
    
    # Add severity patterns
    if compressed.severity_list:
        training_corpus.extend(compressed.severity_list * 10)  # Repeat for frequency
        print(f"   Added {len(compressed.severity_list)} unique severities")
    
    # Add IP addresses
    if compressed.ip_list:
        training_corpus.extend(compressed.ip_list * 5)
        print(f"   Added {len(compressed.ip_list):,} unique IPs")
    
    # Add template patterns (reconstruct from token pool)
    if compressed.token_pool:
        training_corpus.extend(compressed.token_pool * 20)  # Templates are very repetitive
        print(f"   Added {len(compressed.token_pool)} unique tokens")
    
    if not training_corpus:
        print("❌ No training corpus built. Using raw logs instead.")
        training_corpus = all_samples[:5000]
    
    print(f"\n📚 Training corpus: {len(training_corpus):,} items")
    
    # Convert to bytes for zstd training
    # Zstd train_dictionary expects a list of samples
    # Each sample should be 1-10KB for best results
    samples = []
    
    # Create samples by grouping training corpus items
    chunk_size = 100  # items per sample
    for i in range(0, len(training_corpus), chunk_size):
        chunk = training_corpus[i:i+chunk_size]
        sample_text = '\n'.join(str(item) for item in chunk)
        samples.append(sample_text.encode('utf-8'))
    
    total_corpus_size = sum(len(s) for s in samples)
    print(f"   Created {len(samples)} training samples")
    print(f"   Total corpus: {total_corpus_size:,} bytes")
    
    # Train dictionary
    print(f"\n🏋️  Training {dict_size//1024}KB dictionary...")
    try:
        dict_data = zstd.train_dictionary(dict_size, samples)
        dict_bytes = dict_data.as_bytes()
        
        print(f"✅ Dictionary trained successfully!")
        print(f"   Size: {len(dict_bytes):,} bytes")
        
        # Save dictionary
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(dict_bytes)
        
        print(f"\n💾 Saved dictionary to: {output_path}")
        
        # Save metadata
        metadata = {
            'dict_size': len(dict_bytes),
            'training_samples': len(all_samples),
            'corpus_items': len(training_corpus),
            'corpus_bytes': total_corpus_size,
            'datasets': datasets,
            'message_count': len(compressed.message_list) if compressed.message_list else 0,
            'severity_count': len(compressed.severity_list) if compressed.severity_list else 0,
            'ip_count': len(compressed.ip_list) if compressed.ip_list else 0,
            'token_count': len(compressed.token_pool) if compressed.token_pool else 0
        }
        
        metadata_path = output_path.with_suffix('.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"   Metadata saved to: {metadata_path}")
        
        return dict_bytes
        
    except Exception as e:
        print(f"❌ Dictionary training failed: {e}")
        return None


if __name__ == '__main__':
    output_path = Path("logsim/universal_dict.zstd")
    
    dict_bytes = train_universal_dictionary(output_path, dict_size=65536)
    
    if dict_bytes:
        print("\n" + "="*60)
        print("✅ Universal dictionary training complete!")
        print("="*60)
        print("\nNext steps:")
        print("1. Update compressor.py to load and use this dictionary")
        print("2. Run benchmarks to measure compression improvement")
        print("3. Expected gain: +2-3% (16.46x → 16.9x)")
    else:
        sys.exit(1)
