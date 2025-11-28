#!/bin/bash
set -euo pipefail

echo "🧪 Testing logpress package installation..."
echo ""

# Create test environment
echo "🔧 Creating test environment..."
rm -rf test_env

# Prefer python3 but allow 'python' as a fallback. The environment may not have 'python' symlink.
if command -v python3 >/dev/null 2>&1; then
	PYTHON=python3
elif command -v python >/dev/null 2>&1; then
	PYTHON=python
else
	echo "⚠️  No Python interpreter found. Please install Python 3 and the venv module."
	echo "   On Debian/Ubuntu: sudo apt install python3 python3-venv -y"
	exit 1
fi

"$PYTHON" -m venv test_env
source test_env/bin/activate

echo "📦 Installing package from wheel..."
# If there is no wheel, print a helpful message
if [ -z "$(ls dist/*.whl 2>/dev/null || true)" ]; then
	echo "⚠️  No wheel found in dist/. Did you run 'python -m build'?"
else
	pip install dist/*.whl
fi

echo "📦 Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "✅ Testing imports..."
python -c "
from logpress import SemanticCompressor, QueryEngine
from logpress.models import Token, LogTemplate, CompressedLog
print('✓ All imports successful!')
"

echo ""
echo "✅ Testing CLI..."
python -m logpress --help

echo ""
echo "✅ Testing version..."
python -c "import logpress; print(f'logpress version: {logpress.__version__}')"

echo ""
echo "🧹 Cleaning up..."
deactivate
rm -rf test_env

echo ""
echo "✅ Package installation test passed!"
