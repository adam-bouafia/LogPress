#!/usr/bin/env python3
"""
Variable-length integer encoding (varint)

Protocol Buffer style varint encoding for efficient small integer storage:
- Values 0-127: 1 byte
- Values 128-16,383: 2 bytes  
- Values 16,384-2,097,151: 3 bytes
- etc.

Most log data (timestamp deltas, severity IDs, template indices) are small,
making varint encoding much more efficient than fixed 32/64-bit integers.
"""

from typing import List


def encode_varint(value: int) -> bytes:
    """
    Encode integer as variable-length bytes using Protocol Buffer encoding
    
    Args:
        value: Non-negative integer to encode
        
    Returns:
        Bytes representing the varint (1-10 bytes)
        
    Examples:
        >>> encode_varint(0)
        b'\\x00'
        >>> encode_varint(127)
        b'\\x7f'
        >>> encode_varint(128)
        b'\\x80\\x01'
        >>> encode_varint(300)
        b'\\xac\\x02'
    """
    if value < 0:
        raise ValueError(f"Cannot encode negative value: {value}")
    
    result = bytearray()
    
    while value > 0x7F:
        # Set high bit (0x80) to indicate more bytes follow
        result.append((value & 0x7F) | 0x80)
        value >>= 7
    
    # Last byte: no high bit set
    result.append(value & 0x7F)
    
    return bytes(result)


def decode_varint(data: bytes, offset: int = 0) -> tuple[int, int]:
    """
    Decode varint from bytes starting at offset
    
    Args:
        data: Bytes containing varint
        offset: Starting position in bytes
        
    Returns:
        Tuple of (decoded_value, bytes_consumed)
        
    Examples:
        >>> decode_varint(b'\\x00')
        (0, 1)
        >>> decode_varint(b'\\x7f')
        (127, 1)
        >>> decode_varint(b'\\x80\\x01')
        (128, 2)
        >>> decode_varint(b'\\xac\\x02')
        (300, 2)
    """
    result = 0
    shift = 0
    bytes_read = 0
    
    while True:
        if offset + bytes_read >= len(data):
            raise ValueError(f"Incomplete varint at offset {offset}")
        
        byte = data[offset + bytes_read]
        bytes_read += 1
        
        # Add 7 bits to result
        result |= (byte & 0x7F) << shift
        shift += 7
        
        # If high bit not set, we're done
        if (byte & 0x80) == 0:
            break
        
        if shift > 64:
            raise ValueError(f"Varint too large at offset {offset}")
    
    return result, bytes_read


def encode_varint_list(values: List[int]) -> bytes:
    """
    Encode list of integers as varint sequence
    
    Args:
        values: List of non-negative integers
        
    Returns:
        Concatenated varint bytes
        
    Example:
        >>> encode_varint_list([0, 127, 128, 300])
        b'\\x00\\x7f\\x80\\x01\\xac\\x02'
    """
    result = bytearray()
    for value in values:
        result.extend(encode_varint(value))
    return bytes(result)


def decode_varint_list(data: bytes, count: int) -> List[int]:
    """
    Decode sequence of varints from bytes
    
    Args:
        data: Bytes containing varint sequence
        count: Number of varints to decode
        
    Returns:
        List of decoded integers
        
    Example:
        >>> decode_varint_list(b'\\x00\\x7f\\x80\\x01\\xac\\x02', 4)
        [0, 127, 128, 300]
    """
    result = []
    offset = 0
    
    for _ in range(count):
        value, bytes_read = decode_varint(data, offset)
        result.append(value)
        offset += bytes_read
    
    return result


def estimate_varint_size(value: int) -> int:
    """
    Estimate bytes needed for varint encoding
    
    Args:
        value: Integer to estimate
        
    Returns:
        Number of bytes (1-10)
        
    Examples:
        >>> estimate_varint_size(0)
        1
        >>> estimate_varint_size(127)
        1
        >>> estimate_varint_size(128)
        2
        >>> estimate_varint_size(16383)
        2
        >>> estimate_varint_size(16384)
        3
    """
    if value < 0:
        return 10  # Negative numbers need special handling
    if value == 0:
        return 1
    
    # Count 7-bit groups needed
    bits_needed = value.bit_length()
    return (bits_needed + 6) // 7


def estimate_varint_list_size(values: List[int]) -> int:
    """
    Estimate total bytes for varint list
    
    Args:
        values: List of integers
        
    Returns:
        Total estimated bytes
    """
    return sum(estimate_varint_size(v) for v in values)


# Benchmarking helpers
def compare_sizes(values: List[int]) -> dict:
    """
    Compare varint vs fixed-size encoding
    
    Args:
        values: List of integers to analyze
        
    Returns:
        Dict with size comparisons
    """
    # Fixed size (int32 = 4 bytes each)
    fixed_size = len(values) * 4
    
    # Varint size
    varint_data = encode_varint_list(values)
    varint_size = len(varint_data)
    
    # Statistics
    return {
        'count': len(values),
        'fixed_size': fixed_size,
        'varint_size': varint_size,
        'compression_ratio': fixed_size / varint_size if varint_size > 0 else 0,
        'space_saved': fixed_size - varint_size,
        'space_saved_pct': (1 - varint_size / fixed_size) * 100 if fixed_size > 0 else 0
    }


if __name__ == '__main__':
    # Self-test
    import doctest
    doctest.testmod()
    
    # Example: timestamp deltas
    print("Varint Encoding Demo")
    print("=" * 60)
    
    # Simulate timestamp deltas (most are small)
    deltas = [0, 5, 12, 3, 7, 125, 256, 1000, 4, 8, 15, 23]
    
    print(f"\\nTimestamp deltas: {deltas}")
    print(f"Value range: {min(deltas)} to {max(deltas)}")
    
    stats = compare_sizes(deltas)
    print(f"\\nFixed int32: {stats['fixed_size']} bytes ({len(deltas)} × 4)")
    print(f"Varint:      {stats['varint_size']} bytes")
    print(f"Compression: {stats['compression_ratio']:.2f}x")
    print(f"Space saved: {stats['space_saved']} bytes ({stats['space_saved_pct']:.1f}%)")
    
    # Verify round-trip
    encoded = encode_varint_list(deltas)
    decoded = decode_varint_list(encoded, len(deltas))
    assert decoded == deltas, "Round-trip failed!"
    print(f"\\n✓ Round-trip verification passed")
