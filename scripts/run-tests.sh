#!/bin/bash
# Run complete test suite for logpress

set -e

echo "🧪 Running logpress Test Suite"
echo "============================="

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo -e "${RED}Error: Virtual environment not found${NC}"
    exit 1
fi

# Install test dependencies
echo -e "${YELLOW}Installing test dependencies...${NC}"
pip install -q pytest pytest-cov pytest-benchmark pytest-mock

# Run unit tests
echo ""
echo -e "${YELLOW}Running unit tests...${NC}"
python -m pytest logpress/tests/unit/ -v --tb=short

# Run integration tests
echo ""
echo -e "${YELLOW}Running integration tests...${NC}"
python -m pytest logpress/tests/integration/ -v --tb=short

# Run end-to-end tests
echo ""
echo -e "${YELLOW}Running end-to-end tests...${NC}"
python -m pytest logpress/tests/e2e/ -v --tb=short

# Run with coverage
echo ""
echo -e "${YELLOW}Generating coverage report...${NC}"
python -m pytest logpress/tests/ \
    --cov=logpress \
    --cov-report=html \
    --cov-report=term-missing \
    --tb=short

# Run benchmarks (optional)
if [ "$1" == "--benchmark" ]; then
    echo ""
    echo -e "${YELLOW}Running performance benchmarks...${NC}"
    python -m pytest logpress/tests/performance/ \
        --benchmark-only \
        --benchmark-autosave
fi

echo ""
echo -e "${GREEN}✅ Test suite completed!${NC}"
echo -e "Coverage report: file://$(pwd)/htmlcov/index.html"
