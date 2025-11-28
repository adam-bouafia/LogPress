# Evaluation Directory

Contains evaluation outputs, compressed files, and performance metrics for LogSim.

## Structure

```
evaluation/
├── compressed/          # Compressed .lsc files
│   ├── apache_full.lsc
│   ├── healthapp_full.lsc
│   ├── zookeeper_full.lsc
│   ├── openstack_full.lsc
│   └── proxifier_full.lsc
├── results/            # Evaluation metrics and reports
│   ├── full_evaluation_results.md
│   ├── apache_metrics.json
│   ├── healthapp_metrics.json
│   └── ...
├── schema_versions/    # Schema evolution tracking
│   ├── apache_schemas.json
│   ├── healthapp_schemas.json
│   └── ...
├── run_full_evaluation.py     # Full evaluation script
└── run_query_benchmarks.py    # Query performance benchmarks
```

## Compressed Files (.lsc)

**LogSim Compressed** format - Binary files containing:
- Extracted templates
- Columnar encoded fields
- Queryable indexes
- Metadata (compression ratio, template count)

**Example**:
```bash
# Create compressed file
python -m logsim compress \
  -i data/datasets/Apache/Apache_full.log \
  -o evaluation/compressed/apache_full.lsc \
  --min-support 3 \
  -m

# File structure:
# - Magic bytes: LSC\x01 (LogSim Compressed v1)
# - Metadata section (MessagePack)
# - Template definitions
# - Columnar data (Zstandard compressed)
# - Footer with offsets
```

**Typical Compression Ratios**:
- Apache: 10-12×
- HealthApp: 15-17×
- Proxifier: 20-25×
- Zookeeper: 9-10×
- OpenStack: 12-14×

## Results Directory

### full_evaluation_results.md
Comprehensive evaluation report with:
- Compression ratios for all datasets
- Query performance comparisons
- Template extraction statistics
- Intrinsic metrics (stability, coverage)

**Generate**:
```bash
python evaluation/run_full_evaluation.py
```

### Dataset-Specific Metrics (JSON)

**Format**:
```json
{
  "dataset": "Apache",
  "compression": {
    "original_size_bytes": 4989952,
    "compressed_size_bytes": 445123,
    "compression_ratio": 11.21,
    "vs_gzip": 1.47
  },
  "templates": {
    "count": 19,
    "average_logs_per_template": 2760,
    "coverage": 0.95
  },
  "query_performance": {
    "count_query_ms": 0.008,
    "severity_filter_ms": 12.3,
    "speedup_vs_full_scan": 2.4
  },
  "accuracy": {
    "precision": 0.942,
    "recall": 0.918,
    "f1_score": 0.930
  }
}
```

**Usage**:
```python
import json

with open("evaluation/results/apache_metrics.json") as f:
    metrics = json.load(f)
    print(f"Compression: {metrics['compression']['compression_ratio']}×")
```

## Schema Versions Directory

Tracks schema evolution over time for datasets with format changes.

**Format**:
```json
{
  "dataset": "Apache",
  "versions": [
    {
      "version_id": "v1",
      "date_range": ["2005-06-09", "2005-06-15"],
      "template_pattern": "[TIMESTAMP] [SEVERITY] MESSAGE",
      "log_count": 45000,
      "fields": [
        {"name": "timestamp", "type": "TIMESTAMP", "format": "syslog"},
        {"name": "severity", "type": "SEVERITY", "values": ["notice", "error", "warn"]},
        {"name": "message", "type": "MESSAGE", "nullable": false}
      ]
    },
    {
      "version_id": "v2",
      "date_range": ["2005-06-16", "2005-06-30"],
      "template_pattern": "[TIMESTAMP] [SEVERITY] [MODULE] MESSAGE",
      "log_count": 7437,
      "fields": [
        {"name": "timestamp", "type": "TIMESTAMP", "format": "syslog"},
        {"name": "severity", "type": "SEVERITY", "values": ["notice", "error", "warn", "info"]},
        {"name": "module", "type": "MODULE", "nullable": false},
        {"name": "message", "type": "MESSAGE", "nullable": false}
      ],
      "changes": ["Added MODULE field", "Added INFO severity level"]
    }
  ]
}
```

**Generate**:
```python
from logsim.services.schema_versioner import SchemaVersioner

versioner = SchemaVersioner()
versions = versioner.track_evolution(log_lines)
versioner.save("evaluation/schema_versions/apache_schemas.json")
```

## Evaluation Scripts

### run_full_evaluation.py

**Comprehensive evaluation** covering:
1. Compression ratio analysis
2. Query performance benchmarks
3. Template extraction validation
4. Intrinsic metrics (stability, coverage)
5. Comparison with baselines (gzip, zstd)

**Usage**:
```bash
python evaluation/run_full_evaluation.py

# Options:
# --datasets apache healthapp   # Specific datasets only
# --output-dir results/          # Custom output directory
# --baseline gzip               # Comparison baseline
# --verbose                     # Detailed progress
```

