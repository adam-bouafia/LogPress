# Copilot Instructions: Log Schema Extraction & Compression System

## Project Overview

This is a **Master's thesis research project** focused on automatic schema extraction from unstructured system logs and semantic-driven compression. The system uses **constraint-based parsing** (not ML models) to discover implicit log schemas and compress logs while maintaining queryability.

**Core Architecture**: Raw Logs → Tokenizer → Field Detection → Semantic Classification → Schema Extraction → Compression → Queryable Storage

## Dataset Structure

The `datasets/` directory contains 5 real-world log sources (~497K total log entries):

### Apache (52K lines) - Web Server Logs
```
[Thu Jun 09 06:07:04 2005] [notice] LDAP: Built with OpenLDAP LDAP SDK
[Thu Jun 09 06:07:05 2005] [error] env.createBean2(): Factory error creating channel.jni:jni
[Thu Jun 09 06:07:19 2005] [notice] Apache/2.0.49 (Fedora) configured -- resuming normal operations
```
**Schema**: `[TIMESTAMP] [SEVERITY] MESSAGE`

### HealthApp (212K lines) - Android Health Tracking
```
20171223-22:15:29:606|Step_LSC|30002312|onStandStepChanged 3579
20171223-22:15:29:633|Step_StandReportReceiver|30002312|onReceive action: android.intent.action.SCREEN_ON
20171223-22:15:29:635|Step_StandStepCounter|30002312|flush sensor data
```
**Schema**: `TIMESTAMP|COMPONENT|PROCESS_ID|MESSAGE`

### Zookeeper (74K lines) - Distributed Coordination Service
```
2015-07-29 17:41:41,536 - INFO  [main:QuorumPeerConfig@101] - Reading configuration from: /etc/zookeeper/conf/zoo.cfg
2015-07-29 17:41:41,609 - INFO  [main:NIOServerCnxnFactory@94] - binding to port 0.0.0.0/0.0.0.0:2181
2015-07-29 17:41:41,733 - WARN  [WorkerSender[myid=1]:QuorumCnxManager@368] - Cannot open channel to 2 at election address /10.10.34.12:3888
```
**Schema**: `TIMESTAMP - SEVERITY [THREAD:CLASS@LINE] - MESSAGE`

### OpenStack (137K lines) - Cloud Infrastructure
```
nova-compute.log.1.2017-05-17_12:02:35 2017-05-16 15:15:54.960 2931 INFO nova.compute.manager [req-7a738b84-...] [instance: 0f079bdd-...] Took 0.54 seconds to deallocate network
nova-api.log.1.2017-05-17_12:02:19 2017-05-16 15:16:01.511 25749 INFO nova.osapi_compute.wsgi.server [req-378bb69b-...] 10.11.10.1 "GET /v2/54fadb412c4e40cdbaed9335e4c35a9e/flavors HTTP/1.1" status: 200
```
**Schema**: `FILENAME TIMESTAMP PROCESS_ID SEVERITY MODULE [REQUEST_ID] MESSAGE`

### Proxifier (21K lines) - Network Proxy Logs
```
[10.30 16:49:06] chrome.exe - proxy.cse.cuhk.edu.hk:5070 close, 0 bytes sent, 0 bytes received, lifetime <1 sec
[10.30 16:49:06] chrome.exe - proxy.cse.cuhk.edu.hk:5070 close, 0 bytes sent, 0 bytes received, lifetime <1 sec
```
**Schema**: `[TIMESTAMP] PROCESS - HOST:PORT ACTION, BYTES_SENT, BYTES_RECEIVED, LIFETIME`

**Log Format Diversity**: Each source has different timestamp formats, field separators, severity levels, and semantic field types—this diversity is intentional for testing schema extraction robustness.

## Development Phases (PROJECT.md Roadmap)

The thesis follows a **4-phase structure** over 26 weeks:

