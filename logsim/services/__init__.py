"""
Services layer - application orchestration.
"""

from logsim.services.compressor import SemanticCompressor
from logsim.services.query_engine import QueryEngine
from logsim.services.evaluator import SchemaEvaluator
from logsim.services.schema_versioner import SchemaVersioner
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
