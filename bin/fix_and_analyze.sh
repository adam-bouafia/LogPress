#!/bin/bash
# Master script to run all diagnostic and fix tools

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "=============================================="
echo "🔍 Running Comprehensive Analysis & Fixes"
echo "=============================================="
echo ""

# Check virtual environment
if [[ ! -d "venv" ]]; then
    echo "❌ Virtual environment not found. Run: python -m venv venv && source venv/bin/activate"
    exit 1
fi

# Activate venv
source venv/bin/activate

echo "✅ Virtual environment activated"
echo ""

# Step 1: Analyze compression performance
echo "=============================================="
echo "📊 Step 1: Analyze Compression Performance"
echo "=============================================="
echo ""

python bin/analysis/analyze_compression.py

echo ""
echo "✅ Compression analysis complete"
echo "   Results: results/analysis/compression_analysis.json"
echo ""

# Step 2: Run fixed Drain comparison
echo "=============================================="
echo "📊 Step 2: Run Fixed Drain Comparison"
echo "=============================================="
echo ""

python bin/comparison/compare_drain_fixed.py

echo ""
echo "✅ Drain comparison complete"
echo "   Results: results/comparison/drain_vs_logsim_fixed.json"
echo ""

# Step 3: Generate annotation suggestions
echo "=============================================="
echo "📊 Step 3: Generate Annotation Suggestions"
echo "=============================================="
echo ""

echo "Generating batch suggestions for all datasets..."
echo ""

# Run batch mode for each dataset
for dataset in Apache HealthApp Zookeeper Proxifier; do
    echo "Processing $dataset..."
    python bin/annotation/annotation_helper.py <<EOF
2
$(echo "$dataset" | tr 'A-Z' 'a-z' | grep -n "apache\|healthapp\|zookeeper\|proxifier" | cut -d: -f1)
100
EOF
    echo ""
done

echo "✅ Annotation suggestions generated"
echo "   Results: ground_truth/*/annotations_batch.json"
echo ""

# Summary
echo "=============================================="
echo "✅ All Analysis Complete"
echo "=============================================="
echo ""
echo "📊 Generated Results:"
echo "   1. Compression analysis: results/analysis/compression_analysis.json"
echo "   2. Drain comparison: results/comparison/drain_vs_logsim_fixed.json"
echo "   3. Annotation suggestions: ground_truth/*/annotations_batch.json"
echo ""
echo "🔍 Next Steps:"
echo "   1. Review compression_analysis.json for root cause insights"
echo "   2. Compare Drain vs LogSim template extraction accuracy"
echo "   3. Review annotation suggestions and mark verified: true for correct ones"
echo "   4. Run accuracy evaluation with verified ground truth"
echo ""
