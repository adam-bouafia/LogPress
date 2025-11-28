# Results Directory
# All evaluation results are stored here

## Structure

- `compression/` - logpress compression benchmarks (vs Gzip)
- `accuracy/` - Schema extraction accuracy evaluations
- `comparison/` - Drain/Spell comparison results
- `ablation/` - Component contribution analysis
- `scalability/` - Scalability test results

## Usage

View results with:
```bash
python bin/view_benchmarks.py results/compression/apache.json
```

Or directly inspect JSON files for thesis tables.

## Files Generated

Each benchmark creates JSON files with:
- Compression ratios
- Query performance metrics
- Throughput measurements
- Memory usage statistics
- Detailed breakdowns by field type
