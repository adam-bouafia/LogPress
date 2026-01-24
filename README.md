# LogPress: Semantic Log Compression System

A log compression system that achieves **up to 39x compression ratios** using semantic understanding and structure-aware encoding.

## Overview

LogPress transforms unstructured log text into highly compressed structured data by:
1. **Understanding semantic types** (IPs, timestamps, paths, UUIDs, hostnames, etc.)
2. **Extracting structural patterns** (templates)
3. **Encoding values in their native types** (IP as 32-bit int, not string)
4. **Enabling compressed querying using Lazy Reconstruction** (filter before decompression)

### Performance Results (2.4M Logs, 10 Datasets)

| Metric | Result |
|--------|--------|
| **Total Logs Processed** | 2,394,626 |
| **Reconstruction Accuracy** | **100.00%** (all logs verified) |
| **Best Compression** | 39.84x (Zookeeper) |
| **Overall Compression** | 22.33x |
| **Query Performance** | 21-111ms per query |

### Compression Comparison

| Dataset | Gzip | Bzip2 | LZMA | Zstd | LogZip | LogReducer | **LogPress** |
|---------|------|-------|------|------|--------|------------|-------------|
| BGL | 13.67x | 16.04x | 23.16x | 22.72x | 13.67x | 18.18x | **22.33x** |
| Apache | 21.17x | 29.23x | 28.48x | 29.01x | 20.77x | 21.76x | **23.51x** |
| Hadoop | 14.74x | 22.51x | 25.67x | 29.56x | 14.22x | 19.38x | **25.67x** |
| HealthApp | 10.86x | 13.67x | 15.63x | 16.26x | 10.53x | 11.56x | **11.81x** |
| Linux | 11.24x | 14.73x | 20.02x | 19.55x | 11.24x | 15.65x | **14.24x** |
| Mac | 11.66x | 17.98x | 24.33x | 26.67x | 11.24x | 18.62x | **19.86x** |
| Openstack | 12.17x | 15.34x | 15.76x | 16.36x | 11.77x | 15.05x | **13.27x** |
| Proxifier | 15.67x | 23.55x | 21.04x | 20.96x | 15.67x | 20.30x | **15.39x** |
| SSH | 16.74x | 22.62x | 20.71x | 24.44x | 25.89x | 23.23x | **24.06x** |
| Zookeeper | 25.89x | 36.10x | 29.85x | 38.71x | 20.28x | 22.55x | **39.84x** |
| **Overall** | 13.90x | 17.86x | 20.74x | 22.04x | 13.67x | 18.63x | **22.33x** |

**Note**: LogPress provides queryable compressed data using Lazy Reconstruction - unlike raw compression methods that require full decompression for any query. LogPress outperforms Gzip by 60.6%, LogZip by 63.3%, and LogReducer by 19.9%.

### Log-Specific Methods Comparison

| Method | Implementation | Approach | Overall Ratio | Query Support |
|--------|---------------|----------|---------------|---------------|
| **LogZip** | Python (Drain3) | Template extraction + Gzip | 13.67x | No |
| **LogReducer** | C++ (GCC 14.2.0) | Pattern mining + entropy encoding | 18.63x | No |
| **LogPress** | Python (Jupyter) | Semantic typing + MessagePack + Zstd | **22.33x** | **Yes** |

- **LogZip** uses Drain3 for template extraction but achieves ratios nearly identical to raw Gzip, indicating that template extraction overhead cancels out compression gains without semantic encoding.
- **LogReducer** is implemented in C++ and achieves faster processing times, but its pattern mining approach yields lower compression ratios than LogPress.
- **LogPress** combines semantic classification with type-specific encoding, achieving the highest compression ratio among log-specific methods while also enabling queries on compressed data.

---

## 1. Compression Pipeline: 6-Stage Process

LogPress transforms raw log text into compressed structured data through six stages:

### Stage 1: Tokenization
Split raw log strings into tokens and separators using regex patterns.

**Example:**
```
Input:  "2024-01-01 10:05:25 192.168.1.1 ERROR Connection timeout"
Tokens: ["2024-01-01", "10:05:25", "192.168.1.1", "ERROR", "Connection", "timeout"]
Seps:   ["", " ", " ", " ", " ", " ", ""]
```