1. **Phase 1 (Weeks 1-4)**: Manual ground truth annotation of 1,000-2,000 logs with semantic field taxonomy
2. **Phase 2 (Weeks 5-16)**: Build schema extraction engine with 5-step pipeline (tokenizer → semantic types → field grouping → template generation → evolution tracking)
3. **Phase 3 (Weeks 17-24)**: Implement category-aware compression with queryable indexes (target: 8-30x compression ratio)
4. **Phase 4 (Weeks 25-26)**: Thesis writing and polish

## Key Implementation Principles

### Semantic Type Recognition

Use **pattern-based matching** with confidence scoring, not ML. Core semantic types:
- `TIMESTAMP`: Multiple formats (ISO, Unix epoch, syslog-style)
- `IP_ADDRESS`: IPv4/IPv6 patterns
- `USER_ID`, `PROCESS_ID`: Context-aware extraction
- `ERROR_CODE`, `METRIC`, `STATUS`: Domain-specific patterns
- `MESSAGE`: Free-text after structured fields

**Pattern Library Location**: Will be in `semantic_types.py` with regex-based matchers and scoring functions.

### Schema Template Generation

Use **log alignment algorithm**: Identify constant tokens vs. variable positions across multiple logs. Example:

```
Raw logs:
  "[Thu Jun 09 06:07:04 2005] [notice] LDAP: Built with OpenLDAP"
  "[Thu Jun 09 06:07:05 2005] [notice] LDAP: SSL support unavailable"
  
Extracted template:
  "[TIMESTAMP] [SEVERITY] LDAP: [MESSAGE]"
```

### Compression Strategy

**Category-aware compression** based on extracted schema:
- Timestamps: Delta encoding (store differences, not absolute values)
- Low-cardinality fields (severity, status): Dictionary encoding
- Metrics: Time-series compression (Gorilla algorithm)
- Stack traces: Reference tracking (store once, reuse pointer)

**Queryable Index**: Store fields in columnar format for fast range/equality queries without full decompression.

## Code Organization (Planned)

```
logsim/
├── tokenizer.py           # Smart log tokenization (handles varied formats)
├── semantic_types.py      # Pattern library with confidence scoring
├── field_grouping.py      # Identify related fields (ip+port, user+action)
├── template_generator.py  # Log alignment & schema extraction
├── schema_versioner.py    # Track schema evolution over time
├── compressor.py          # Category-aware compression codecs
├── query_engine.py        # Query execution on compressed data
├── evaluator.py           # Accuracy metrics vs ground truth
└── tests/                 # Unit tests for each component
```

## Development Workflow

### When Adding New Semantic Type Patterns

1. Add pattern to `semantic_types.py` with examples from actual dataset logs
2. Include confidence scoring (0.0-1.0) based on pattern specificity
3. Test against all 5 log sources to avoid overfitting
4. Document which datasets the pattern applies to

### When Implementing Compression Codecs

1. Extract schema first using template generator
2. Choose codec based on field type (temporal, categorical, numeric, text)
3. Measure compression ratio AND query latency (both matter)
4. Target: >10x compression with <2x query slowdown

### Testing Strategy

- **Ground Truth Validation**: Compare extracted schemas against manually annotated examples
- **Accuracy Metrics**: Precision (% extracted fields correct) and Recall (% actual fields extracted)
- **Target**: >90% accuracy on schema extraction
- **Compression Benchmarks**: Compare against gzip (baseline) and LogShrink (if available)

#### Precision/Recall Calculation for Schema Extraction

**Precision**: Of all fields you extracted, how many are correct?
```python
# Example: Manual annotation says log has [TIMESTAMP, SEVERITY, MESSAGE]
# Your system extracted [TIMESTAMP, SEVERITY, IP_ADDRESS, MESSAGE]

true_positives = 3  # TIMESTAMP, SEVERITY, MESSAGE are correct
false_positives = 1  # IP_ADDRESS is wrong (doesn't exist in ground truth)
precision = true_positives / (true_positives + false_positives) = 3/4 = 75%
```

