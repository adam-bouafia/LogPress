# logpress Core Package

This is the main Python package containing all logpress functionality organized in **MCP (Model-Context-Protocol) architecture**.

## Architecture Overview

```
logpress/
├── models/          # Pure data structures (no logpress)
├── protocols/       # Abstract interfaces (contracts)
├── context/        # Business logpress & algorithms
├── services/       # High-level orchestration
├── cli/           # User interfaces
└── tests/         # Test suite
```

## Layer Descriptions

### Models Layer (`models/`)
**Pure data structures** - No business logpress, just dataclasses.

- `Token`: Tokenization output
- `LogTemplate`: Extracted schema template
- `CompressedLog`: Compression output container
- `SemanticFieldType`: Field type enumeration

**Example**:
```python
from logpress.models import Token, LogTemplate

token = Token(value="ERROR", start_pos=10, end_pos=15, token_type="SEVERITY")
template = LogTemplate(
    template_id="t1",
    pattern="[TIMESTAMP] [SEVERITY] [MESSAGE]",
    fields=[...],
    log_count=100
)
```

### Protocols Layer (`protocols/`)
**Abstract interfaces** - Defines contracts for implementations.

- `TokenizerProtocol`: Log tokenization interface
- `EncoderProtocol`: Compression codec interface
- `CompressorProtocol`: Compression backend interface
- `QueryEngineProtocol`: Query execution interface

**Example**:
```python
from logpress.protocols import EncoderProtocol

class CustomEncoder(EncoderProtocol):
    def encode(self, values: List[Any]) -> bytes:
        # Your encoding logpress
        pass
    
    def decode(self, data: bytes) -> List[Any]:
        # Your decoding logpress
        pass
    
    @property
    def name(self) -> str:
        return "custom"
```

### Context Layer (`context/`)
**Business logpress** - Core algorithms and implementations.

#### Tokenization (`context/tokenization/`)
- `tokenizer.py`: FSM-based log tokenizer
- Handles brackets, delimiters, quoted strings
- 5 token types: BRACKET, DELIMITER, QUOTED, ALPHANUM, SPECIAL

**Usage**:
```python
from logpress.context.tokenization.tokenizer import LogTokenizer

tokenizer = LogTokenizer()
tokens = tokenizer.tokenize("[2005-06-09 06:07:04] [ERROR] Connection failed")
# Returns: [Token(...), Token(...), ...]
```

#### Extraction (`context/extraction/`)
- `template_generator.py`: Log alignment algorithm
- Extracts schemas from multiple log lines
- Identifies constant vs variable positions

**Usage**:
```python
from logpress.context.extraction.template_generator import TemplateGenerator

generator = TemplateGenerator(min_support=3)
templates = generator.extract_schemas(log_lines)
# Returns: {template_id: LogTemplate, ...}
```

#### Classification (`context/classification/`)
- `semantic_types.py`: Pattern-based field recognition
- Detects: TIMESTAMP, IP, SEVERITY, PID, etc.
- Confidence scoring: 0.0-1.0

**Usage**:
```python
from logpress.context.classification.semantic_types import SemanticTypeRecognizer

recognizer = SemanticTypeRecognizer()
field_type, confidence = recognizer.classify("192.168.1.1")
# Returns: ("IP_ADDRESS", 0.95)
```

#### Encoding (`context/encoding/`)
**Compression codecs**:
- `varint.py`: Variable-length integer encoding
- `bwt.py`: Burrows-Wheeler Transform
- `gorilla.py`: Time-series compression

**Usage**:
```python
from logpress.context.encoding.varint import encode_varint, decode_varint

encoded = encode_varint(1234)  # bytes
decoded = decode_varint(encoded)  # 1234
```

### Services Layer (`services/`)
**High-level orchestration** - Combines context modules.

#### SemanticCompressor (`services/compressor.py`)
**6-stage compression pipeline**:
1. Tokenization
2. Template extraction
3. Semantic classification
4. Columnar encoding
5. Serialization (MessagePack)
6. Compression (Zstandard)

**Usage**:
```python
from logpress.services.compressor import SemanticCompressor

compressor = SemanticCompressor(min_support=3)
compressed_log, stats = compressor.compress(log_lines)
compressor.save("output.lsc")
```

#### QueryEngine (`services/query_engine.py`)
**Selective decompression** - Query without full decompression.

**Usage**:
```python
from logpress.services.query_engine import QueryEngine

engine = QueryEngine()
engine.load("compressed.lsc")
results = engine.query_by_severity("ERROR", limit=20)
```

#### SchemaEvaluator (`services/evaluator.py`)
**Accuracy metrics** - Compare against ground truth.

**Usage**:
```python
from logpress.services.evaluator import SchemaEvaluator

evaluator = SchemaEvaluator()
metrics = evaluator.evaluate(
    extracted_schemas=schemas,
    ground_truth="annotations/apache.json"
)
# Returns: {precision: 0.94, recall: 0.92, f1: 0.93}
```