### Stage 2: Classification
Assign semantic types to each token using pattern matching (20 types with priority-based matching):

**20 Semantic Types:**

| Type | Code | Description | Pattern Priority |
|------|------|-------------|------------------|
| `TIMESTAMP` | 0 | Time/date patterns | 97-102 |
| `SEVERITY` | 1 | DEBUG, INFO, WARN, ERROR, etc. | 85 |
| `IP_ADDRESS` | 2 | IPv4 addresses (with optional port) | 90 |
| `PORT` | 3 | Port numbers | 75 |
| `PROCESS_ID` | 4 | Process IDs `[pid]` | 75 |
| `PATH` | 5 | File paths and URLs | 77-78 |
| `HEX` | 6 | Hexadecimal values | 69-70 |
| `UUID` | 7 | UUID identifiers | 95 |
| `MAC_ADDRESS` | 8 | MAC addresses | 95 |
| `NUMBER` | 9 | Generic numbers, floats, versions | 59-74 |
| `WORD` | 10 | Generic words | 50-51 |
| `WORD_ID` | 11 | Dictionary-encoded words | - |
| `OTHER` | 12 | Unclassified tokens (fallback) | 0 |
| `HOSTNAME` | 13 | Server/host identifiers | 82 |
| `USERNAME` | 14 | User/account names | 81-82 |
| `ERROR_CODE` | 15 | Error codes (E0001, TIMEOUT) | 80 |
| `REQUEST_ID` | 16 | Request/transaction IDs | 80 |
| `SEPARATOR` | 17 | Punctuation `:[]=-\|{}` | 105 |
| `MODULE` | 18 | Package names (a.b.c format) | 91-92 |
| `COMPONENT` | 19 | Service/module names | - |

**Classification Process:**
1. Patterns sorted by priority (highest first)
2. First matching pattern wins
3. Fallback to `OTHER` if no match

### Stage 3: Template Extraction
Identify structural patterns by extracting templates from classified logs. Variable tokens (IP, timestamp, integers, etc.) become placeholders `<*TYPE*>`, while constants stay fixed.

**Example:**
```
Log 1: "2024-01-01 10:05:25 192.168.1.1 ERROR Connection timeout"
Log 2: "2024-01-01 10:05:26 192.168.1.2 ERROR Connection timeout"

Template: "<*TIMESTAMP*> <*TIMESTAMP*> <*IP*> ERROR Connection timeout"
Values 1: [(TS, "2024-01-01"), (TS, "10:05:25"), (IP, 192.168.1.1)]
Values 2: [(TS, "2024-01-01"), (TS, "10:05:26"), (IP, 192.168.1.2)]
```

Templates are frequency-sorted and dictionary-encoded for optimal compression.

### Stage 4: Semantic Encoding
Convert typed values to native representations for space efficiency:

| Type | Raw String | Encoded Format | Savings |
|------|-----------|----------------|---------|
| IP Address | `"192.168.1.1"` (13 bytes) | `3232235777` (4 bytes int) | 69% |
| Timestamp | `"2024-01-01 10:05:25"` | Original string | 0% |
| Integer | `"12345"` | `12345` (int) | 60% |
| Hex | `"0xDEADBEEF"` | `3735928559` (int) | 70% |
| Path | `"/var/log/app.log"` | Dictionary ID | 75% |
| MAC | `"00:1A:2B:3C:4D:5E"` | `113729277278` (int) | 66% |

**Key optimizations:**
- IP addresses to 32-bit integers via bit-shifting
- Paths & repeated strings to dictionary encoding (deduplication)
- Hex values to native integers (preserving original format for reconstruction)
- Leading zeros preserved (for example "09" stays "09" not "9")

### Stage 5: Serialization (msgpack)
Convert structured Python objects (templates, values, separators, dictionaries) into binary bytes. This step is necessary because compression algorithms work on bytes, not complex data structures.

