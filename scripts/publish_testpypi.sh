#!/bin/bash
set -e

echo "📤 Publishing logpress to TestPyPI..."
echo ""
echo "⚠️  This will publish to TEST PyPI (test.pypi.org)"
echo ""

# Build package
echo "🔨 Building package..."
bash scripts/build_package.sh

# Upload to TestPyPI
echo ""
echo "📤 Uploading to TestPyPI..."
twine upload --repository testpypi dist/* --config-file .pypirc

echo ""
echo "✅ Published to TestPyPI!"
echo "🔗 View at: https://test.pypi.org/project/logpress/"
echo ""
echo "📦 Test installation with:"
echo "   pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ logpress"
echo ""
echo "   # The --extra-index-url is needed for dependencies"
