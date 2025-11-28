#!/usr/bin/env python3
"""
Gorilla timestamp compression algorithm

Facebook's Gorilla algorithm for efficient timestamp compression:
- Stores first timestamp as-is
- Stores delta-of-deltas with variable-bit encoding
- Achieves 8-12 bits per timestamp (vs 64 bits uncompressed)

Reference: "Gorilla: A Fast, Scalable, In-Memory Time Series Database" (VLDB 2015)
"""

import struct
from typing import List, Tuple


class GorillaTimestampCompressor:
    """Compress timestamps using Gorilla algorithm"""
    
    def __init__(self):
        """Initialize compressor"""
        self.compressed_bits: List[int] = []
        self.bit_position = 0
    
    def compress(self, timestamps: List[int]) -> bytes:
        """
        Compress list of Unix timestamps
        
        Args:
            timestamps: List of Unix timestamps (seconds or milliseconds)
        
        Returns:
            Compressed bytes
        """
        if not timestamps:
            return b''
        
        # Reset state
        self.compressed_bits = []
        self.bit_position = 0
        
        # Store first timestamp as-is (64 bits)
        self._write_bits(timestamps[0], 64)
        
        if len(timestamps) == 1:
            return self._get_bytes()
        
        # Store first delta (32 bits is enough for typical log time ranges)
        delta = timestamps[1] - timestamps[0]
        self._write_bits(delta & 0xFFFFFFFF, 32)
        
        if len(timestamps) == 2:
            return self._get_bytes()
        
        # Compress subsequent deltas using delta-of-deltas
        prev_delta = delta
        for i in range(2, len(timestamps)):
            current_delta = timestamps[i] - timestamps[i-1]
            delta_of_delta = current_delta - prev_delta
            
            self._compress_delta_of_delta(delta_of_delta)
            prev_delta = current_delta
        
        return self._get_bytes()
    
    def _compress_delta_of_delta(self, dod: int):
        """
        Compress delta-of-delta using variable-bit encoding
        
        Encoding scheme:
        - 0: same delta (1 bit)
        - 10: delta changed by [-63, 64] (2 + 7 bits = 9 bits)
        - 110: delta changed by [-255, 256] (3 + 9 bits = 12 bits)
        - 1110: delta changed by [-2047, 2048] (4 + 12 bits = 16 bits)
        - 1111: delta changed significantly (4 + 32 bits = 36 bits)
        """
        if dod == 0:
            # Same delta: 1 bit
            self._write_bits(0, 1)
        elif -63 <= dod <= 64:
            # Small change: 2 + 7 bits = 9 bits
            self._write_bits(0b10, 2)
            self._write_bits(dod & 0x7F, 7)
        elif -255 <= dod <= 256:
            # Medium change: 3 + 9 bits = 12 bits
            self._write_bits(0b110, 3)
            self._write_bits(dod & 0x1FF, 9)
        elif -2047 <= dod <= 2048:
            # Larger change: 4 + 12 bits = 16 bits
            self._write_bits(0b1110, 4)
            self._write_bits(dod & 0xFFF, 12)
        else:
            # Significant change: 4 + 32 bits = 36 bits
            self._write_bits(0b1111, 4)
            self._write_bits(dod & 0xFFFFFFFF, 32)
    
    def _write_bits(self, value: int, num_bits: int):
        """Write bits to compressed stream"""
        for i in range(num_bits):
            bit = (value >> (num_bits - 1 - i)) & 1
            self.compressed_bits.append(bit)
            self.bit_position += 1
    
    def _get_bytes(self) -> bytes:
        """Convert bit stream to bytes"""
        # Pad to byte boundary
        while len(self.compressed_bits) % 8 != 0:
            self.compressed_bits.append(0)
        
        # Convert bits to bytes
        result = bytearray()
        for i in range(0, len(self.compressed_bits), 8):
            byte_bits = self.compressed_bits[i:i+8]
            byte_value = 0
            for j, bit in enumerate(byte_bits):
                byte_value |= (bit << (7 - j))
            result.append(byte_value)
        
        return bytes(result)
    
    def decompress(self, compressed: bytes, count: int) -> List[int]:
        """
        Decompress timestamps
        
        Args:
            compressed: Compressed bytes
            count: Number of timestamps
        
        Returns:
            List of decompressed timestamps
        """
        if count == 0:
            return []
        
        # Convert bytes to bits
        bits = []
        for byte in compressed:
            for i in range(8):
                bits.append((byte >> (7 - i)) & 1)
        
        bit_pos = 0
        
        def read_bits(n):
            nonlocal bit_pos
            value = 0
            for i in range(n):
                if bit_pos < len(bits):
                    value = (value << 1) | bits[bit_pos]
                    bit_pos += 1
            return value
        
        # Read first timestamp
        timestamps = [read_bits(64)]
        
        if count == 1:
            return timestamps
        
        # Read first delta
        first_delta = read_bits(32)
        # Handle signed 32-bit
        if first_delta & 0x80000000:
            first_delta -= 0x100000000
        
        timestamps.append(timestamps[0] + first_delta)
        
        if count == 2:
            return timestamps
        
        # Read delta-of-deltas
        prev_delta = first_delta
        for _ in range(count - 2):
            # Read control bits
            if bit_pos >= len(bits):
                break
            
            if bits[bit_pos] == 0:
                # Same delta
                bit_pos += 1
                dod = 0
            elif bit_pos + 1 < len(bits) and bits[bit_pos+1] == 0:
                # Small change
                bit_pos += 2
                dod = read_bits(7)
                if dod & 0x40:
                    dod -= 0x80
            elif bit_pos + 2 < len(bits) and bits[bit_pos+2] == 0:
                # Medium change
                bit_pos += 3
                dod = read_bits(9)
                if dod & 0x100:
                    dod -= 0x200
            elif bit_pos + 3 < len(bits) and bits[bit_pos+3] == 0:
                # Larger change
                bit_pos += 4
                dod = read_bits(12)
                if dod & 0x800:
                    dod -= 0x1000
            else:
                # Significant change
                bit_pos += 4
                dod = read_bits(32)
                if dod & 0x80000000:
                    dod -= 0x100000000
            
            current_delta = prev_delta + dod
            timestamps.append(timestamps[-1] + current_delta)
            prev_delta = current_delta
        
        return timestamps


