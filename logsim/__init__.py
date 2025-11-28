"""
LogSim - Semantic-Driven Log Schema Extraction and Compression

A production-ready system for extracting implicit schemas from unstructured
system logs and compressing them with semantic awareness.

MCP Architecture:
- Models: Pure data structures (Token, LogTemplate, CompressedLog)
- Protocols: Interface contracts (TokenizerProtocol, EncoderProtocol)
- Context: Domain implementations (Tokenization, Extraction, Encoding)
- Services: Application orchestration (Compressor, QueryEngine)
- CLI: User interface (compress, query commands)
"""

__version__ = "1.0.0"
__author__ = "Master's Thesis Project"
__license__ = "MIT"

# Core MCP layers
from logsim import models, protocols
from logsim.context import LogTokenizer, Tokenizer, TemplateGenerator, SemanticTypeRecognizer, SemanticFieldClassifier
from logsim.services import SemanticCompressor, Compressor, QueryEngine, SchemaEvaluator, Evaluator, SchemaVersioner

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
