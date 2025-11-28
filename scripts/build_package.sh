#!/bin/bash
set -e

echo "🔨 Building logpress Python package..."
echo ""

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf build/ dist/ *.egg-info logpress.egg-info

# Install/prepare build tools
echo "📦 Installing build tools..."
# Use $PYTHON if provided, otherwise try to pick the active virtual env's python
PYTHON=${PYTHON:-python3}
# If there's an active python virtualenv in the environment, prefer it
if [ -n "${VIRTUAL_ENV:-}" ] && [ -x "${VIRTUAL_ENV}/bin/python" ]; then
	PYTHON="$VIRTUAL_ENV/bin/python"
fi

echo "Using Python: $PYTHON"

"$PYTHON" -m pip install --upgrade pip setuptools wheel
"$PYTHON" -m pip install --upgrade build twine

# Build package
echo "🏗️  Building package..."
"$PYTHON" -m build

# Check package
echo "✅ Checking package..."
"$PYTHON" -m twine check dist/*

echo ""
echo "✅ Package built successfully!"
echo "📦 Packages created:"
ls -lh dist/

echo ""
echo "📋 Package contents:"
tar -tzf dist/logpress-0.1.0.tar.gz | head -20

echo ""
echo "🎉 Build complete!"
