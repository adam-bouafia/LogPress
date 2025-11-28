# Scripts Directory

Automation scripts for logpress testing, deployment, and interactive usage.

## Structure

```
scripts/
├── logpress-interactive.sh       # Bash interactive menu (450+ lines)
├── run-tests.sh                # Test suite runner
├── run-pre-production-tests.sh # Pre-deployment validation
└── migrate_to_mcp.sh          # MCP architecture migration (historical)
```

## Scripts Overview

### logpress-interactive.sh

**Bash interactive CLI** with colored menus and dataset auto-discovery.

**Features**:
- 🔍 Auto-discovers datasets from `data/datasets/`
- 📊 Shows dataset info (lines, size)
- 🗜️ Multi-select compression workflow
- 🔎 Query interface
- 📈 Run full evaluation
- 📄 View results
- ⚙️ Settings menu

**Usage**:
```bash
# Make executable (if needed)
chmod +x scripts/logpress-interactive.sh

# Run directly
bash scripts/logpress-interactive.sh

# Or from Docker
docker-compose -f deployment/docker-compose.yml run --rm logpress-interactive-bash
```

**Menu Structure**:
```
╔════════════════════════════════════════════════╗
║         logpress Interactive CLI                 ║
║    Semantic Log Compression System             ║
╚════════════════════════════════════════════════╝

Datasets found: 5
  1. Apache        - 52,437 lines (4.76 MB)
  2. HealthApp     - 212,005 lines (19.21 MB)
  3. Zookeeper     - 74,380 lines (9.85 MB)
  4. OpenStack     - 137,236 lines (28.35 MB)
  5. Proxifier     - 21,329 lines (2.01 MB)

Options:
  [1] Compress Dataset(s)
  [2] Query Compressed File
  [3] Run Full Evaluation
  [4] View Results
  [5] Settings
  [6] Help
  [7] Exit

Choose an option:
```

**Functions**:
- `scan_datasets()` - Discovers log files
- `show_main_menu()` - Displays menu
- `compress_datasets()` - Compression workflow
- `query_files()` - Query interface
- `run_evaluation()` - Runs evaluation script
- `view_results()` - Shows recent results
- `show_settings()` - Configuration menu

### run-tests.sh

**Comprehensive test runner** with coverage reporting.

**Features**:
- Runs all test categories (unit, integration, e2e, performance)
- Generates HTML coverage report
- Colored output with test counts
- Benchmark summaries

**Usage**:
```bash
# Run all tests with coverage
bash scripts/run-tests.sh

# View HTML report
firefox htmlcov/index.html
```

**Output**:
```
╔════════════════════════════════════════════════╗
║          logpress Test Suite Runner              ║
╚════════════════════════════════════════════════╝

Setting up virtual environment...
✓ Virtual environment ready

Installing test dependencies...
✓ Dependencies installed

Running test suite...
========================= test session starts ==========================
collected 25 items

logpress/tests/unit/test_dataset_discovery.py ............ [ 36%]
logpress/tests/integration/test_compression_workflow.py .... [ 52%]
logpress/tests/integration/test_interactive_cli.py .... [ 68%]
logpress/tests/e2e/test_workflows.py ... [ 80%]
logpress/tests/performance/test_benchmarks.py ..... [100%]

========================== 25 passed in 4.48s ==========================

Coverage: 42%

HTML coverage report: htmlcov/index.html
```

**Script Content**:
```bash
#!/bin/bash
set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

# Activate venv
source venv/bin/activate

# Install dependencies
pip install -q pytest pytest-cov pytest-benchmark pytest-mock

# Run tests with coverage
python -m pytest logpress/tests/ \
  --cov=logpress \
  --cov-report=term-missing \
  --cov-report=html \
  -v

echo -e "${GREEN}✅ All tests passed!${NC}"
echo "Coverage report: htmlcov/index.html"
```

### run-pre-production-tests.sh

**Pre-deployment validation** - Ensures system is production-ready.

**Tests**:
1. ✅ Dataset discovery
2. ✅ Compression on sample data
3. ✅ CLI commands work
4. ✅ Docker build succeeds
5. ✅ Interactive CLI initializes
6. ✅ Unit tests pass

**Usage**:
```bash
# Run validation
bash scripts/run-pre-production-tests.sh
```

**Output**:
```
🚀 Running Pre-Production Validation
=====================================

1️⃣  Testing dataset discovery...
✓ Found 5 datasets
  - Apache: 52,437 lines, 4.76 MB
  - HealthApp: 212,005 lines, 19.21 MB
  - Zookeeper: 74,380 lines, 9.85 MB
  - OpenStack: 137,236 lines, 28.35 MB
  - Proxifier: 21,329 lines, 2.01 MB

2️⃣  Testing compression on sample data...
✓ Compressed 100 logs into 3 templates
  Compression ratio: 14.2x

3️⃣  Testing CLI commands...
✓ CLI help works
✓ Compress command registered
✓ Query command registered

4️⃣  Testing Docker build...
✓ Docker image builds successfully

5️⃣  Testing interactive CLI initialization...
✓ Interactive CLI initialized with 5 datasets

6️⃣  Running quick test suite...
.........

✅ Pre-production validation complete!

Ready for production deployment:
  - Dataset discovery: Working
  - Compression: Working
  - CLI commands: Working
  - Docker: Working
  - Unit tests: Passing
```