**Recall**: Of all fields that should be extracted, how many did you find?
```python
# Same example
true_positives = 3   # Found TIMESTAMP, SEVERITY, MESSAGE
false_negatives = 0  # Didn't miss any required fields
recall = true_positives / (true_positives + false_negatives) = 3/3 = 100%
```

**F1-Score**: Harmonic mean of precision and recall
```python
f1 = 2 * (precision * recall) / (precision + recall) = 2 * (0.75 * 1.0) / (0.75 + 1.0) = 85.7%
```

#### Testing Commands

```bash
# Run schema extraction on test set
python logsim/evaluator.py --dataset datasets/Apache/Apache_full.log --ground-truth annotations/apache_ground_truth.json

# Compression benchmark
python logsim/compressor.py --input datasets/Apache/Apache_full.log --output compressed/apache.bin --measure
gzip -k datasets/Apache/Apache_full.log
ls -lh datasets/Apache/Apache_full.log* compressed/apache.bin

# Query performance test
python logsim/query_engine.py --compressed compressed/apache.bin --query "SELECT COUNT(*) WHERE severity='ERROR' AND timestamp > '2005-06-09 06:00:00'"
```

## Important Constraints

- **No ML models**: This is a constraint-based approach using regex, heuristics, and pattern matching
- **No distributed system**: Single-machine implementation (laptop/workstation sufficient)
- **Python or Rust**: Choose based on performance needs (Python for prototyping, Rust for compression)
- **Queryability requirement**: Compression must preserve ability to filter/aggregate without full decompression

## External Dependencies

### Python Libraries (requirements.txt)
```python
# Core dependencies
regex>=2023.0.0           # Advanced regex patterns with Unicode support
python-dateutil>=2.8.0    # Timestamp parsing (multiple formats)
numpy>=1.24.0             # Numerical operations for compression
pandas>=2.0.0             # Data manipulation for evaluation

# Compression codecs
zstandard>=0.21.0         # Zstandard compression (baseline comparison)
python-snappy>=0.6.0      # Snappy compression (fast codec)
lz4>=4.3.0                # LZ4 compression (alternative baseline)

# Testing & benchmarks
pytest>=7.4.0             # Unit testing framework
pytest-benchmark>=4.0.0   # Performance benchmarking
```

### Optional Tools
```bash
# Install gzip for baseline compression comparison (usually pre-installed)
gzip --version

# Install hyperfine for command-line benchmarking
cargo install hyperfine
# or: sudo apt install hyperfine

# Memory profiling (optional)
pip install memory-profiler
```

### Installation
```bash
cd "/home/neo/Documents/THESIS/Automatic Schema Extraction from Unstructured System Logs"
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Research Context

**Target venues**: VLDB, SIGMOD, IEEE BigData  
**Related work**: Log parsing (Drain, Spell), schema inference, lakehouse compression (Parquet, ORC)  
**Novel contribution**: Semantic-aware compression that adapts to log content types, not generic compression

## Common Pitfalls to Avoid

1. **Don't overfit to one log format**: Patterns must generalize across Apache, HealthApp, Zookeeper, etc.
2. **Don't ignore timestamp diversity**: Handle ISO8601, Unix epoch, custom formats
3. **Don't compress without indexing**: Queryability is core requirement, not optional
4. **Don't skip schema versioning**: Logs change format over time (v1 → v2 → v3)
5. **Don't use lossy compression**: Must be able to reconstruct exact original logs

## Key Files to Reference

- **PROJECT.md**: Complete thesis roadmap with phase details, algorithms, evaluation criteria
- **datasets/Apache/Apache_full.log**: Example of web server log format (52K lines)
- **datasets/HealthApp/HealthApp_full.log**: Example of structured pipe-delimited logs (212K lines)
- **datasets/Zookeeper/Zookeeper_full.log**: Example of Java application logs with stack traces (74K lines)