```python
data = {
    "template_ids": [0, 0, 1, 0, 2, ...],        # Template for each log
    "values": [                                   # Encoded values per log
        [(TYPE_IP, 3232235777), (TYPE_TS, "10:05:25")],
        [(TYPE_IP, 3232235778), (TYPE_TS, "10:05:26")],
        ...
    ],
    "templates": {0: ["<*IP*>", "ERROR", "..."], ...},
    "separators": [[" ", " ", ...], ...],
    "id_to_path": {0: "/var/log/app.log", ...}
}
msgpack.packb(data) to bytes
```

### Stage 6: Compression (zstd)
Apply Zstandard compression (level 22) to the serialized byte stream, producing the final `.logpress` file.

```python
zstd.compress(msgpack_bytes, level=22) to .logpress file
```

**Why Zstd?**
- Excellent compression ratios (comparable to LZMA)
- 5-10x faster decompression than LZMA/bzip2
- Good balance of speed and compression

### Pipeline Timing Breakdown

From processing 2.4M logs across 10 datasets (total: 2263.91s):

| Stage | Time | Percentage |
|-------|------|------------|
| Tokenization | 203.09s | 9.0% |
| Classification | 499.47s | 22.1% |
| Template Extraction | 20.25s | 0.9% |
| Semantic Encoding | 663.41s | 29.3% |
| Serialization | 678.90s | 30.0% |
| Compression | 198.54s | 8.8% |

**Key Insight**: Compression (Zstd) is only 8.8% of total time. The semantic processing dominates runtime but enables both high compression ratios and queryability.

### Baseline Methods

LogPress was compared against:

**Raw Compression:**
- **Gzip** (level 9): Fast, widely used, 13.90x overall
- **Bzip2** (level 9): Better ratio than Gzip, 17.86x overall
- **LZMA** (preset 9): High compression, slow, 20.74x overall
- **Zstandard** (level 22): Best raw compression, 22.04x overall

**Log-Specific Methods:**
- **LogZip** (Drain3 0.9.10): Template extraction followed by Gzip compression
- **LogReducer** (THULR C++): Pattern mining with entropy encoding

---

## 2. Decompression & Reconstruction

LogPress enables two modes of operation:

### Quick Decompression (For Querying)
Decompress to structured format WITHOUT full reconstruction:

```python
# 1. Load & Decompress
compressed = read_file("dataset.logpress")
packed = zstd.decompress(compressed)
data = msgpack.unpackb(packed)

# 2. Data is now in structured format
# data["template_ids"] = [0, 0, 1, ...]
# data["values"] = [[(TYPE_IP, 3232235777), ...], ...]
# Ready for fast filtering!
```

### Full Reconstruction (Lossless)
Rebuild original log strings when needed:

```python
def reconstruct_log(template, values, separators, dictionaries):
    decoded_tokens = []
    
    # Replace placeholders with decoded values
    for i, token in enumerate(template):
        if token.startswith("<*") and token.endswith("*>"):
            # Decode semantic value
            value_type, value_data = values[i]
            if value_type == TYPE_IP:
                decoded = int_to_ip(value_data)  # 3232235777 to "192.168.1.1"
            elif value_type == TYPE_PATH:
                decoded = dictionaries["id_to_path"][value_data]
            # ... other types
            decoded_tokens.append(decoded)
        else:
            decoded_tokens.append(token)  # Constant token
    
    # Interleave separators
    result = []
    for i, token in enumerate(decoded_tokens):
        if i < len(separators):
            result.append(separators[i])
        result.append(token)
    if len(separators) > len(decoded_tokens):
        result.append(separators[len(decoded_tokens)])
    
    return "".join(result)
```

---

## 3. Query System (Lazy Reconstruction)

LogPress enables querying WITHOUT decompressing all logs:

**Query Process:**
1. **Load structured data** (steps 1-2 above) - data is already in memory in structured form
2. **Filter on structured data** (no full reconstruction):
   - **By Severity**: Search templates containing severity keywords (for example "ERROR") to filter by matching template IDs
   - **By IP Address**: Convert query IP to integer to match values where `type==TYPE_IP` and `value==query_ip_int`
   - **By Template Keyword**: Search templates for keyword to filter by matching template IDs
   - **By Template ID**: Direct filter on template_ids array
