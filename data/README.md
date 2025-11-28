# Data Directory

Contains input datasets and ground truth annotations for LogSim validation.

## Structure

```
data/
├── datasets/         # Real-world log sources (497K entries)
│   ├── Apache/
│   ├── HealthApp/
│   ├── Zookeeper/
│   ├── OpenStack/
│   ├── Proxifier/
│   └── BGL/
│       HDFS/
│       HPC/
│       Linux/
│       Mac/
└── ground_truth/     # Manual annotations for accuracy validation
```

## Datasets Overview

| Dataset | Lines | Size | Format | Use Case |
|---------|-------|------|--------|----------|
| **Apache** | 52,437 | 4.76 MB | Syslog-style | Web server logs |
| **HealthApp** | 212,005 | 19.21 MB | Pipe-delimited | Android health tracking |
| **Zookeeper** | 74,380 | 9.85 MB | Java logging | Distributed coordination |
| **OpenStack** | 137,236 | 28.35 MB | Multi-file | Cloud infrastructure |
| **Proxifier** | 21,329 | 2.01 MB | Structured | Network proxy |

## Dataset Details

### Apache (Web Server Logs)
**Format**: `[TIMESTAMP] [SEVERITY] MESSAGE`

```
[Thu Jun 09 06:07:04 2005] [notice] LDAP: Built with OpenLDAP LDAP SDK
[Thu Jun 09 06:07:05 2005] [error] env.createBean2(): Factory error
[Thu Jun 09 06:07:19 2005] [notice] Apache/2.0.49 configured
```

**Characteristics**:
- Fixed bracket-delimited structure
- 5 severity levels: notice, error, warn, info, debug
- Apache/module names in messages
- No stack traces

**Files**:
- `Apache_full.log` - Complete dataset (52,437 lines)
- `Apache_2k.log` - Sample for testing (2,000 lines)

### HealthApp (Android Health Tracking)
**Format**: `TIMESTAMP|COMPONENT|PROCESS_ID|MESSAGE`

```
20171223-22:15:29:606|Step_LSC|30002312|onStandStepChanged 3579
20171223-22:15:29:633|Step_StandReportReceiver|30002312|onReceive action
```

**Characteristics**:
- Pipe-delimited fields
- Component-based hierarchy (Step_*, Health_*, etc.)
- Numeric process IDs
- Event-driven messages

**Files**:
- `HealthApp_full.log` - Complete dataset (212,005 lines)
- `HealthApp_2k.log` - Sample for testing (2,000 lines)

### Zookeeper (Distributed Coordination)
**Format**: `TIMESTAMP - SEVERITY [THREAD:CLASS@LINE] - MESSAGE`

```
2015-07-29 17:41:41,536 - INFO  [main:QuorumPeerConfig@101] - Reading configuration
2015-07-29 17:41:41,609 - INFO  [main:NIOServerCnxnFactory@94] - binding to port
2015-07-29 17:41:41,733 - WARN  [WorkerSender[myid=1]:QuorumCnxManager@368] - Cannot open channel
```

**Characteristics**:
- Java logging format
- Thread names in brackets
- Class/method/line numbers
- Multi-line stack traces

**Files**:
- `Zookeeper_full.log` - Complete dataset (74,380 lines)
- `Zookeeper_2k.log` - Sample for testing (2,000 lines)

### OpenStack (Cloud Infrastructure)
**Format**: `FILENAME TIMESTAMP PROCESS_ID SEVERITY MODULE [REQUEST_ID] MESSAGE`

```
nova-compute.log.1.2017-05-17_12:02:35 2017-05-16 15:15:54.960 2931 INFO nova.compute.manager [req-7a738b84] Took 0.54 seconds
nova-api.log.1.2017-05-17_12:02:19 2017-05-16 15:16:01.511 25749 INFO nova.osapi_compute.wsgi.server [req-378bb69b] 10.11.10.1 "GET /v2/..."
```

**Characteristics**:
- Multi-file aggregation
- Request IDs for tracing
- HTTP request logging
- Complex module hierarchies

**Files**:
- `OpenStack_full.log` - Complete dataset (137,236 lines)
- `OpenStack_2k.log` - Sample for testing (2,000 lines)

### Proxifier (Network Proxy)
**Format**: `[TIMESTAMP] PROCESS - HOST:PORT ACTION, BYTES_SENT, BYTES_RECEIVED, LIFETIME`