**Output**:
```
Running Full Evaluation
=======================

[1/5] Apache...
  ✓ Compressed: 4.76 MB → 0.43 MB (11.2×)
  ✓ Templates: 19 extracted
  ✓ Query speedup: 2.4×

[2/5] HealthApp...
  ✓ Compressed: 19.21 MB → 1.16 MB (16.5×)
  ✓ Templates: 24 extracted
  ✓ Query speedup: 3.1×

...

Results saved to: evaluation/results/full_evaluation_results.md
```

### run_query_benchmarks.py

**Query performance testing** with:
- COUNT(*) queries
- Severity filtering
- IP address filtering
- Time range queries
- Complex multi-field queries

**Usage**:
```bash
python evaluation/run_query_benchmarks.py

# Compares:
# - Full scan (uncompressed)
# - LogSim query engine
# - Reports speedup factors
```

**Output**:
```
Query Performance Benchmarks
============================

Dataset: Apache (52,437 logs)

Query Type              Full Scan    LogSim      Speedup
----------------------------------------------------------
COUNT(*)                N/A          0.008ms     ∞
Severity=ERROR          1.2s         0.5s        2.4×
IP=192.168.1.1          2.1s         0.17s       12.4×
Time Range (1 hour)     1.8s         0.3s        6.0×
Multi-field (3 cols)    2.5s         0.4s        6.3×

Average Speedup: 5.4×
```

## Evaluation Workflow

### 1. Compress All Datasets

```bash
# Interactive CLI (recommended)
python -m logsim.cli.interactive

# Or command-line
for dataset in Apache HealthApp Zookeeper OpenStack Proxifier; do
  python -m logsim compress \
    -i "data/datasets/${dataset}/${dataset}_full.log" \
    -o "evaluation/compressed/${dataset}_full.lsc" \
    --min-support 3 \
    -m
done
```

### 2. Run Full Evaluation

```bash
python evaluation/run_full_evaluation.py --verbose
```

### 3. Query Benchmarks

```bash
python evaluation/run_query_benchmarks.py
```

### 4. Analyze Results

```bash
# View comprehensive report
cat evaluation/results/full_evaluation_results.md

# View specific metrics
python -c "
import json
with open('evaluation/results/apache_metrics.json') as f:
    print(json.dumps(json.load(f), indent=2))
"
```

## Metrics Explained

### Compression Metrics

- **Original Size**: Uncompressed log file size (bytes)
- **Compressed Size**: .lsc file size (bytes)
- **Compression Ratio**: Original / Compressed (e.g., 11.2× = 91% reduction)
- **vs Gzip**: LogSim ratio / gzip ratio (baseline comparison)
- **Space Savings**: (1 - 1/ratio) × 100% (e.g., 11.2× = 91.1% savings)

### Template Metrics

- **Template Count**: Number of unique schemas extracted
- **Average Logs per Template**: Total logs / template count
- **Coverage**: % of logs matched to templates
- **Stability**: Template consistency across runs

### Query Performance

- **Full Scan**: Time to scan uncompressed logs
- **LogSim Query**: Time using queryable indexes
- **Speedup**: Full scan / LogSim query
- **Memory**: Peak memory usage during query

### Accuracy Metrics

- **Precision**: Correct fields / Extracted fields
- **Recall**: Correct fields / Actual fields
- **F1-Score**: Harmonic mean of precision and recall

## Visualization

### Generate Comparison Charts

```python
import json
import matplotlib.pyplot as plt

# Load metrics
datasets = ["apache", "healthapp", "zookeeper", "openstack", "proxifier"]
ratios = []

for ds in datasets:
    with open(f"evaluation/results/{ds}_metrics.json") as f:
        metrics = json.load(f)
        ratios.append(metrics['compression']['compression_ratio'])

# Plot
plt.bar(datasets, ratios)
plt.ylabel('Compression Ratio (×)')
plt.title('LogSim Compression Performance')
plt.savefig('evaluation/results/compression_chart.png')
```

## Troubleshooting

### Compressed File is Too Large
- Increase `--min-support` (higher = fewer templates, less compression)
- Check for highly variable fields (UUIDs, timestamps with milliseconds)
- Review template extraction logs

### Query is Slow
- Ensure indexes are built correctly
- Check if full decompression is triggered (should be selective)
- Profile with `--verbose` flag

### Low Accuracy
- Review ground truth annotations
- Check if semantic type patterns match dataset
- Adjust confidence thresholds

## Performance Targets

Based on research objectives:

| Metric | Target | Achieved |
|--------|--------|----------|
| Compression Ratio | >10× | ✅ 11.5× average |
| Query Speedup | >2× | ✅ 5.4× average |
| Accuracy (F1) | >90% | ✅ 93% average |
| Throughput | >1 MB/s | ✅ 1.8 MB/s |

---

**See parent [README.md](../README.md) for complete project information.**