3. **Lazy Reconstruction**: Only reconstruct logs matching the filter criteria (not all logs)
4. **Semantic Decoding**: Convert native types back to strings:
   - IP integer to dotted notation (for example `3232235777` to `192.168.1.1`)
   - Dictionary IDs to original path/string values
   - Integers to string representation
5. **Return Results**: Log indices or reconstructed log strings

### Query Performance Results

| Query Type | Avg Time | Description |
|------------|----------|-------------|
| Severity | 98.25ms | Filter by ERROR, WARN, etc. |
| Keyword | 45.19ms | Search templates for keyword |
| Template ID | 21.14ms | Direct ID lookup |
| IP Address | 110.56ms | Convert IP to int, filter values |
| Reconstruct (100 logs) | 20.64ms | Lazy reconstruction |

Querying operates on compressed structured data (template IDs, typed values) rather than raw text, enabling fast filtering before expensive reconstruction.

**Example Query Flow:**
```
Query: "Find all logs with IP 192.168.1.1"
1. Convert: "192.168.1.1" to 3232235777 (integer)
2. Filter: Scan values array for (TYPE_IP, 3232235777) tuples
3. Reconstruct: Only matching logs are rebuilt from templates+values+separators
4. Return: Reconstructed log strings or indices
```

This approach is much faster than:
- Decompressing entire log file
- Searching through full text
- Then filtering matches

---

## 4. Datasets Evaluated

LogPress was evaluated on 10 log datasets from the [Loghub](https://github.com/logpai/loghub) benchmark:

| Dataset | Logs | Avg Length | Unique Templates | Description |
|---------|------|------------|------------------|-------------|
| BGL | 826,284 | 139 chars | ~500 | BlueGene/L supercomputer |
| Apache | 51,978 | 94 chars | ~50 | Apache web server |
| Hadoop | 179,993 | 176 chars | ~300 | Hadoop distributed system |
| HealthApp | 253,395 | 90 chars | ~200 | Android health app |
| Linux | 25,567 | 90 chars | ~100 | Linux syslog |
| Mac | 117,283 | 141 chars | ~400 | macOS system logs |
| Openstack | 189,386 | 294 chars | ~50 | OpenStack cloud |
| Proxifier | 21,320 | 117 chars | ~20 | Windows proxy |
| SSH | 655,147 | 110 chars | ~50 | SSH authentication |
| Zookeeper | 74,273 | 138 chars | ~100 | Apache Zookeeper |

**Total**: 2,394,626 logs processed with **100% lossless reconstruction**.

---

## 5. File Structure

```
LogPress/
├── LogPress.ipynb          # Main implementation notebook
├── README.md               # This documentation
├── compressed/             # Output .logpress files
│   ├── BGL.logpress
│   ├── Apache.logpress
│   └── ...
├── datasets/               # Input log files (Loghub format)
├── tables/                 # Analysis results (CSV)
│   ├── compression_ratios.csv
│   ├── compression_times.csv
│   ├── verification_results.csv
│   └── ...
├── plots/                  # Visualization outputs
└── diagrams/               # Architecture diagrams
```

---

## 6. Usage

### Compress Logs
```python
# Load and compress
from logpress import compress_dataset

compressed = compress_dataset("my_logs", logs, classified_logs, templates, template_dict, separators)

# Save to .logpress file
with open("output.logpress", "wb") as f:
    f.write(zstd.compress(msgpack.packb(compressed)))
```

### Decompress and Query
```python
# Load compressed data
with open("output.logpress", "rb") as f:
    data = msgpack.unpackb(zstd.decompress(f.read()))

# Query by severity (no full reconstruction)
error_logs = [i for i, tid in enumerate(data["template_ids"]) 
              if "ERROR" in data["templates"][tid]]

# Reconstruct only matching logs
for idx in error_logs[:10]:
    log = reconstruct_log(data["templates"][data["template_ids"][idx]], 
                          data["values"][idx], 
                          data["separators"][idx])
    print(log)
```

---