### CLI Layer (`cli/`)
**User interfaces** - Command-line and interactive.

#### Interactive CLI (`cli/interactive.py`)
Rich terminal UI with:
- Auto-discovery of datasets
- Progress bars and tables
- Multi-select dataset compression
- Query builder interface

**Usage**:
```bash
python -m logpress.cli.interactive
```

#### Commands (`cli/commands.py`)
Click-based CLI commands:
- `compress`: Compress log files
- `query`: Query compressed files
- `evaluate`: Run evaluation

**Usage**:
```bash
python -m logpress compress -i input.log -o output.lsc
python -m logpress query -c output.lsc --severity ERROR
```

### Tests Layer (`tests/`)
**Test suite** - 25 tests, 100% passing.

- `unit/`: Component testing (9 tests)
- `integration/`: Workflow testing (8 tests)
- `e2e/`: End-to-end testing (3 tests)
- `performance/`: Benchmarks (5 tests)

**Run tests**:
```bash
python -m pytest logpress/tests/ -v
```

## API Reference

### Quick Import Guide

```python
# Models
from logpress.models import Token, LogTemplate, CompressedLog

# Services (High-level API)
from logpress.services import SemanticCompressor, QueryEngine

# Context (Low-level components)
from logpress.context.tokenization.tokenizer import LogTokenizer
from logpress.context.extraction.template_generator import TemplateGenerator
from logpress.context.classification.semantic_types import SemanticTypeRecognizer

# Protocols (For extensions)
from logpress.protocols import EncoderProtocol, CompressorProtocol
```

### Common Workflows

#### 1. Compress Logs

```python
from logpress.services import SemanticCompressor

# Load logs
with open("input.log", 'r') as f:
    logs = [line.strip() for line in f if line.strip()]

# Compress
compressor = SemanticCompressor(min_support=3)
compressed_log, stats = compressor.compress(logs, verbose=True)

# Save
compressor.save("output.lsc", verbose=True)

# Metrics
print(f"Compression ratio: {stats.compression_ratio:.2f}x")
print(f"Templates extracted: {stats.template_count}")
```

#### 2. Query Compressed Logs

```python
from logpress.services import QueryEngine

# Load compressed file
engine = QueryEngine()
engine.load("output.lsc")

# Count logs
total = engine.count()

# Filter by severity
errors = engine.query_by_severity("ERROR", limit=20)

# Filter by IP
ip_logs = engine.query_by_ip("192.168.1.1", limit=50)
```

#### 3. Evaluate Accuracy

```python
from logpress.services import SchemaEvaluator

evaluator = SchemaEvaluator()
metrics = evaluator.evaluate(
    extracted_schemas=schemas,
    ground_truth_file="annotations/apache.json"
)

print(f"Precision: {metrics['precision']:.2%}")
print(f"Recall: {metrics['recall']:.2%}")
print(f"F1-Score: {metrics['f1']:.2%}")
```

## Extension Points

### Add Custom Encoder

```python
from logpress.protocols import EncoderProtocol
from logpress.services import SemanticCompressor

class MyEncoder(EncoderProtocol):
    def encode(self, values):
        return b"..."  # Your encoding
    
    def decode(self, data):
        return [...]   # Your decoding
    
    @property
    def name(self):
        return "my_encoder"

# Register
compressor = SemanticCompressor()
compressor.encoders['custom_field'] = MyEncoder()
```

### Add Semantic Type Pattern

```python
from logpress.context.classification.semantic_types import SemanticTypeRecognizer

recognizer = SemanticTypeRecognizer()

# Add custom pattern
recognizer.add_pattern(
    name="CUSTOM_ID",
    pattern=r'^CUST-\d{6}$',
    confidence=0.9
)
```

## Performance Guidelines

### Compression
- **Throughput**: 1-2 MB/s (template extraction is bottleneck)
- **Memory**: ~5× input size during processing
- **Optimal min_support**: 3-5 (balance template count vs accuracy)

### Query
- **COUNT(*)**: <0.01ms (metadata only)
- **Filtered queries**: 2-12× faster than full scan
- **Memory**: Loads only required columns

## Testing

```bash
# Run all tests
python -m pytest logpress/tests/ -v

# Run specific layer
python -m pytest logpress/tests/unit/ -v
python -m pytest logpress/tests/integration/ -v

# With coverage
python -m pytest logpress/tests/ --cov=logpress --cov-report=html
```

## Documentation

- [Testing Guide](../documentation/TESTING.md)
- [MCP Architecture](../documentation/MCP_ARCHITECTURE.md)
- [API Reference](../documentation/API.md)

---

**See parent [README.md](../README.md) for project overview and quick start.**
