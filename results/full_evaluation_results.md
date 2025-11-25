# LogSim Full Evaluation Results

**Date**: 2025-11-25 23:32:19

**Total Datasets**: 4
**Total Logs**: 359,965
**Total Size**: 36.52 MB

## Summary Table

| Dataset | Logs | Original | Compressed | Ratio | vs gzip | Speed |
|---------|------|----------|------------|-------|---------|-------|
| Apache | 51,978 | 4.75 MB | 584.24 KB | 8.32x | 39.2% | 1.26 MB/s |
| HealthApp | 212,394 | 19.53 MB | 1870.52 KB | 10.69x | 97.9% | 2.57 MB/s |
| Proxifier | 21,320 | 2.40 MB | 196.98 KB | 12.49x | 79.6% | 1.29 MB/s |
| Zookeeper | 74,273 | 9.84 MB | 609.86 KB | 16.53x | 63.9% | 1.27 MB/s |
| **AVERAGE** | 359,965 | 36.52 MB | 3261.60 KB | 11.47x | 79.9% | — |

## Verified Production Pipeline

### Stage 1: Tokenization
- **Algorithm**: FSM-based tokenizer
- **File**: `logsim/tokenizer.py`
- **Method**: Context-aware boundary detection

### Stage 2: Template Extraction
- **Algorithm**: Custom log alignment (NOT Drain3)
- **File**: `logsim/template_generator.py`
- **Method**: Position-by-position alignment across logs
- **Result**: 77 templates across all datasets

### Stage 3: Semantic Classification
- **Algorithm**: Pattern-based matching with confidence scoring
- **File**: `logsim/semantic_types.py`
- **Types**: TIMESTAMP, SEVERITY, IP_ADDRESS, HOST, PROCESS_ID, MESSAGE, etc.

### Stage 4: Columnar Encoding
1. **Delta Encoding**: Timestamps (store differences)
2. **Zigzag Encoding**: Signed integers
3. **Varint Encoding**: Protocol Buffer style (`varint.py`)
4. **Dictionary Encoding**: Low-cardinality fields (severity, status)
5. **RLE v2**: Pattern detection for repeated values
6. **Token Pool**: Global template token deduplication

### Stage 5: Binary Serialization & Compression
1. **MessagePack**: Binary serialization (`msgpack.packb`)
2. **Zstandard**: Level 15 compression (`zstd.compress`)

### Stage 6: Query Engine
- **File**: `logsim/query_engine.py`
- **Method**: Selective decompression (columnar field access)
- **Benefit**: Query without full decompression

## Per-Dataset Details

### Apache

- **Logs**: 51,978
- **Original Size**: 4,975,683 bytes (4.75 MB)
- **Compressed Size**: 598,262 bytes (584.24 KB)
- **Compression Ratio**: 8.32x
- **vs gzip-9**: 39.2%
- **Compression Time**: 3.774s (1.26 MB/s)
- **Decompression Time**: 0.441s
- **Templates**: 19

**Techniques Applied**:
- Tokenization: FSM-based (logsim/tokenizer.py)
- Template Extraction: Custom log alignment algorithm (19 templates)
- Token Pool: Global deduplication (64 unique tokens)
- Delta Encoding: Timestamps (51978 values)
- Zigzag Encoding: Signed integers (varint.py)
- Varint Encoding: Protocol Buffer style (varint.py)
- Dictionary Encoding: Low-cardinality fields (severity, IP, etc.)
- RLE v2: Pattern detection (log_index: 22500 bytes)
- MessagePack: Binary serialization
- Zstandard: Level 15 post-compression

### HealthApp

- **Logs**: 212,394
- **Original Size**: 20,483,278 bytes (19.53 MB)
- **Compressed Size**: 1,915,410 bytes (1870.52 KB)
- **Compression Ratio**: 10.69x
- **vs gzip-9**: 97.9%
- **Compression Time**: 7.603s (2.57 MB/s)
- **Decompression Time**: 1.261s
- **Templates**: 2

**Techniques Applied**:
- Tokenization: FSM-based (logsim/tokenizer.py)
- Template Extraction: Custom log alignment algorithm (2 templates)
- Token Pool: Global deduplication (5 unique tokens)
- Delta Encoding: Timestamps (212394 values)
- Zigzag Encoding: Signed integers (varint.py)
- Varint Encoding: Protocol Buffer style (varint.py)
- Dictionary Encoding: Low-cardinality fields (severity, IP, etc.)
- RLE v2: Pattern detection (log_index: 34 bytes)
- MessagePack: Binary serialization
- Zstandard: Level 15 post-compression

### Proxifier

- **Logs**: 21,320
- **Original Size**: 2,519,085 bytes (2.40 MB)
- **Compressed Size**: 201,711 bytes (196.98 KB)
- **Compression Ratio**: 12.49x
- **vs gzip-9**: 79.6%
- **Compression Time**: 1.861s (1.29 MB/s)
- **Decompression Time**: 0.171s
- **Templates**: 26

**Techniques Applied**:
- Tokenization: FSM-based (logsim/tokenizer.py)
- Template Extraction: Custom log alignment algorithm (26 templates)
- Token Pool: Global deduplication (47 unique tokens)
- Delta Encoding: Timestamps (21320 values)
- Zigzag Encoding: Signed integers (varint.py)
- Varint Encoding: Protocol Buffer style (varint.py)
- Dictionary Encoding: Low-cardinality fields (severity, IP, etc.)
- RLE v2: Pattern detection (log_index: 15936 bytes)
- MessagePack: Binary serialization
- Zstandard: Level 15 post-compression

### Zookeeper

- **Logs**: 74,273
- **Original Size**: 10,319,891 bytes (9.84 MB)
- **Compressed Size**: 624,500 bytes (609.86 KB)
- **Compression Ratio**: 16.53x
- **vs gzip-9**: 63.9%
- **Compression Time**: 7.742s (1.27 MB/s)
- **Decompression Time**: 0.585s
- **Templates**: 30

**Techniques Applied**:
- Tokenization: FSM-based (logsim/tokenizer.py)
- Template Extraction: Custom log alignment algorithm (30 templates)
- Token Pool: Global deduplication (104 unique tokens)
- Delta Encoding: Timestamps (74273 values)
- Zigzag Encoding: Signed integers (varint.py)
- Varint Encoding: Protocol Buffer style (varint.py)
- Dictionary Encoding: Low-cardinality fields (severity, IP, etc.)
- RLE v2: Pattern detection (log_index: 113511 bytes)
- MessagePack: Binary serialization
- Zstandard: Level 15 post-compression

