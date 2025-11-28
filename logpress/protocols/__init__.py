"""
Protocols (interfaces) for logpress components.

This module defines abstract contracts that implementations must follow.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from logpress.models import Token, LogTemplate

__all__ = [
    'TokenizerProtocol',
    'EncoderProtocol',
    'CompressorProtocol',
    'QueryEngineProtocol'
]


class TokenizerProtocol(ABC):
    """Protocol for log tokenization."""
    
    @abstractmethod
    def tokenize(self, log_line: str) -> List[Token]:
        """
        Tokenize a log line into structured tokens.
        
        Args:
            log_line: Raw log string
            
        Returns:
            List of Token objects
        """
        pass


class EncoderProtocol(ABC):
    """Protocol for encoding/decoding data."""
    
    @abstractmethod
    def encode(self, values: List[Any]) -> bytes:
        """
        Encode a list of values into compressed bytes.
        
        Args:
            values: List of values to encode
            
        Returns:
            Encoded byte data
        """
        pass
    
    @abstractmethod
    def decode(self, data: bytes) -> List[Any]:
        """
        Decode compressed bytes back to original values.
        
        Args:
            data: Encoded byte data
            
        Returns:
            Original values
        """
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return encoder name for logging."""
        pass


class CompressorProtocol(ABC):
    """Protocol for compression/decompression."""
    
    @abstractmethod
    def compress(self, data: bytes) -> bytes:
        """Compress byte data."""
        pass
    
    @abstractmethod
    def decompress(self, data: bytes) -> bytes:
        """Decompress byte data."""
        pass
    
    @property
    @abstractmethod
    def level(self) -> int:
        """Return compression level."""
        pass


class QueryEngineProtocol(ABC):
    """Protocol for querying compressed logs."""
    
    @abstractmethod
    def load(self, compressed_file: str):
        """Load compressed log file."""
        pass
    
    @abstractmethod
    def count(self) -> int:
        """Return total log count."""
        pass
    
    @abstractmethod
    def query_by_severity(self, severity: str, limit: Optional[int] = None) -> List[str]:
        """Query logs by severity level."""
        pass
    
    @abstractmethod
    def query_by_ip(self, ip: str, limit: Optional[int] = None) -> List[str]:
        """Query logs by IP address."""
        pass
