#!/bin/bash
# End-to-end demo: Extract schemas → Compress → Query

echo "╔════════════════════════════════════════════════════════════╗"
echo "║   LogSim: End-to-End Demo (Extract → Compress → Query)    ║"
echo "╚════════════════════════════════════════════════════════════╝"

# Step 1: Extract schemas
echo ""
echo "📊 [1/3] Extracting schemas from Apache logs (1,000 samples)..."
python3 demo_extraction.py --dataset Apache --sample-size 1000

# Step 2: Compress logs
echo ""
echo "📦 [2/3] Compressing with semantic awareness..."
python3 -m logsim.compressor --input datasets/Apache/Apache_full.log --output compressed/apache_demo.lsc --sample-size 1000 --measure

# Step 3: Query compressed data
echo ""
echo "⚡ [3/3] Querying compressed data..."
echo ""
echo "Query 1: Get statistics"
python3 -m logsim.query_engine --compressed compressed/apache_demo.lsc --query stats

echo ""
echo "Query 2: Filter by severity=ERROR"
python3 -m logsim.query_engine --compressed compressed/apache_demo.lsc --query severity --value ERROR

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  ✅ Demo complete! Schemas extracted, compressed, queried  ║"
echo "╚════════════════════════════════════════════════════════════╝"
