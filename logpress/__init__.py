"""
logpress - Semantic-Driven Log Schema Extraction and Compression

A production-ready system for extracting implicit schemas from unstructured
system logs and compressing them with semantic awareness.

MCP Architecture:
- Models: Pure data structures (Token, LogTemplate, CompressedLog)
- Protocols: Interface contracts (TokenizerProtocol, EncoderProtocol)
- Context: Domain implementations (Tokenization, Extraction, Encoding)
- Services: Application orchestration (Compressor, QueryEngine)
- CLI: User interface (compress, query commands)

Example usage:
    >>> from logpress import SemanticCompressor, QueryEngine
    >>> compressor = SemanticCompressor(min_support=3)
    >>> compressed, stats = compressor.compress(log_lines)
    >>> print(f"Compression ratio: {stats.compression_ratio:.2f}×")
"""

__version__ = "1.0.0"
__author__ = "Adam Bouafia"
__license__ = "MIT"

# Core MCP layers
from logpress import models, protocols
from logpress.context import LogTokenizer, Tokenizer, TemplateGenerator, SemanticTypeRecognizer, SemanticFieldClassifier
from logpress.services import SemanticCompressor, Compressor, QueryEngine, SchemaEvaluator, Evaluator, SchemaVersioner

# Legacy compatibility aliases (already defined in services)
LogTokenizer = LogTokenizer
SemanticTypeRecognizer = SemanticTypeRecognizer
SchemaEvaluator = SchemaEvaluator

__all__ = [
    # MCP Architecture
    'models',
    'protocols',
    'LogTokenizer',
    'Tokenizer',
    'TemplateGenerator',
    'SemanticTypeRecognizer',
    'SemanticFieldClassifier',
    'SemanticCompressor',
    'Compressor',
    'QueryEngine',
    'SchemaEvaluator',
    'Evaluator',
    'SchemaVersioner',
]
