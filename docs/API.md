# LogSim API Reference

## Core Modules

### logsim.template_generator

Extract log schemas using log alignment algorithm.

#### TemplateGenerator

```python
class TemplateGenerator:
    def __init__(self, min_support: int = 5, similarity_threshold: float = 0.8)
    def extract_schemas(self, logs: List[str], verbose: bool = False) -> List[Template]
```

**Parameters:**
- `min_support`: Minimum number of logs required to form a template
- `similarity_threshold`: Threshold for grouping similar log structures

**Returns:**
- List of `Template` objects with fields: `template_id`, `pattern`, `fields`, `count`, `examples`

**Example:**

```python
from logsim.template_generator import TemplateGenerator

generator = TemplateGenerator(min_support=5)
templates = generator.extract_schemas(logs, verbose=True)

for t in templates:
    print(f"Template: {t.pattern}")
    print(f"Matches: {t.count} logs ({t.count/len(logs)*100:.1f}%)")
```

---

### logsim.compressor

Compress logs with semantic-aware codecs.

#### SemanticCompressor

```python
class SemanticCompressor:
    def __init__(self, min_support: int = 5)
    def compress(self, logs: List[str], verbose: bool = False) -> Tuple[CompressedLog, Dict]
    def save(self, filepath: Path)
    @staticmethod
    def load(filepath: Path) -> CompressedLog
    def decompress(self) -> List[str]
```

**Methods:**

- `compress()`: Returns (CompressedLog, stats_dict)
  - Stats include: compression_ratio, original_size, compressed_size
- `save()`: Write compressed data to file
- `load()`: Load compressed data from file (class method)
- `decompress()`: Restore original logs

**Example:**

```python
from logsim.compressor import SemanticCompressor

compressor = SemanticCompressor(min_support=5)
compressed, stats = compressor.compress(logs, verbose=True)

print(f"Ratio: {stats['compression_ratio']:.2f}x")
compressor.save('output.lsc')

# Load and decompress
loaded = SemanticCompressor.load('output.lsc')
restored = loaded.decompress()
```

---

### logsim.query_engine

Query compressed logs without decompression.

#### QueryEngine

```python
class QueryEngine:
    def __init__(self, compressed_path: Path)
    def count_all(self) -> QueryResult
    def query_by_severity(self, severity: str) -> QueryResult
    def query_by_ip(self, ip: str) -> QueryResult
    def get_statistics(self) -> Dict
```

**QueryResult fields:**
- `matched_count`: Number of matching logs
- `scanned_count`: Number of entries scanned
- `execution_time`: Query time in seconds
- `logs`: List of matching log entries

**Example:**

```python
from logsim.query_engine import QueryEngine

engine = QueryEngine('output.lsc')

# Count total logs
result = engine.count_all()
print(f"Total: {result.matched_count} logs")

# Filter by severity
errors = engine.query_by_severity('ERROR')
print(f"Errors: {errors.matched_count} ({errors.execution_time*1000:.2f}ms)")

# Statistics
stats = engine.get_statistics()
print(f"Unique IPs: {stats['unique_ips']}")
print(f"Unique severities: {stats['unique_severities']}")
```

---

### logsim.schema_versioner

Track schema evolution over time.

#### SchemaVersioner

```python
class SchemaVersioner:
    def __init__(self, storage_dir: Path = Path("schema_versions"))
    def register_schema(self, source_name: str, template: str, 
                       fields: List[str], field_types: Dict[str, str],
                       sample_count: int) -> int
    def get_version(self, source_name: str, version: int) -> SchemaVersion
    def get_current_version(self, source_name: str) -> SchemaVersion
    def compare_versions(self, source_name: str, v1: int, v2: int) -> Dict
    def get_compatibility_matrix(self, source_name: str) -> Dict[str, Dict[str, str]]
```

**Methods:**

- `register_schema()`: Register new schema version, returns version number
- `get_version()`: Get specific schema version
- `compare_versions()`: Compare two versions, returns compatibility info
- `get_compatibility_matrix()`: Get full compatibility matrix

**Example:**

```python
from logsim.schema_versioner import SchemaVersioner

versioner = SchemaVersioner()

# Register schema
v1 = versioner.register_schema(
    source_name='Apache',
    template='[TIMESTAMP] [SEVERITY] MESSAGE',
    fields=['timestamp', 'severity', 'message'],
    field_types={'timestamp': 'TIMESTAMP', 'severity': 'SEVERITY', 'message': 'MESSAGE'},
    sample_count=1000
)

# Compare versions
comparison = versioner.compare_versions('Apache', 1, 2)
print(f"Added: {comparison['added_fields']}")
print(f"Removed: {comparison['removed_fields']}")
print(f"Compatible: {comparison['compatible']}")
```