**Script Structure**:
```bash
#!/bin/bash
set -e

echo "🚀 Running Pre-Production Validation"
echo "====================================="

# 1. Test dataset discovery
echo "1️⃣  Testing dataset discovery..."
python -c "
from logpress.cli.interactive import InteractiveCLI
cli = InteractiveCLI()
datasets = cli.scan_datasets()
print(f'✓ Found {len(datasets)} datasets')
"

# 2. Test compression
echo "2️⃣  Testing compression on sample data..."
python -c "
from logpress.services.compressor import SemanticCompressor
logs = ['[2005-06-09 06:07:04] [info] Test'] * 100
compressor = SemanticCompressor(min_support=2)
compressed_log, stats = compressor.compress(logs, verbose=False)
print(f'✓ Compressed {stats.log_count} logs')
"

# 3. Test CLI commands
echo "3️⃣  Testing CLI commands..."
python -m logpress --help > /dev/null && echo "✓ CLI help works"

# 4. Test Docker build
echo "4️⃣  Testing Docker build..."
if command -v docker &> /dev/null; then
    docker-compose -f deployment/docker-compose.yml build logpress-cli > /dev/null 2>&1
    echo "✓ Docker image builds successfully"
fi

# 5. Test interactive CLI
echo "5️⃣  Testing interactive CLI initialization..."
timeout 5 python -c "
from logpress.cli.interactive import InteractiveCLI
cli = InteractiveCLI()
cli.datasets = cli.scan_datasets()
print(f'✓ Interactive CLI initialized')
" 2>/dev/null

# 6. Run quick tests
echo "6️⃣  Running quick test suite..."
python -m pytest logpress/tests/unit/ -q --tb=line

echo "✅ Pre-production validation complete!"
```

### migrate_to_mcp.sh (Historical)

**MCP architecture migration script** - Used during project reorganization.

**What it did**:
- Created MCP directory structure
- Moved files to appropriate layers (models, protocols, context, services)
- Updated import statements
- Generated migration documentation

**Note**: This script was used once during the project restructuring and is kept for reference.

## Creating New Scripts

### Template for Automation Scripts

```bash
#!/bin/bash
# Script description here

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'  # No color

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Functions
function print_header() {
    echo -e "${GREEN}╔════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║           $1${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════╝${NC}"
}

function print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

function print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Main script logpress
print_header "Script Name"

# Do work...
print_success "Task completed"
```

### Make Script Executable

```bash
# Make executable
chmod +x scripts/my-new-script.sh

# Test execution
bash scripts/my-new-script.sh
```

## Usage Examples

### Daily Development Workflow

```bash
# 1. Run tests before committing
bash scripts/run-tests.sh

# 2. Interactive exploration
bash scripts/logpress-interactive.sh

# 3. Pre-commit validation
bash scripts/run-pre-production-tests.sh
```

### Production Deployment

```bash
# 1. Run full validation
bash scripts/run-pre-production-tests.sh

# 2. Build Docker image
cd deployment
docker-compose build

# 3. Deploy to production
docker-compose up -d
```

### Continuous Integration

```bash
# In CI pipeline (e.g., GitHub Actions)
- name: Run tests
  run: bash scripts/run-tests.sh

- name: Validate deployment
  run: bash scripts/run-pre-production-tests.sh
```

## Integration with Docker

All scripts are available inside Docker containers:

```bash
# Run tests in container
docker-compose -f deployment/docker-compose.yml run --rm logpress-cli \
  bash /app/scripts/run-tests.sh

# Run interactive bash menu
docker-compose -f deployment/docker-compose.yml run --rm logpress-interactive-bash

# Run validation in container
docker-compose -f deployment/docker-compose.yml run --rm logpress-cli \
  bash /app/scripts/run-pre-production-tests.sh
```

## Troubleshooting

### Script Not Executable

```bash
# Add execute permission
chmod +x scripts/script-name.sh

# Verify permissions
ls -l scripts/script-name.sh
```

### Python Module Not Found

```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Docker Command Not Found

```bash
# Install Docker
# Ubuntu/Debian
sudo apt-get install docker.io docker-compose

# Or use the script without Docker tests
bash scripts/run-pre-production-tests.sh  # Skips Docker tests if not available
```

## Best Practices

1. **Always use `set -e`** - Exit on first error
2. **Add colored output** - Improves readability
3. **Include help text** - Document usage
4. **Test in isolation** - Don't depend on specific environment
5. **Make idempotent** - Can run multiple times safely
6. **Add error handling** - Gracefully handle failures

---

**See parent [README.md](../README.md) for complete project information.**
