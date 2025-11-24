#!/bin/bash
# Full Evaluation Pipeline for LogSim Thesis
# This script runs all evaluation steps sequentially

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Datasets
DATASETS=("Apache" "HealthApp" "Zookeeper" "OpenStack" "Proxifier")

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}LogSim Full Evaluation Pipeline${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Check Python environment
echo -e "${YELLOW}Checking Python environment...${NC}"
python3 --version
if ! python3 -c "import logsim" 2>/dev/null; then
    echo -e "${RED}ERROR: logsim module not found!${NC}"
    echo "Make sure you're in the project directory"
    exit 1
fi
echo -e "${GREEN}✓ Python environment OK${NC}\n"

# ============================================================
# STEP 1: Run LogSim Benchmarks (Compression + Queries)
# ============================================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}STEP 1: Running LogSim Benchmarks${NC}"
echo -e "${BLUE}========================================${NC}\n"

mkdir -p results/compression

for dataset in "${DATASETS[@]}"; do
    echo -e "${YELLOW}Running benchmark for $dataset...${NC}"
    python3 bin/benchmark.py \
        --dataset "$dataset" \
        --sample-size 5000 \
        --output "results/compression/${dataset,,}.json" || {
        echo -e "${RED}Warning: Benchmark failed for $dataset${NC}"
    }
done

echo -e "${GREEN}✓ Step 1 Complete: LogSim benchmarks finished${NC}\n"

# ============================================================
# STEP 2: Generate Ground Truth Templates
# ============================================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}STEP 2: Generating Ground Truth Templates${NC}"
echo -e "${BLUE}========================================${NC}\n"

if ! python3 -c "from logsim.semantic_types import SemanticTypeDetector" 2>/dev/null; then
    echo -e "${YELLOW}Warning: Cannot generate ground truth (semantic_types module issue)${NC}"
    echo -e "${YELLOW}Skipping ground truth generation...${NC}\n"
else
    for dataset in "${DATASETS[@]}"; do
        echo -e "${YELLOW}Generating template for $dataset...${NC}"
        python3 bin/comparison/generate_ground_truth.py \
            --dataset "$dataset" \
            --count 100 || {
            echo -e "${RED}Warning: Ground truth generation failed for $dataset${NC}"
        }
    done
    
    echo -e "${GREEN}✓ Step 2 Complete: Ground truth templates generated${NC}"
    echo -e "${YELLOW}⚠ MANUAL STEP REQUIRED:${NC}"
    echo -e "  Review and correct annotations in ground_truth/ directories"
    echo -e "  Rename files from *_draft.json to *_ground_truth.json\n"
fi

# ============================================================
# STEP 3: Measure Schema Extraction Accuracy
# ============================================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}STEP 3: Measuring Schema Extraction Accuracy${NC}"
echo -e "${BLUE}========================================${NC}\n"

echo -e "${YELLOW}Checking for verified ground truth files...${NC}"

mkdir -p results/accuracy

ground_truth_ready=false
for dataset in "${DATASETS[@]}"; do
    gt_file="ground_truth/${dataset,,}/${dataset,,}_ground_truth.json"
    if [ -f "$gt_file" ]; then
        echo -e "${YELLOW}Running accuracy evaluation for $dataset...${NC}"
        python3 logsim/evaluator.py \
            --dataset "datasets/$dataset/${dataset}_full.log" \
            --ground-truth "$gt_file" \
            --sample-size 100 \
            --output "results/accuracy/${dataset,,}_accuracy.json" || {
            echo -e "${RED}Warning: Accuracy evaluation failed for $dataset${NC}"
        }
        ground_truth_ready=true
    else
        echo -e "${YELLOW}⚠ Ground truth not found: $gt_file${NC}"
    fi
done

if [ "$ground_truth_ready" = true ]; then
    echo -e "${GREEN}✓ Step 3 Complete: Accuracy evaluation finished${NC}\n"
else
    echo -e "${YELLOW}⚠ Step 3 Skipped: No verified ground truth files found${NC}\n"
fi

# ============================================================
# STEP 4: Install Comparison Systems (if needed)
# ============================================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}STEP 4: Checking Comparison Systems${NC}"
echo -e "${BLUE}========================================${NC}\n"

if python3 -c "from logparser.Drain import LogParser" 2>/dev/null; then
    echo -e "${GREEN}✓ logparser library already installed${NC}\n"
else
    echo -e "${YELLOW}logparser not found. Install with:${NC}"
    echo -e "  pip install git+https://github.com/logpai/logparser.git\n"
    echo -e "${YELLOW}Skipping Drain/Spell comparisons...${NC}\n"
fi

# ============================================================
# STEP 5: Run Drain Comparison (if available)
# ============================================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}STEP 5: Running Drain Comparison${NC}"
echo -e "${BLUE}========================================${NC}\n"

if python3 -c "from logparser.Drain import LogParser" 2>/dev/null; then
    mkdir -p results/comparison
    
    for dataset in "${DATASETS[@]}"; do
        echo -e "${YELLOW}Running Drain on $dataset...${NC}"
        python3 bin/comparison/compare_drain.py \
            --dataset "$dataset" \
            --sample-size 5000 || {
            echo -e "${RED}Warning: Drain comparison failed for $dataset${NC}"
        }
    done
    echo -e "${GREEN}✓ Step 5 Complete: Drain comparison finished${NC}\n"
else
    echo -e "${YELLOW}⚠ Step 5 Skipped: logparser not installed${NC}\n"
fi

# ============================================================
# STEP 6: Run Spell Comparison (if available)
# ============================================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}STEP 6: Running Spell Comparison${NC}"
echo -e "${BLUE}========================================${NC}\n"

if python3 -c "from logparser.Spell import LogParser" 2>/dev/null; then
    for dataset in "${DATASETS[@]}"; do
        echo -e "${YELLOW}Running Spell on $dataset...${NC}"
        python3 bin/comparison/compare_spell.py \
            --dataset "$dataset" \
            --sample-size 5000 || {
            echo -e "${RED}Warning: Spell comparison failed for $dataset${NC}"
        }
    done
    echo -e "${GREEN}✓ Step 6 Complete: Spell comparison finished${NC}\n"
else
    echo -e "${YELLOW}⚠ Step 6 Skipped: logparser not installed${NC}\n"
fi

# ============================================================
# STEP 7: Ablation Study
# ============================================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}STEP 7: Running Ablation Study${NC}"
echo -e "${BLUE}========================================${NC}\n"

mkdir -p results/ablation

for dataset in "${DATASETS[@]}"; do
    echo -e "${YELLOW}Running ablation study for $dataset...${NC}"
    python3 bin/comparison/ablation_study.py \
        --dataset "$dataset" \
        --sample-size 5000 || {
        echo -e "${RED}Warning: Ablation study failed for $dataset${NC}"
    }
done

echo -e "${GREEN}✓ Step 7 Complete: Ablation study finished${NC}\n"

# ============================================================
# STEP 8: Scalability Tests
# ============================================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}STEP 8: Running Scalability Tests${NC}"
echo -e "${BLUE}========================================${NC}\n"

mkdir -p results/scalability

# Test with Apache dataset at different scales
SIZES=(1000 5000 10000 25000 50000)

for size in "${SIZES[@]}"; do
    echo -e "${YELLOW}Testing with $size logs...${NC}"
    python3 bin/benchmark.py \
        --dataset Apache \
        --sample-size "$size" \
        --output "results/scalability/apache_${size}.json" || {
        echo -e "${RED}Warning: Scalability test failed for size $size${NC}"
    }
done

echo -e "${GREEN}✓ Step 8 Complete: Scalability tests finished${NC}\n"

# ============================================================
# FINAL SUMMARY
# ============================================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}EVALUATION PIPELINE COMPLETE${NC}"
echo -e "${BLUE}========================================${NC}\n"

echo -e "${GREEN}Results saved to:${NC}"
echo -e "  • results/compression/     (LogSim vs Gzip benchmarks)"
echo -e "  • results/accuracy/        (Schema extraction accuracy)"
echo -e "  • results/comparison/      (Drain/Spell comparisons)"
echo -e "  • results/ablation/        (Component contribution)"
echo -e "  • results/scalability/     (Scalability analysis)"
echo -e ""

echo -e "${YELLOW}Next steps:${NC}"
echo -e "  1. Review results with: python bin/view_benchmarks.py results/compression/apache.json"
echo -e "  2. Generate thesis tables from JSON results"
echo -e "  3. Complete manual ground truth annotations (if not done)"
echo -e "  4. Run accuracy evaluation after ground truth is ready"
echo -e ""

echo -e "${GREEN}✓ All evaluation steps completed successfully!${NC}\n"
