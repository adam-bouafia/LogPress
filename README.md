# LogSim: Semantic Log Compression with Automatic Schema Extraction

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

LogSim is a high-performance log compression system that automatically extracts schemas from unstructured logs and applies semantic-aware compression techniques. It achieves **11.47x average compression** while maintaining the ability to query specific fields without full decompression.

## Features

- **Automatic Schema Extraction**: No configuration required - discovers log templates automatically
- **Semantic-Aware Compression**: Different compression strategies for timestamps, IPs, severity levels, and messages
- **Queryable Format**: Columnar storage enables selective field access without full decompression
- **High Performance**: Processes 1.35-2.82 MB/s with 11.47x compression ratio
- **Lossless**: Perfect reconstruction of original logs

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/adam-bouafia/LogSim.git
cd LogSim

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Basic Usage

**Compress logs:**

```python
from logsim.compressor import SemanticCompressor
from pathlib import Path

# Load your log file
with open('your_logs.log', 'r') as f:
    logs = [line.strip() for line in f if line.strip()]

# Compress
compressor = SemanticCompressor(min_support=3)
compressed, stats = compressor.compress(logs, verbose=True)

# Save compressed data
compressor.save(Path('compressed_logs.lsc'))

print(f"Compression ratio: {stats.compression_ratio:.2f}x")
print(f"Original: {stats.original_size/1024:.2f} KB")
print(f"Compressed: {stats.compressed_size/1024:.2f} KB")
```

**Decompress logs:**

```python
from logsim.compressor import SemanticCompressor

# Load compressed data
compressor = SemanticCompressor()
compressed = compressor.load(Path('compressed_logs.lsc'))

# Decompress
original_logs = compressor.decompress(compressed)
```

**Query without full decompression:**

```python
from logsim.query_engine import QueryEngine
from pathlib import Path

# Query specific fields
engine = QueryEngine(Path('compressed_logs.lsc'))

# Get all ERROR severity logs
errors = engine.query(severity='ERROR')

# Get logs in time range
recent = engine.query(
    timestamp_start='2025-01-01 00:00:00',
    timestamp_end='2025-01-31 23:59:59'
)

# Combined filters
critical = engine.query(severity='ERROR', contains='database')
```

## Benchmarks

Performance on real-world log datasets (360K total logs, 36.52 MB):

| Dataset | Logs | Original | Compressed | Ratio | vs gzip-9 | Speed |
|---------|------|----------|------------|-------|-----------|-------|
| Apache | 51,978 | 4.75 MB | 584 KB | **8.32x** | 39.2% | 1.40 MB/s |
| HealthApp | 212,394 | 19.53 MB | 1.87 MB | **10.69x** | 97.9% | 2.82 MB/s |
| Proxifier | 21,320 | 2.40 MB | 197 KB | **12.49x** | 79.6% | 1.35 MB/s |
| Zookeeper | 74,273 | 9.84 MB | 610 KB | **16.53x** | 63.9% | 1.35 MB/s |
| **Average** | **360K** | **36.52 MB** | **3.18 MB** | **11.47x** | **79.9%** | **1.73 MB/s** |

**Key Metrics:**
- Average compression ratio: **11.47x** (79.9% of gzip-9 efficiency)
- Compression speed: **1.73 MB/s** average
- Template extraction: **77 templates** across all datasets
- Match rate: **100%** (all logs successfully matched)

## How It Works

LogSim uses a 6-stage pipeline:

### 1. Tokenization
FSM-based tokenizer with context-aware boundary detection (`logsim/tokenizer.py`)

### 2. Template Extraction
Custom log alignment algorithm that discovers patterns by position-by-position comparison (`logsim/template_generator.py`)

### 3. Semantic Classification
Pattern-based field type detection: TIMESTAMP, SEVERITY, IP_ADDRESS, HOST, PROCESS_ID, MESSAGE (`logsim/semantic_types.py`)

### 4. Columnar Encoding
Different strategies per field type:
- **Delta Encoding**: Timestamps (store differences)
- **Zigzag Encoding**: Signed integers
- **Varint Encoding**: Protocol Buffer style compression
- **Dictionary Encoding**: Low-cardinality fields (severity, status)
- **RLE v2**: Pattern detection for repeated sequences
- **Token Pool**: Global template deduplication

### 5. Binary Serialization
- **MessagePack**: Efficient binary format
- **Zstandard Level 15**: Final compression pass

### 6. Query Engine
Selective decompression with columnar field access (`logsim/query_engine.py`)

## Evaluation

Run comprehensive evaluation on all datasets:

```bash
python run_full_evaluation.py
```

Results will be saved to `results/full_evaluation_results.md`.

## Project Structure

```
LogSim/
├── logsim/                 # Core implementation
│   ├── compressor.py       # Main compression logic
│   ├── tokenizer.py        # FSM-based tokenization
│   ├── template_generator.py  # Schema extraction
│   ├── semantic_types.py   # Field type detection
│   ├── query_engine.py     # Selective decompression
│   ├── varint.py           # Variable-length encoding
│   ├── bwt.py              # Burrows-Wheeler Transform
│   └── gorilla_compression.py  # Time-series compression
├── datasets/               # Sample log datasets
│   ├── Apache/
│   ├── HealthApp/
│   ├── Proxifier/
│   └── Zookeeper/
├── ground_truth/           # Manual annotations for evaluation
├── results/                # Evaluation results
├── docs/                   # Additional documentation
│   ├── API.md              # API reference
│   └── SETUP.md            # Detailed setup guide
├── run_full_evaluation.py  # Benchmark script
└── requirements.txt        # Python dependencies
```

## Supported Log Formats

LogSim automatically handles diverse log formats:

- **Apache**: `[Thu Jun 09 06:07:04 2005] [notice] LDAP: Built with OpenLDAP`
- **HealthApp**: `20171223-22:15:29:606|Step_LSC|30002312|onStandStepChanged 3579`
- **Zookeeper**: `2015-07-29 17:41:41,536 - INFO [main:QuorumPeerConfig@101] - Reading configuration`
- **Proxifier**: `[10.30 16:49:06] chrome.exe - proxy.cse.cuhk.edu.hk:5070 close, 0 bytes`

## Requirements

- Python 3.8+
- Dependencies listed in `requirements.txt`:
  - `msgpack` - Binary serialization
  - `zstandard` - Zstandard compression
  - `regex` - Advanced pattern matching
  - `python-dateutil` - Timestamp parsing
  - `numpy` - Numerical operations

## Documentation

- [API Reference](docs/API.md) - Detailed API documentation
- [Setup Guide](docs/SETUP.md) - Installation and configuration
- [Evaluation Results](results/full_evaluation_results.md) - Detailed benchmark data

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Citation

If you use LogSim in your research, please cite:

```bibtex
@software{logsim2025,
  author = {Adam Bouafia},
  title = {LogSim: Semantic Log Compression with Automatic Schema Extraction},
  year = {2025},
  url = {https://github.com/adam-bouafia/LogSim}
}
```

## Acknowledgments

This project implements techniques inspired by research in log parsing, columnar compression, and semantic preprocessing. See the related work section in our documentation for detailed references.

## Contact

- Author: Adam Bouafia
- GitHub: [@adam-bouafia](https://github.com/adam-bouafia)
- Issues: [GitHub Issues](https://github.com/adam-bouafia/LogSim/issues)