def benchmark_gorilla():
    """Benchmark Gorilla compression"""
    import time
    
    print("🚀 Gorilla Timestamp Compression Benchmark")
    print("=" * 80)
    
    # Generate realistic log timestamps (1 second intervals)
    base_time = 1717891200  # 2024-06-09 00:00:00
    timestamps = [base_time + i for i in range(10000)]
    
    # Test 1: Regular intervals
    print("\n[Test 1] Regular intervals (1 second apart)")
    compressor = GorillaTimestampCompressor()
    
    start = time.time()
    compressed = compressor.compress(timestamps)
    compress_time = time.time() - start
    
    original_size = len(timestamps) * 8  # 8 bytes per timestamp
    compressed_size = len(compressed)
    ratio = original_size / compressed_size
    
    print(f"  • Original:   {original_size:,} bytes ({original_size/1024:.1f} KB)")
    print(f"  • Compressed: {compressed_size:,} bytes ({compressed_size/1024:.1f} KB)")
    print(f"  • Ratio:      {ratio:.2f}x")
    print(f"  • Time:       {compress_time*1000:.2f}ms")
    print(f"  • Bits/value: {compressed_size*8/len(timestamps):.1f} bits")
    
    # Verify decompression
    start = time.time()
    decompressed = compressor.decompress(compressed, len(timestamps))
    decompress_time = time.time() - start
    
    print(f"  • Decompress: {decompress_time*1000:.2f}ms")
    print(f"  • Correct:    {decompressed == timestamps}")
    
    # Test 2: Variable intervals (more realistic logs)
    import random
    random.seed(42)
    variable_timestamps = [base_time]
    for _ in range(9999):
        # Random interval between 1-10 seconds
        variable_timestamps.append(variable_timestamps[-1] + random.randint(1, 10))
    
    print("\n[Test 2] Variable intervals (1-10 seconds)")
    compressed2 = compressor.compress(variable_timestamps)
    compressed_size2 = len(compressed2)
    ratio2 = original_size / compressed_size2
    
    print(f"  • Original:   {original_size:,} bytes ({original_size/1024:.1f} KB)")
    print(f"  • Compressed: {compressed_size2:,} bytes ({compressed_size2/1024:.1f} KB)")
    print(f"  • Ratio:      {ratio2:.2f}x")
    print(f"  • Bits/value: {compressed_size2*8/len(variable_timestamps):.1f} bits")
    
    decompressed2 = compressor.decompress(compressed2, len(variable_timestamps))
    print(f"  • Correct:    {decompressed2 == variable_timestamps}")
    
    # Comparison with naive delta encoding
    print("\n[Comparison] vs Naive Delta Encoding")
    naive_size = 8 + (len(timestamps) - 1) * 4  # First timestamp + 32-bit deltas
    print(f"  • Naive delta:   {naive_size:,} bytes ({naive_size/1024:.1f} KB)")
    print(f"  • Gorilla:       {compressed_size:,} bytes ({compressed_size/1024:.1f} KB)")
    print(f"  • Improvement:   {naive_size/compressed_size:.2f}x better")
    
    print("\n" + "=" * 80)
    print(f"✅ Gorilla achieves {ratio:.1f}x compression on regular timestamps")
    print(f"✅ Gorilla achieves {ratio2:.1f}x compression on variable timestamps")
    print(f"✅ Average {compressed_size*8/len(timestamps):.1f} bits per timestamp")


if __name__ == "__main__":
    benchmark_gorilla()
