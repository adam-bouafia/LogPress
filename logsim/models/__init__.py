"""
Data models and schemas for LogSim.

This module contains pure data structures with no business logic.
"""

from dataclasses import dataclass, field as dataclass_field
from typing import List, Dict, Optional, Any
from enum import Enum

__all__ = [
    'Token',
    'LogTemplate', 
    'CompressedLog',
    'SemanticFieldType',
    'TemplateField'
]


@dataclass
class Token:
    """Represents a single token from log tokenization."""
    value: str
    start_pos: int
    end_pos: int
    token_type: str  # 'BRACKET', 'DELIMITER', 'WORD', etc.


@dataclass
class TemplateField:
    """Represents a field within a log template."""
    name: str
    field_type: str  # 'TIMESTAMP', 'SEVERITY', 'MESSAGE', etc.
    position: int
    is_variable: bool
    pattern: Optional[str] = None


@dataclass
class LogTemplate:
    """Represents an extracted log schema template."""
    template_id: str
    pattern: List[str]
    fields: List[TemplateField]
    log_count: int
    sample_logs: List[str]
    confidence: float = 1.0


@dataclass
class CompressedLog:
    """Container for compressed log data with metadata."""
    templates: Dict[str, LogTemplate]
    template_ids: List[str]
    
    # Encoded columns
    timestamps: bytes
    severity_list: bytes
    ip_list: bytes
    message_list: bytes
    
    # Metadata
    original_size: int
    compressed_size: int
    log_count: int
    compression_time: float


class SemanticFieldType(Enum):
    """Enumeration of semantic field types."""
    TIMESTAMP = "timestamp"
    SEVERITY = "severity"
    IP_ADDRESS = "ip_address"
    PROCESS_ID = "process_id"
    COMPONENT = "component"
    MESSAGE = "message"
    USER_ID = "user_id"
    ERROR_CODE = "error_code"
    METRIC = "metric"
    UNKNOWN = "unknown"