---

### logsim.evaluator

Evaluate schema extraction accuracy.

#### SchemaEvaluator

```python
class SchemaEvaluator:
    def __init__(self)
    def load_ground_truth(self, filepath: Path)
    def load_extracted_schemas(self, filepath: Path)
    def evaluate_all(self) -> EvaluationMetrics
```

**EvaluationMetrics fields:**
- `precision`: Precision score (0.0-1.0)
- `recall`: Recall score (0.0-1.0)
- `f1_score`: F1 score (0.0-1.0)
- `true_positives`, `false_positives`, `false_negatives`: Counts

**Example:**

```python
from logsim.evaluator import SchemaEvaluator

evaluator = SchemaEvaluator()
evaluator.load_ground_truth('ground_truth.json')
evaluator.load_extracted_schemas('extracted.json')

metrics = evaluator.evaluate_all()
print(f"Precision: {metrics.precision*100:.2f}%")
print(f"Recall: {metrics.recall*100:.2f}%")
print(f"F1-Score: {metrics.f1_score*100:.2f}%")
```

---

### logsim.gorilla_compression

Optimize timestamp compression using Gorilla algorithm.

#### GorillaTimestampCompressor

```python
class GorillaTimestampCompressor:
    def __init__(self)
    def compress(self, timestamps: List[int]) -> bytes
    def decompress(self, compressed: bytes, count: int) -> List[int]
```

**Features:**
- 63x compression on regular intervals
- 7.8x compression on variable intervals
- 1-8 bits per timestamp vs 64 bits uncompressed

**Example:**

```python
from logsim.gorilla_compression import GorillaTimestampCompressor

compressor = GorillaTimestampCompressor()

# Unix timestamps
timestamps = [1700000000 + i for i in range(10000)]

compressed = compressor.compress(timestamps)
decompressed = compressor.decompress(compressed, len(timestamps))

ratio = len(timestamps) * 8 / len(compressed)
print(f"Compression: {ratio:.1f}x")
```

---

## Command-Line Tools

### bin/benchmark.py

Run compression and query benchmarks.

```bash
python bin/benchmark.py --dataset DATASET --sample-size SIZE [--output FILE]
```

**Options:**
- `--dataset`: Dataset name (Apache, HealthApp, Zookeeper, OpenStack, Proxifier, all)
- `--sample-size`: Number of logs to test (default: 5000)
- `--output`: Output JSON file (default: benchmarks.json)

**Output:**
- Compression ratios vs gzip
- Query performance metrics
- JSON results file

---

### bin/view_benchmarks.py

Visualize benchmark results.

```bash
python bin/view_benchmarks.py [RESULTS_FILE]
```

Displays formatted tables with compression ratios, query speeds, and comparisons.

---

### examples/demo_extraction.py

Extract schemas from datasets.

```bash
python examples/demo_extraction.py --dataset DATASET --sample-size SIZE
```

**Options:**
- `--dataset`: Dataset name or 'all'
- `--sample-size`: Number of logs to process (default: 5000)

**Output:**
- Extracted templates
- Coverage statistics
- JSON results in `annotations/` directory

---

## Data Structures

### Template

```python
@dataclass
class Template:
    template_id: str
    pattern: str
    fields: List[str]
    field_types: Dict[str, str]
    count: int
    examples: List[str]
```

### CompressedLog

```python
@dataclass
class CompressedLog:
    templates: List[str]
    dictionaries: Dict[str, List[str]]
    indices: List[Dict[str, int]]
    timestamp_deltas: List[int]
    metadata: Dict
```

### QueryResult

```python
@dataclass
class QueryResult:
    matched_count: int
    scanned_count: int
    execution_time: float
    logs: List[str]
```

---

## Constants

### Semantic Types

```python
SEMANTIC_TYPES = [
    'TIMESTAMP',
    'IP_ADDRESS',
    'PORT',
    'URL',
    'EMAIL',
    'USER_ID',
    'PROCESS_ID',
    'ERROR_CODE',
    'STATUS',
    'SEVERITY',
    'HOST',
    'PATH',
    'METRIC',
    'MESSAGE'
]
```

### Severity Levels

```python
SEVERITY_LEVELS = ['ERROR', 'WARN', 'INFO', 'DEBUG', 'TRACE', 'FATAL', 'CRITICAL']
```