```
[10.30 16:49:06] chrome.exe - proxy.cse.cuhk.edu.hk:5070 close, 0 bytes sent, 0 bytes received, lifetime <1 sec
[10.30 16:49:06] chrome.exe - proxy.cse.cuhk.edu.hk:5070 open through proxy proxy.cse.cuhk.edu.hk:5070 HTTPS
```

**Characteristics**:
- Network connection lifecycle
- Byte counters
- Proxy server information
- Connection duration

**Files**:
- `Proxifier_full.log` - Complete dataset (21,329 lines)
- `Proxifier_2k.log` - Sample for testing (2,000 lines)

## Dataset Diversity (Research Validation)

The datasets provide diverse validation scenarios:

| Feature | Apache | HealthApp | Zookeeper | OpenStack | Proxifier |
|---------|--------|-----------|-----------|-----------|-----------|
| **Timestamp Format** | Syslog | Custom | ISO | ISO | Custom |
| **Field Separator** | Space | Pipe | Space | Space | Space |
| **Severity Levels** | 5 | None | 4 | 5 | None |
| **Stack Traces** | No | No | Yes | Yes | No |
| **Multi-file** | No | No | No | Yes | No |
| **Structured Fields** | Low | High | Medium | High | Medium |

This diversity tests:
- ✅ Tokenization robustness (multiple delimiters)
- ✅ Timestamp parsing flexibility (multiple formats)
- ✅ Semantic classification accuracy (different field types)
- ✅ Template extraction generalization (varied structures)

## Ground Truth Annotations

**Location**: `ground_truth/`

Manual annotations for validation, including:
- Identified semantic fields (TIMESTAMP, SEVERITY, IP, etc.)
- Field boundaries (start/end positions)
- Template assignments
- Confidence scores

**Format**: JSON
```json
{
  "log_id": "apache_001",
  "raw_log": "[Thu Jun 09 06:07:04 2005] [notice] LDAP: Built with OpenLDAP",
  "fields": [
    {"type": "TIMESTAMP", "value": "Thu Jun 09 06:07:04 2005", "start": 1, "end": 25},
    {"type": "SEVERITY", "value": "notice", "start": 28, "end": 34},
    {"type": "MESSAGE", "value": "LDAP: Built with OpenLDAP", "start": 36, "end": 61}
  ],
  "template_id": "apache_t1"
}
```

**Usage**:
```python
from logsim.services.evaluator import SchemaEvaluator

evaluator = SchemaEvaluator()
metrics = evaluator.evaluate(
    extracted_schemas=schemas,
    ground_truth_file="data/ground_truth/apache/apache_annotations.json"
)
```

## Adding New Datasets

1. **Create directory**:
   ```bash
   mkdir -p data/datasets/NewDataset
   ```

2. **Add log file**:
   ```bash
   # Full dataset
   cp your_logs.log data/datasets/NewDataset/NewDataset_full.log
   
   # Sample (first 2000 lines)
   head -n 2000 data/datasets/NewDataset/NewDataset_full.log > data/datasets/NewDataset/NewDataset_2k.log
   ```

3. **Document format** in ground truth:
   ```bash
   mkdir -p data/ground_truth/newdataset
   # Add README.md with format specification
   # Add sample annotations (JSON)
   ```

4. **Test discovery**:
   ```bash
   python -m logsim.cli.interactive
   # Should auto-discover new dataset
   ```

## Data Sources

These datasets are sourced from publicly available log repositories:
- **Apache**: Apache HTTP Server logs
- **HealthApp**: Android application logs (research dataset)
- **Zookeeper**: Apache Zookeeper distributed system logs
- **OpenStack**: OpenStack cloud platform logs
- **Proxifier**: Network proxy application logs

**Attribution**: See individual dataset directories for specific license information.

## Usage Examples

### Scan Datasets Programmatically

```python
from logsim.cli.interactive import InteractiveCLI

cli = InteractiveCLI()
datasets = cli.scan_datasets()

for ds in datasets:
    print(f"{ds.name}: {ds.lines:,} lines, {ds.size_mb:.2f} MB")
```

### Compress a Dataset

```bash
python -m logsim compress \
  -i data/datasets/Apache/Apache_full.log \
  -o evaluation/compressed/apache.lsc \
  --min-support 3 \
  -m
```

### Evaluate Against Ground Truth

```bash
python evaluation/run_full_evaluation.py
```

---

**See parent [README.md](../README.md) for complete project information.**
