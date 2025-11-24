"""
Compressor: Category-aware compression with semantic understanding

This module compresses logs using schema-aware strategies:
- Timestamps: Delta encoding (store differences)
- Categorical fields: Dictionary encoding (severity, status)
- Metrics: Gorilla time-series compression
- Text: Reference tracking for repeated patterns
- BWT preprocessing: Burrows-Wheeler Transform for better entropy coding
- Maintains queryable columnar format

Target: 10-30x compression ratio while preserving query capability
"""

import struct
import json
import gzip
import msgpack
import zstandard as zstd
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field as dataclass_field
from collections import defaultdict
from pathlib import Path
from datetime import datetime
import time

from .template_generator import TemplateGenerator, LogTemplate
from .gorilla_compression import GorillaTimestampCompressor
from .semantic_types import SemanticType
from .bwt import bwt_transform, bwt_inverse
from .varint import (
    encode_varint_list, decode_varint_list,
    encode_varint, decode_varint
)
from .bwt import bwt_transform, bwt_inverse
from .preprocessor import OttenPreprocessor  # Otten's binary encoding
from .template_dictionary import TemplateDictionary  # Otten's word dictionaries

# Load universal Zstandard dictionary (trained from all datasets)
_UNIVERSAL_DICT = None
_UNIVERSAL_DICT_PATH = Path(__file__).parent / "universal_dict.zstd"

def load_universal_dict() -> Optional[bytes]:
    """Load pre-trained universal Zstandard dictionary"""
    global _UNIVERSAL_DICT
    if _UNIVERSAL_DICT is None and _UNIVERSAL_DICT_PATH.exists():
        with open(_UNIVERSAL_DICT_PATH, 'rb') as f:
            _UNIVERSAL_DICT = f.read()
    return _UNIVERSAL_DICT


def zigzag_encode(n: int) -> int:
    """Zigzag encoding for signed integers: maps negatives to positive odds"""
    if n >= 0:
        return n << 1
    else:
        return ((-n) << 1) - 1


def zigzag_decode(n: int) -> int:
    """Decode zigzag encoded integer"""
    return (n >> 1) ^ (-(n & 1))


def encode_rle(values: List[int]) -> bytes:
    """Run-length encode list of integers using varint"""
    if not values:
        return b''
    
    result = bytearray()
    current_val = values[0]
    count = 1
    
    for val in values[1:]:
        if val == current_val and count < 65535:  # Max count per run
            count += 1
        else:
            result.extend(encode_varint(current_val))
            result.extend(encode_varint(count))
            current_val = val
            count = 1
    
    # Last run
    result.extend(encode_varint(current_val))
    result.extend(encode_varint(count))
    
    return bytes(result)


def decode_rle(data: bytes, expected_count: int) -> List[int]:
    """Decode run-length encoded varints"""
    result = []
    offset = 0
    
    while len(result) < expected_count and offset < len(data):
        value, bytes_read = decode_varint(data, offset)
        offset += bytes_read
        count, bytes_read = decode_varint(data, offset)
        offset += bytes_read
        result.extend([value] * count)
    
    return result[:expected_count]


