# LogPress: 

## Implementation Summary

### 1. Compression Pipeline: 6-Stage Process

LogPress transforms raw log text into compressed structured data using six stages:

**Stage 1: Tokenization** - Split raw log strings into tokens and separators using regex patterns. Each log becomes a sequence of meaningful units.

**Stage 2: Classification** - Assign semantic types to each token using pattern matching:
   - `TYPE_IP`: IP addresses (IPv4)
   - `TYPE_TS`: Timestamps
   - `TYPE_PATH`: File paths and URLs
   - `TYPE_INT`: Integers
   - `TYPE_HEX`: Hexadecimal values
   - `TYPE_UUID`: UUIDs
   - `TYPE_MAC`: MAC addresses
   - `TYPE_RAW`: Unclassified strings

**Stage 3: Template Extraction** - Identify structural patterns by extracting templates from classified logs. Variable tokens (IP, timestamp, integers, etc.) become placeholders, constants stay fixed. Templates are stored in a dictionary for better compressibility.

**Stage 4: Semantic Encoding** - Convert typed values to native representations:
   - IP addresses → 32-bit integers (for example `192.168.1.1` → `3232235777`)
   - Timestamps → original strings (kept for lossless reconstruction)
   - Paths & raw strings → dictionary-based encoding (deduplication)
   - Integers and hex values → native integer types

**Stage 5: Serialization (msgpack)** - Convert structured Python objects (templates, values, separators, dictionaries) into a binary bytes. This step is necessary because compression algorithms works on bytes, not complex data structures.

**Stage 6: Compression (zstd)** - Apply Zstandard compression (level 22) to the serialized byte stream from msgpack, producing the final `.logpress` file.

**For Comparison We have:**
- **Baselines (gzip/bzip2/lzma/zstd)**: Compress raw text directly → `text.encode() → compress()`
- **LogPress Full Pipeline**: All 6 stages → `tokenize → classify → extract_templates → semantic encode → serialize → compress`
- **LogPress Compress Only**: Only Stage 6 for fair comparison with baselines

### 2. Decompression Process

To decompressed logs, LogPress performs reverse compression logic:

1. **Load & Decompress**: Read `.logpress` file → `zstd.decompress()` → byte stream
2. **Deserialize**: `msgpack.unpackb()` → structured Python objects (template_ids, values, separators, dictionaries)
3. **No reconstruction yet**: Data remains in structured format for efficient querying

### 3. Query System (Lazy Reconstruction)

LogPress enables efficient querying WITHOUT decompressing all logs:

**Query Process:**
1. **Load structured data** (steps 1-2 above) - data is already in memory in structured form
2. **Filter on structured data** (no full reconstruction):
   - **By Severity**: Search templates containing severity keywords (for example "ERROR") → filter by matching template IDs
   - **By IP Address**: Convert query IP to integer → match values where `type==TYPE_IP` and `value==query_ip_int`
   - **By Template Keyword**: Search templates for keyword → filter by matching template IDs
   - **By Template ID**: Direct filter on template_ids array
3. **Lazy Reconstruction**: Only reconstruct logs matching the filter criteria (not all logs)
4. **Semantic Decoding**: Convert native types back to strings:
   - IP integer → dotted notation (for example `3232235777` → `192.168.1.1`)
   - Dictionary IDs → original path/string values
   - Integers → string representation
5. **Return Results**: Log indices or reconstructed log strings

Querying operates on compressed structured data (template IDs, typed values) rather than raw text, enabling fast filtering before expensive reconstruction.

**Example Query Flow:**
```
Query: "Find all logs with IP 192.168.1.1"
1. Convert: "192.168.1.1" → 3232235777 (integer)
2. Filter: Scan values array for (TYPE_IP, 3232235777) tuples
3. Reconstruct: Only matching logs are rebuilt from templates+values+separators
4. Return: Reconstructed log strings or indices
```

This approach is much faster than:
- Decompressing entire log file
- Searching through full text
- Then filtering matches