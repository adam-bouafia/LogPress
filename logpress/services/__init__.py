"""
Services layer - application orchestration.
"""

from logpress.services.compressor import SemanticCompressor
from logpress.services.query_engine import QueryEngine
from logpress.services.evaluator import SchemaEvaluator
from logpress.services.schema_versioner import SchemaVersioner
# Note: intrinsic_metrics is a script module, not a service class

# Provide consistent naming
Compressor = SemanticCompressor
Evaluator = SchemaEvaluator

__all__ = [
    'SemanticCompressor',
    'QueryEngine',
    'SchemaEvaluator',
    'SchemaVersioner',
    # Aliases
    'Compressor',
    'Evaluator',
]