def encode_rle_v2(values: List[int]) -> bytes:
    """Enhanced RLE: detect repeating patterns, not just consecutive runs
    
    Example: [1,2,3,1,2,3,1,2,3] → pattern=[1,2,3] repeat=3
    Format: <pattern_len><pattern_values...><repeat_count>
    """
    if not values or len(values) < 4:
        return encode_rle(values)  # Fallback to simple RLE
    
    result = bytearray()
    
    # Try pattern lengths from 2 to len(values)//2
    best_compression = None
    best_pattern_len = 1
    
    for pattern_len in range(2, min(len(values) // 2 + 1, 20)):
        # Check if values form repeating pattern
        pattern = values[:pattern_len]
        repeats = 0
        idx = 0
        
        while idx + pattern_len <= len(values):
            if values[idx:idx + pattern_len] == pattern:
                repeats += 1
                idx += pattern_len
            else:
                break
        
        # Pattern must repeat at least 3 times to be worth encoding
        if repeats >= 3:
            compressed_size = 1 + pattern_len + 1  # pattern_len + pattern + repeat_count (approx)
            original_size = repeats * pattern_len
            if best_compression is None or compressed_size < best_compression:
                best_compression = compressed_size
                best_pattern_len = pattern_len
    
    # Encode with best pattern if found
    if best_compression and best_pattern_len > 1:
        pattern = values[:best_pattern_len]
        repeats = 0
        idx = 0
        
        while idx + best_pattern_len <= len(values):
            if values[idx:idx + best_pattern_len] == pattern:
                repeats += 1
                idx += best_pattern_len
            else:
                break
        
        # Encode pattern
        result.append(0xFF)  # Marker for pattern encoding
        result.extend(encode_varint(best_pattern_len))
        for val in pattern:
            result.extend(encode_varint(val))
        result.extend(encode_varint(repeats))
        
        # Encode remaining values with simple RLE
        if idx < len(values):
            remaining_rle = encode_rle(values[idx:])
            result.extend(remaining_rle)
        
        return bytes(result)
    else:
        # No pattern found, use simple RLE
        return encode_rle(values)


def decode_rle_v2(data: bytes, expected_count: int) -> List[int]:
    """Decode enhanced RLE with pattern support"""
    if not data or data[0] != 0xFF:
        return decode_rle(data, expected_count)
    
    result = []
    offset = 1  # Skip marker
    
    # Decode pattern
    pattern_len, bytes_read = decode_varint(data, offset)
    offset += bytes_read
    
    pattern = []
    for _ in range(pattern_len):
        val, bytes_read = decode_varint(data, offset)
        offset += bytes_read
        pattern.append(val)
    
    repeats, bytes_read = decode_varint(data, offset)
    offset += bytes_read
    
    # Reconstruct pattern repetitions
    for _ in range(repeats):
        result.extend(pattern)
    
    # Decode remaining with simple RLE
    if offset < len(data) and len(result) < expected_count:
        remaining = decode_rle(data[offset:], expected_count - len(result))
        result.extend(remaining)
    
    return result[:expected_count]


def build_token_pool(templates: List['LogTemplate']) -> Tuple[List[str], List[List[int]]]:
    """Build global token pool and deduplicate template tokens
    
    Returns:
        token_pool: List of unique tokens
        template_refs: List of token ID lists for each template
    """
    token_to_id = {}
    token_pool = []
    template_refs = []
    
    for template in templates:
        # Pattern is already a list of tokens (List[str])
        tokens = template.pattern if isinstance(template.pattern, list) else template.pattern.split()
        token_ids = []
        
        for token in tokens:
            if token not in token_to_id:
                token_to_id[token] = len(token_pool)
                token_pool.append(token)
            token_ids.append(token_to_id[token])
        
        template_refs.append(token_ids)
    
    return token_pool, template_refs


def reconstruct_template_patterns(token_pool: List[str], template_refs: List[List[int]]) -> List[str]:
    """Reconstruct template patterns from token pool references"""
    patterns = []
    for token_ids in template_refs:
        pattern = ' '.join(token_pool[tid] for tid in token_ids)
        patterns.append(pattern)
    return patterns


@dataclass
class CompressionStats:
    """Statistics about compression operation"""
    original_size: int
    compressed_size: int
    compression_ratio: float
    compression_time: float
    log_count: int
    template_count: int
    
    def __repr__(self):
        return (f"CompressionStats(ratio={self.compression_ratio:.2f}x, "
                f"time={self.compression_time:.2f}s, logs={self.log_count})")


@dataclass
class CompressedLog:
    """Compressed log storage format for semantic-aware compression"""
    version: str = "1.0"
    templates: List[Dict] = dataclass_field(default_factory=list)
    
    # Token pool for template deduplication
    token_pool: List[str] = dataclass_field(default_factory=list)
    template_token_refs: List[bytes] = dataclass_field(default_factory=list)  # Varint-encoded token IDs
    
    # Trained Zstd dictionary for messages
    zstd_dict: Optional[bytes] = None
    
    # Otten's template dictionaries (word-based encoding)
    template_dicts_serialized: Optional[Dict[str, Dict]] = None
    
    # Varint-encoded columnar storage (stored as bytes)
    timestamps_varint: bytes = b''  # Zigzag + varint encoded deltas
    timestamp_base: int = 0
    timestamp_count: int = 0
    severities_varint: bytes = b''  # Fallback for large cardinality
    severity_count: int = 0
    
    ip_addresses_varint: bytes = b''  # Varint encoded dictionary IDs
    ip_count: int = 0
    
    messages_varint: bytes = b''  # Varint encoded dictionary IDs
    message_count: int = 0
    
    # Dictionaries as lists (more compact than dict with int keys)
    severity_list: List[str] = dataclass_field(default_factory=list)
    ip_list: List[str] = dataclass_field(default_factory=list)
    message_list: List[str] = dataclass_field(default_factory=list)
    
    # Index: RLE-compressed template IDs + varint field indices
    log_index_templates_rle: bytes = b''  # RLE compressed template IDs
    log_index_fields_varint: bytes = b''  # Varint field indices (flat list)
    log_index_field_counts: List[int] = dataclass_field(default_factory=list)  # Fields per log
    
    # Metadata
    original_count: int = 0
    compressed_at: str = ""


class SemanticCompressor:
    """
    Semantic-aware log compressor
    
    Compression strategies based on field semantic types:
    1. TIMESTAMP: Delta encoding (store differences from baseline)
    2. SEVERITY/STATUS: Dictionary encoding (low cardinality)
    3. IP_ADDRESS/HOST: Dictionary encoding
    4. MESSAGE: Dictionary encoding with zstd for unique messages
    5. PROCESS_ID/USER_ID: Dictionary encoding
    
    Storage format: Columnar with indexes for fast queries
    """
    
    def __init__(self, min_support: int = 3, enable_otten: bool = False):
        self.generator = TemplateGenerator(min_support=min_support)
        self.compressed_data = None
        self.enable_otten = enable_otten  # Otten's preprocessing techniques
        
        # Initialize Otten's preprocessors
        if self.enable_otten:
            self.preprocessor = OttenPreprocessor()
            self.template_dicts: Dict[str, TemplateDictionary] = {}  # template_id → dictionary
        
    def compress(self, log_lines: List[str], verbose: bool = True) -> Tuple[CompressedLog, CompressionStats]:
        """
        Compress logs using semantic-aware strategies
        
        Args:
            log_lines: List of raw log strings
            verbose: Print progress information
            
        Returns:
            Tuple of (compressed_data, compression_stats)
        """
        start_time = time.time()
        
        if verbose:
            print(f"🗜️  Starting compression of {len(log_lines)} logs...")
        
        # Step 1: Extract schemas
        if verbose:
            print(f"  [1/4] Extracting schemas...")
        templates = self.generator.extract_schemas(log_lines)
        
        if not templates:
            raise ValueError("No templates extracted - cannot compress")
        
        if verbose:
            print(f"  ✓ Found {len(templates)} templates")
        
        # Step 2: Match logs to templates and extract fields
        if verbose:
            print(f"  [2/4] Matching logs to templates...")
        
        compressed = CompressedLog()
        compressed.version = '3.3'  # Current format with Otten's preprocessing
        compressed.original_count = len(log_lines)
        compressed.compressed_at = datetime.now().isoformat()
        
        # v3.0: Build token pool for template deduplication
        token_pool, template_refs = build_token_pool(templates)
        compressed.token_pool = token_pool
        compressed.template_token_refs = [encode_varint_list(refs) for refs in template_refs]
        
        if verbose:
            # Calculate actual character savings from deduplication
            total_pattern_chars = sum(len(' '.join(t.pattern)) for t in templates)
            pool_chars = sum(len(token) for token in token_pool) + len(token_pool) - 1  # Include spaces
            ref_bytes = sum(len(ref) for ref in compressed.template_token_refs)
            savings = total_pattern_chars - (pool_chars + ref_bytes)
            if savings > 0:
                print(f"     Token pool: {len(token_pool)} unique tokens, saved {savings} bytes ({savings*100//max(total_pattern_chars,1)}% reduction)")
            elif savings < 0:
                print(f"     Token pool: {len(token_pool)} unique tokens, added {abs(savings)} bytes overhead")
        
        # Store templates (patterns reconstructed from token pool)
        compressed.templates = [
            {
                'id': t.template_id,
                # 'pattern' removed - reconstruct from token_pool + template_token_refs
                'field_types': {pos: ftype.value for pos, ftype in t.field_types.items()},
                'match_count': t.match_count
            }
            for t in templates
        ]
        
        # Compression state
        timestamp_base = None
        last_timestamp = 0
        
        severity_map = {}
        ip_map = {}
        message_map = {}
        
        # Temporary storage for collected data (will be varint-encoded later)
        timestamps_list = []
        severities_list = []
        ips_list = []
        messages_list = []
        log_index = []
        
        matched_count = 0
        
        # Step 3: Build template dictionaries (Otten's word-based encoding)
        if self.enable_otten and verbose:
            print(f"  [3/7] Building per-template word dictionaries (Otten technique)...")
        
        if self.enable_otten:
            # First pass: collect all messages per template to build dictionaries
            template_messages = defaultdict(list)
            
            for log_line in log_lines:
                result = self.generator.match_log_to_template(log_line)
                if result:
                    template, fields = result
                    # Collect MESSAGE fields for dictionary building
                    for field_name, field_value in fields.items():
                        if field_name.upper() not in ('TIMESTAMP', 'SEVERITY', 'STATUS', 'IP_ADDRESS', 'HOST'):
                            template_messages[template.template_id].append(field_value)
            
            # Build dictionaries for each template
            for template_id, messages in template_messages.items():
                if len(messages) >= 2:  # Need at least 2 messages
                    template_dict = TemplateDictionary(template_id)
                    template_dict.build_from_messages(messages, min_freq=2)
                    self.template_dicts[template_id] = template_dict
                    
                    if verbose:
                        stats = template_dict.get_stats()
                        if stats['num_words'] > 0:
                            print(f"     Template {template_id}: {stats['num_words']} words, "
                                  f"avg_len={stats['avg_word_length']:.1f}, "
                                  f"utilization={stats['utilization']:.1f}%")
        
        # Step 4: Process each log and collect fields
        if verbose:
            step_num = "4/7" if self.enable_otten else "3/6"
            print(f"  [{step_num}] Matching and collecting fields...")
        
        for log_line in log_lines:
            result = self.generator.match_log_to_template(log_line)
            
            if not result:
                # Store unmatched log as full message
                msg_id = self._get_or_create_id(log_line, message_map)
                messages_list.append(msg_id)
                log_index.append((-1, [len(messages_list) - 1]))  # -1 = no template
                continue
            
            template, fields = result
            matched_count += 1
            
            # Find template index
            template_idx = next(
                (i for i, t in enumerate(templates) if t.template_id == template.template_id),
                0
            )
            
            # Compress fields based on semantic type
            field_indices = []
            
            for field_name, field_value in fields.items():
                if field_name.upper() == 'TIMESTAMP':
                    # Otten Phase 1: Binary timestamp encoding (15+ bytes → 4 bytes)
                    if self.enable_otten:
                        # Convert to binary, then parse to get epoch seconds
                        binary_ts = self.preprocessor.encode_timestamp_binary(field_value)
                        ts = self.preprocessor.decode_timestamp_binary(binary_ts)
                    else:
                        ts = self._parse_timestamp(field_value)
                    
                    # Delta encoding for timestamps
                    if timestamp_base is None:
                        timestamp_base = ts
                        delta = 0
                    else:
                        delta = ts - last_timestamp
                    timestamps_list.append(delta)
                    last_timestamp = ts
                    field_indices.append(len(timestamps_list) - 1)
                    
                elif field_name.upper() in ('SEVERITY', 'STATUS'):
                    # Dictionary encoding for categorical
                    sev_id = self._get_or_create_id(field_value, severity_map)
                    severities_list.append(sev_id)
                    field_indices.append(len(severities_list) - 1)
                    
                elif field_name.upper() in ('IP_ADDRESS', 'HOST'):
                    # Otten Phase 1: Binary IP encoding (15 bytes → 4 bytes)
                    if self.enable_otten:
                        # Store binary IP in dictionary instead of string
                        binary_ip = self.preprocessor.encode_ip_binary(field_value)
                        ip_id = self._get_or_create_id(binary_ip, ip_map)
                    else:
                        # Dictionary encoding for IPs (original string)
                        ip_id = self._get_or_create_id(field_value, ip_map)
                    
                    ips_list.append(ip_id)
                    field_indices.append(len(ips_list) - 1)
                    
                else:
                    # Otten Phase 2: Word dictionary encoding for messages
                    if self.enable_otten and template.template_id in self.template_dicts:
                        template_dict = self.template_dicts[template.template_id]
                        encoded_msg = template_dict.encode_message(field_value)
                        msg_id = self._get_or_create_id(encoded_msg, message_map)
                    else:
                        # Default: dictionary encoding for messages (original)
                        msg_id = self._get_or_create_id(field_value, message_map)
                    
                    messages_list.append(msg_id)
                    field_indices.append(len(messages_list) - 1)
            
            log_index.append((template_idx, field_indices))
        
        # Step 5: Store template dictionaries in compressed data (for decompression)
        if self.enable_otten:
            # Serialize template dictionaries for decompression
            compressed.template_dicts_serialized = {
                template_id: {
                    'word_to_code': dict(td.word_to_code),
                    'code_to_word': dict(td.code_to_word)
                }
                for template_id, td in self.template_dicts.items()
            }
            
            if verbose:
                total_dict_words = sum(len(td.word_to_code) for td in self.template_dicts.values())
                print(f"     Otten preprocessing: {len(self.template_dicts)} template dicts, {total_dict_words} total words")
        
        # Step 6: Apply varint encoding to all integer arrays
        if verbose:
            step_num = "6/7" if self.enable_otten else "4/6"
            print(f"  [{step_num}] Applying varint compression...")
        
        # Timestamps: zigzag + varint (handles negative deltas)
        if timestamps_list:
            zigzag_deltas = [zigzag_encode(d) for d in timestamps_list]
            compressed.timestamps_varint = encode_varint_list(zigzag_deltas)
            compressed.timestamp_count = len(timestamps_list)
            compressed.timestamp_base = timestamp_base if timestamp_base else 0
            
            if verbose:
                original_size = len(timestamps_list) * 4
                varint_size = len(compressed.timestamps_varint)
                print(f"     Timestamps: {original_size} → {varint_size} bytes ({original_size/varint_size:.1f}x)")
        
        # Severities: varint encoding
        if severities_list:
            compressed.severities_varint = encode_varint_list(severities_list)
            compressed.severity_count = len(severities_list)
        
        # IPs: varint
        if ips_list:
            compressed.ip_addresses_varint = encode_varint_list(ips_list)
            compressed.ip_count = len(ips_list)
        
        # Messages: varint encoding
        if messages_list:
            compressed.messages_varint = encode_varint_list(messages_list)
            compressed.message_count = len(messages_list)
        
        # Step 5: RLE compress log_index template IDs with pattern detection
        if verbose:
            print(f"  [5/6] RLE compressing log index (with pattern detection)...")
        
        template_ids = [idx[0] for idx in log_index]
        # Apply zigzag encoding to handle negative template IDs (-1 for unmatched)
        zigzag_template_ids = [zigzag_encode(tid) for tid in template_ids]
        compressed.log_index_templates_rle = encode_rle_v2(zigzag_template_ids)
        
        # Flatten field indices and store counts
        all_field_indices = []
        field_counts = []
        for _, field_indices in log_index:
            all_field_indices.extend(field_indices)
            field_counts.append(len(field_indices))
        
        compressed.log_index_fields_varint = encode_varint_list(all_field_indices)
        compressed.log_index_field_counts = field_counts
        
        if verbose:
            original_index_size = len(template_ids) * 4 + len(all_field_indices) * 4
            compressed_index_size = len(compressed.log_index_templates_rle) + len(compressed.log_index_fields_varint)
            print(f"     Log index: {original_index_size} → {compressed_index_size} bytes ({original_index_size/compressed_index_size:.1f}x)")
        
        # Step 6: Convert dictionaries to lists and train Zstd dictionary
        if verbose:
            print(f"  [6/6] Optimizing dictionaries and training Zstd dictionary...")
        
        compressed.severity_list = [val for val, idx in sorted(severity_map.items(), key=lambda x: x[1])] if severity_map else []
        compressed.ip_list = [val for val, idx in sorted(ip_map.items(), key=lambda x: x[1])] if ip_map else []
        compressed.message_list = [val for val, idx in sorted(message_map.items(), key=lambda x: x[1])] if message_map else []
        
        # Train Zstd dictionary on message corpus
        if len(compressed.message_list) >= 100:
            # Use first 1000 messages as training corpus
            valid_messages = [msg for msg in compressed.message_list[:1000] if msg and isinstance(msg, str)]
            
            if len(valid_messages) >= 50:
                corpus = '\n'.join(valid_messages)
                samples = [corpus.encode('utf-8')]
                
                # Train 20KB dictionary
                try:
                    dict_data = zstd.train_dictionary(20 * 1024, samples)
                    compressed.zstd_dict = dict_data.as_bytes()
                    
                    if verbose:
                        print(f"     Trained Zstd dictionary: {len(compressed.zstd_dict):,} bytes from {len(valid_messages)} messages")
                except Exception as e:
                    if verbose:
                        print(f"     Zstd dictionary training skipped: {e}")
                    compressed.zstd_dict = None
            else:
                compressed.zstd_dict = None
        else:
            compressed.zstd_dict = None
        
        # Calculate statistics
        original_size = sum(len(log.encode('utf-8')) for log in log_lines)
        compressed_size = self._estimate_compressed_size(compressed)
        
        compression_time = time.time() - start_time
        
        stats = CompressionStats(
            original_size=original_size,
            compressed_size=compressed_size,
            compression_ratio=original_size / compressed_size if compressed_size > 0 else 0,
            compression_time=compression_time,
            log_count=len(log_lines),
            template_count=len(templates)
        )
        
        if verbose:
            print(f"\n✅ Compression complete!")
            print(f"  • Original size: {original_size:,} bytes ({original_size/1024:.1f} KB)")
            print(f"  • Compressed size: {compressed_size:,} bytes ({compressed_size/1024:.1f} KB)")
            print(f"  • Compression ratio: {stats.compression_ratio:.2f}x")
            print(f"  • Matched logs: {matched_count}/{len(log_lines)} ({matched_count/len(log_lines)*100:.1f}%)")
            print(f"  • Time: {compression_time:.2f}s")
            print(f"  • Dictionaries: severity={len(severity_map)}, ip={len(ip_map)}, message={len(message_map)}")
        
        self.compressed_data = compressed
        return compressed, stats
    
    def _parse_timestamp(self, ts_str: str) -> int:
        """Convert timestamp string to Unix epoch (milliseconds)"""
        try:
            # Try various timestamp formats
            # ISO format: 2024-11-23T10:15:32 or 2024-11-23 10:15:32
            if 'T' in ts_str or len(ts_str) == 19:
                dt = datetime.fromisoformat(ts_str.replace('T', ' '))
                return int(dt.timestamp() * 1000)
            
            # Custom format: 20171223-22:15:29:606
            if '-' in ts_str and ':' in ts_str and len(ts_str) > 20:
                parts = ts_str.split('-')
                if len(parts[0]) == 8:  # YYYYMMDD
                    date_part = parts[0]
                    time_part = '-'.join(parts[1:])
                    year = date_part[:4]
                    month = date_part[4:6]
                    day = date_part[6:8]
                    dt_str = f"{year}-{month}-{day} {time_part.replace(':', ':', 2).replace(':', '.', 1)}"
                    dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S.%f")
                    return int(dt.timestamp() * 1000)
            
            # Unix timestamp (already in seconds or milliseconds)
            if ts_str.isdigit():
                ts = int(ts_str)
                if ts > 10**12:  # Milliseconds
                    return ts
                else:  # Seconds
                    return ts * 1000
            
            # Default: return 0 if can't parse
            return 0
            
        except Exception:
            return 0
    
    def _get_or_create_id(self, value: str, mapping: Dict[str, int]) -> int:
        """Get or create dictionary ID for a value"""
        if value not in mapping:
            mapping[value] = len(mapping)
        return mapping[value]
    
    def _estimate_compressed_size(self, compressed: CompressedLog) -> int:
        """Estimate compressed data size in bytes (for varint format)"""
        size = 0
        
        # Templates (still JSON)
        size += len(json.dumps(compressed.templates).encode('utf-8'))
        
        # Varint-encoded fields (already bytes)
        size += len(compressed.timestamps_varint)
        size += len(compressed.severities_varint)
        size += len(compressed.ip_addresses_varint)
        size += len(compressed.messages_varint)
        
        # Dictionaries as lists (handle both strings and bytes)
        size += len(json.dumps(compressed.severity_list).encode('utf-8'))
        
        # IP list might contain bytes (Otten's binary encoding)
        ip_list_size = 0
        for ip in compressed.ip_list:
            if isinstance(ip, bytes):
                ip_list_size += len(ip)
            else:
                ip_list_size += len(str(ip).encode('utf-8'))
        size += ip_list_size
        
        # Message list might contain bytes (Otten's word encoding)
        message_list_size = 0
        for msg in compressed.message_list:
            if isinstance(msg, bytes):
                message_list_size += len(msg)
            else:
                message_list_size += len(str(msg).encode('utf-8'))
        size += message_list_size // 3  # Estimate zstd compression
        
        # RLE + varint index
        size += len(compressed.log_index_templates_rle)
        size += len(compressed.log_index_fields_varint)
        size += len(compressed.log_index_field_counts) * 4  # List of counts
        
        return size
    
    def save(self, filepath: Path, verbose: bool = False, use_bwt: bool = False):
        """Save optimized compressed data (varint + RLE + MessagePack + [BWT] + zstd)
        
        Args:
            filepath: Output file path
            verbose: Print compression statistics
            use_bwt: Apply Burrows-Wheeler Transform before Zstd (default: False)
                    BWT achieves 28.10x avg compression (+79.7% vs baseline)
                    but adds ~2s processing time per 5K logs
        """
        if not self.compressed_data:
            raise ValueError("No compressed data to save")
        
        cd = self.compressed_data
        
        output = {
            'version': cd.version,
            'templates': cd.templates,
            
            # v3.0: Token pool and Zstd dictionary
            'token_pool': cd.token_pool,
            'template_token_refs': cd.template_token_refs,
            'zstd_dict': cd.zstd_dict,
            
            # v3.3: Otten's template dictionaries (word-based encoding)
            'template_dicts_serialized': cd.template_dicts_serialized,
            
            # Varint-encoded fields (already bytes)
            'timestamps_varint': cd.timestamps_varint,
            'timestamp_base': cd.timestamp_base,
            'timestamp_count': cd.timestamp_count,
            'severities_varint': cd.severities_varint,
            'severity_count': cd.severity_count,
            'ip_addresses_varint': cd.ip_addresses_varint,
            'ip_count': cd.ip_count,
            'messages_varint': cd.messages_varint,
            'message_count': cd.message_count,
            
            # Dictionaries as lists
            'severity_list': cd.severity_list,
            'ip_list': cd.ip_list,
            'message_list': cd.message_list,
            
            # RLE + varint index
            'log_index_templates_rle': cd.log_index_templates_rle,
            'log_index_fields_varint': cd.log_index_fields_varint,
            'log_index_field_counts': cd.log_index_field_counts,
            
            'original_count': cd.original_count,
            'compressed_at': cd.compressed_at
        }
        
        # MessagePack + optional BWT + zstd with trained dictionary
        msgpack_data = msgpack.packb(output, use_bin_type=True)
        
        # Apply BWT preprocessing if requested
        if use_bwt:
            if verbose:
                print(f"   Applying BWT preprocessing...")
            import time
            start = time.time()
            data_to_compress = bwt_transform(msgpack_data, block_size=256*1024)
            bwt_time = time.time() - start
            if verbose:
                print(f"   BWT: {len(msgpack_data):,} → {len(data_to_compress):,} bytes ({bwt_time:.2f}s)")
        else:
            data_to_compress = msgpack_data
        
        # Try to use universal dictionary first (trained from all datasets)
        universal_dict = load_universal_dict()
        
        if universal_dict:
            # Use universal dictionary (better for cross-dataset compression)
            zdict = zstd.ZstdCompressionDict(universal_dict)
            cctx = zstd.ZstdCompressor(level=15, dict_data=zdict)
            compressed = cctx.compress(data_to_compress)
            if verbose:
                print(f"   Using universal Zstd dictionary ({len(universal_dict):,} bytes)")
        elif cd.zstd_dict:
            # Fallback to per-batch trained dictionary
            zdict = zstd.ZstdCompressionDict(cd.zstd_dict)
            cctx = zstd.ZstdCompressor(level=15, dict_data=zdict)
            compressed = cctx.compress(data_to_compress)
            if verbose:
                print(f"   Using per-batch Zstd dictionary ({len(cd.zstd_dict):,} bytes)")
        else:
            # No dictionary available
            compressed = zstd.compress(data_to_compress, level=15)
            if verbose:
                print(f"   Using Zstd without dictionary")
        
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'wb') as f:
            f.write(compressed)
        
        print(f"💾 Saved optimized compressed data to {filepath}")
        print(f"   MessagePack size: {len(msgpack_data):,} bytes ({len(msgpack_data)/1024:.1f} KB)")
        if use_bwt:
            print(f"   After BWT: {len(data_to_compress):,} bytes ({len(data_to_compress)/1024:.1f} KB)")
        print(f"   Final size: {len(compressed):,} bytes ({len(compressed)/1024:.1f} KB)")
        print(f"   Zstd ratio: {len(data_to_compress) / len(compressed):.2f}x")
        print(f"   Overall ratio: {len(msgpack_data) / len(compressed):.2f}x")
    
    @staticmethod
    def load(filepath: Path, use_bwt: bool = False) -> CompressedLog:
        """Load compressed data from file (zstd -> [BWT inverse] -> MessagePack -> varint/RLE decode)
        
        Args:
            filepath: Input file path
            use_bwt: Apply BWT inverse after Zstd decompression (default: False)
                    Set to True if file was compressed with use_bwt=True
        """
        with open(filepath, 'rb') as f:
            compressed_bytes = f.read()
        
        # Try decompression with universal dictionary first
        universal_dict = load_universal_dict()
        
        if universal_dict:
            try:
                zdict = zstd.ZstdCompressionDict(universal_dict)
                dctx = zstd.ZstdDecompressor(dict_data=zdict)
                decompressed = dctx.decompress(compressed_bytes)
            except:
                # Fallback to no dictionary
                decompressed = zstd.decompress(compressed_bytes)
        else:
            # Try new format first (single zstd layer)
            try:
                decompressed = zstd.decompress(compressed_bytes)
            except:
                # Fallback: try old format (zstd -> gzip)
                gzipped = zstd.decompress(compressed_bytes)
                decompressed = gzip.decompress(gzipped)
        
        # Apply BWT inverse if needed
        if use_bwt:
            msgpack_data = bwt_inverse(decompressed)
        else:
            msgpack_data = decompressed
        
        try:
            data = msgpack.unpackb(msgpack_data, raw=False, strict_map_key=False)
        except Exception as e:
            # Debug: Check if msgpack_data is valid
            print(f"DEBUG: msgpack unpack failed")
            print(f"  use_bwt: {use_bwt}")
            print(f"  decompressed size: {len(decompressed)}")
            print(f"  msgpack_data size: {len(msgpack_data)}")
            print(f"  First 50 bytes (hex): {msgpack_data[:50].hex()}")
            raise
        
        compressed = CompressedLog()
        compressed.version = data.get('version', '1.0')
        compressed.templates = data['templates']
        
        # Check version for backwards compatibility
        if compressed.version in ['2.0', '3.0', '3.1', '3.2', '3.3']:
            # v3.0+: Load token pool and Zstd dictionary
            if compressed.version in ['3.0', '3.1', '3.2', '3.3']:
                compressed.token_pool = data.get('token_pool', [])
                compressed.template_token_refs = data.get('template_token_refs', [])
                compressed.zstd_dict = data.get('zstd_dict', None)
                
                # v3.3+: Load Otten's template dictionaries
                if compressed.version == '3.3':
                    compressed.template_dicts_serialized = data.get('template_dicts_serialized', None)
                
                # Reconstruct template patterns from token pool
                if compressed.token_pool and compressed.template_token_refs:
                    # Decode varint-encoded token refs (decode all varints in each bytes)
                    decoded_refs = []
                    for ref_bytes in compressed.template_token_refs:
                        # Decode all varints until end of bytes
                        token_ids = []
                        offset = 0
                        while offset < len(ref_bytes):
                            value, bytes_read = decode_varint(ref_bytes, offset)
                            token_ids.append(value)
                            offset += bytes_read
                        decoded_refs.append(token_ids)
                    
                    # Reconstruct patterns and update templates
                    for i, token_ids in enumerate(decoded_refs):
                        if i < len(compressed.templates):
                            # Reconstruct pattern as list of tokens
                            pattern = [compressed.token_pool[tid] for tid in token_ids]
                            compressed.templates[i]['pattern'] = pattern
            
            # Varint format (v2.0+)
            compressed.timestamps_varint = data.get('timestamps_varint', b'')
            compressed.timestamp_base = data.get('timestamp_base', 0)
            compressed.timestamp_count = data.get('timestamp_count', 0)
            
            # Severities (varint encoding)
            compressed.severities_varint = data.get('severities_varint', b'')
            
            compressed.severity_count = data.get('severity_count', 0)
            compressed.ip_addresses_varint = data.get('ip_addresses_varint', b'')
            compressed.ip_count = data.get('ip_count', 0)
            compressed.messages_varint = data.get('messages_varint', b'')
            compressed.message_count = data.get('message_count', 0)
            
            compressed.severity_list = data.get('severity_list', [])
            compressed.ip_list = data.get('ip_list', [])
            compressed.message_list = data.get('message_list', [])
            
            compressed.log_index_templates_rle = data.get('log_index_templates_rle', b'')
            compressed.log_index_fields_varint = data.get('log_index_fields_varint', b'')
            compressed.log_index_field_counts = data.get('log_index_field_counts', [])
        else:
            # Old format - would need conversion (not implemented for now)
            raise ValueError(f"Unsupported format version {compressed.version}. Please re-compress with new version.")
        
        compressed.original_count = data['original_count']
        compressed.compressed_at = data['compressed_at']
        
        return compressed
    
    def decompress(self, compressed: Optional[CompressedLog] = None, enable_otten: bool = False) -> List[str]:
        """
        Decompress back to original log format
        
        Args:
            compressed: CompressedLog object (uses self.compressed_data if None)
            enable_otten: Enable Otten's preprocessing decoding (default: False)
            
        Returns:
            List of reconstructed log strings
        """
        if compressed is None:
            compressed = self.compressed_data
        
        if not compressed:
            raise ValueError("No compressed data available")
        
        # Initialize Otten preprocessors if needed
        if enable_otten:
            preprocessor = OttenPreprocessor()
            
            # Reconstruct template dictionaries from serialized form
            template_dicts = {}
            if compressed.template_dicts_serialized:
                for template_id, dict_data in compressed.template_dicts_serialized.items():
                    template_dict = TemplateDictionary(template_id)
                    # Restore mappings (convert string keys back to integers)
                    template_dict.word_to_code = {
                        word: int(code) for word, code in dict_data['word_to_code'].items()
                    }
                    template_dict.code_to_word = {
                        int(code): word for code, word in dict_data['code_to_word'].items()
                    }
                    template_dicts[template_id] = template_dict
        
        # Decode varint/RLE data first
        timestamps = []
        if compressed.timestamps_varint:
            zigzag_deltas = decode_varint_list(compressed.timestamps_varint, compressed.timestamp_count)
            timestamps = [zigzag_decode(d) for d in zigzag_deltas]
        
        # Decode severities (varint)
        severities = []
        if compressed.severities_varint:
            severities = decode_varint_list(compressed.severities_varint, compressed.severity_count)
        
        ip_addresses = []
        if compressed.ip_addresses_varint:
            ip_addresses = decode_varint_list(compressed.ip_addresses_varint, compressed.ip_count)
        
        messages = []
        if compressed.messages_varint:
            messages = decode_varint_list(compressed.messages_varint, compressed.message_count)
        
        # Decode RLE template IDs (with pattern support) and apply zigzag decode
        zigzag_template_ids = decode_rle_v2(compressed.log_index_templates_rle, compressed.original_count)
        template_ids = [zigzag_decode(tid) for tid in zigzag_template_ids]
        
        # Reconstruct field indices per log
        all_field_indices = decode_varint_list(compressed.log_index_fields_varint, sum(compressed.log_index_field_counts))
        log_index = []
        offset = 0
        for count in compressed.log_index_field_counts:
            field_indices = all_field_indices[offset:offset + count]
            log_index.append(field_indices)
            offset += count
        
        logs = []
        current_ts = compressed.timestamp_base if compressed.timestamp_base else 0
        
        for log_idx, (template_idx, field_indices) in enumerate(zip(template_ids, log_index)):
            if template_idx == -1:
                # Unmatched log - stored as full message
                msg_id = messages[field_indices[0]]
                logs.append(compressed.message_list[msg_id])
                continue
            
            # Get template
            template_data = compressed.templates[template_idx]
            pattern = template_data['pattern']
            
            # Reconstruct fields by iterating through pattern and field_indices in parallel
            # field_indices contains one entry per extracted field (in order of extraction)
            reconstructed = []
            field_idx = 0
            
            for part in pattern:
                if part.startswith('[') and part.endswith(']'):
                    # Variable field - get from decoded data
                    if field_idx >= len(field_indices):
                        # No more field data - skip this placeholder or use empty
                        field_idx += 1
                        continue
                        
                    field_type = part[1:-1].upper()
                    actual_idx = field_indices[field_idx]
                    
                    if field_type == 'TIMESTAMP':
                        if actual_idx < len(timestamps):
                            delta = timestamps[actual_idx]
                            current_ts += delta
                            # Otten decoding: timestamp is already in epoch seconds
                            if enable_otten:
                                # Format as human-readable
                                from datetime import datetime
                                dt = datetime.fromtimestamp(current_ts)
                                reconstructed.append(dt.strftime('%Y-%m-%d %H:%M:%S'))
                            else:
                                reconstructed.append(str(current_ts))
                    elif field_type in ('SEVERITY', 'STATUS'):
                        if actual_idx < len(severities):
                            sev_id = severities[actual_idx]
                            if sev_id < len(compressed.severity_list):
                                reconstructed.append(compressed.severity_list[sev_id])
                    elif field_type in ('IP_ADDRESS', 'HOST'):
                        if actual_idx < len(ip_addresses):
                            ip_id = ip_addresses[actual_idx]
                            if ip_id < len(compressed.ip_list):
                                ip_value = compressed.ip_list[ip_id]
                                # Otten decoding: IP might be binary (bytes) or string
                                if enable_otten and isinstance(ip_value, bytes):
                                    decoded_ip = preprocessor.decode_ip_binary(ip_value)
                                    reconstructed.append(decoded_ip)
                                else:
                                    reconstructed.append(ip_value)
                    else:  # MESSAGE
                        if actual_idx < len(messages):
                            msg_id = messages[actual_idx]
                            if msg_id < len(compressed.message_list):
                                msg_value = compressed.message_list[msg_id]
                                
                                # Otten decoding: Message might be encoded with template dictionary
                                if enable_otten and template_data.get('id') in template_dicts:
                                    template_dict = template_dicts[template_data['id']]
                                    if isinstance(msg_value, bytes):
                                        decoded_msg = template_dict.decode_message(msg_value)
                                        reconstructed.append(decoded_msg)
                                    else:
                                        # Already decoded or not encoded
                                        reconstructed.append(msg_value)
                                else:
                                    reconstructed.append(msg_value)
                    
                    field_idx += 1
                else:
                    # Constant part - use as-is
                    reconstructed.append(part)
            
            logs.append(' '.join(str(part) for part in reconstructed))
        
        return logs


# CLI for compression benchmarking
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Compress logs with semantic awareness")
    parser.add_argument('--input', required=True, help='Input log file')
    parser.add_argument('--output', required=True, help='Output compressed file')
    parser.add_argument('--sample-size', type=int, default=None, help='Number of logs to compress')
    parser.add_argument('--measure', action='store_true', help='Compare with gzip')
    
    args = parser.parse_args()
    
    # Load logs
    print(f"📂 Loading logs from {args.input}")
    logs = []
    with open(args.input, 'r', encoding='utf-8', errors='ignore') as f:
        for i, line in enumerate(f):
            if args.sample_size and i >= args.sample_size:
                break
            line = line.strip()
            if line:
                logs.append(line)
    
    print(f"✓ Loaded {len(logs)} logs\n")
    
    # Compress
    compressor = SemanticCompressor(min_support=5)
    compressed, stats = compressor.compress(logs, verbose=True)
    
    # Save
    output_path = Path(args.output)
    compressor.save(output_path)
    
    # Compare with gzip if requested
    if args.measure:
        print(f"\n📊 Comparison with gzip:")
        import gzip
        
        original_data = '\n'.join(logs).encode('utf-8')
        gzipped = gzip.compress(original_data, compresslevel=9)
        
        actual_file_size = output_path.stat().st_size
        
        print(f"  • Original: {len(original_data):,} bytes")
        print(f"  • LogSim:   {actual_file_size:,} bytes ({len(original_data)/actual_file_size:.2f}x)")
        print(f"  • gzip -9:  {len(gzipped):,} bytes ({len(original_data)/len(gzipped):.2f}x)")
        print(f"  • LogSim advantage: {len(gzipped)/actual_file_size:.2f}x better than gzip")
