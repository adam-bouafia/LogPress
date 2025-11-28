"""
Encoding context for data compression.
"""

from logsim.context.encoding.varint import encode_varint, decode_varint
from logsim.context.encoding.bwt import bwt_transform, bwt_inverse
from logsim.context.encoding.gorilla import GorillaTimestampCompressor

__all__ = [
    'encode_varint',
    'decode_varint',
    'bwt_transform',
    'bwt_inverse',
    'GorillaTimestampCompressor',
]
