# Setup Guide

## Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd "Automatic Schema Extraction from Unstructured System Logs"
```

### 2. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Verify Installation
```bash
python -c "import logsim; print('LogSim version:', logsim.__version__)"
```

## Quick Start

### Schema Extraction
```bash
python examples/demo_extraction.py datasets/Apache/Apache_2k.log
```

### Compression Benchmark
```bash
python bin/benchmark.py datasets/Apache/Apache_2k.log
```

### Full Pipeline Demo
```bash
bash examples/demo_full.sh
```

## Directory Structure

```
.
├── bin/              # Production CLI tools
├── logsim/           # Core library modules
├── examples/         # Demo scripts
├── docs/             # Documentation
├── tests/            # Unit tests
├── datasets/         # Input log files (5 sources, ~497K lines)
├── compressed/       # Output .lsc compressed files
├── annotations/      # Ground truth annotations
├── schema_versions/  # Extracted schema JSON files
└── ground_truth/     # Manual annotations for evaluation
```

## Development

### Running Tests
```bash
pytest tests/ -v
```

### Code Style
```bash
# Install development dependencies
pip install black flake8 mypy

# Format code
black logsim/ bin/ examples/

# Lint
flake8 logsim/ bin/ examples/

# Type checking
mypy logsim/
```

## Troubleshooting

### Import Errors
If you see `ModuleNotFoundError: No module named 'logsim'`, ensure:
1. Virtual environment is activated
2. You're running commands from the repository root
3. Dependencies are installed: `pip install -r requirements.txt`

### Missing Datasets
The `datasets/` folder should contain 5 subdirectories:
- Apache (52K lines)
- HealthApp (212K lines)
- Zookeeper (74K lines)
- OpenStack (137K lines)
- Proxifier (21K lines)

If missing, check the original thesis dataset source.

## Performance Tips

1. **For large logs (>100MB)**: Increase chunk size in compressor
2. **For faster compression**: Use lower semantic analysis depth
3. **For better query performance**: Enable index optimization in QueryEngine

```

## License

MIT License - see LICENSE file for details
