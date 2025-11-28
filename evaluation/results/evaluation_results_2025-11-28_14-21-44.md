# logpress Evaluation Results

**Date**: 2025-11-28 14:21:44

**Total Datasets**: 8
**Total Logs**: 1,072,831
**Total Original Size**: 124.92 MB
**Total Compressed Size**: 10454.47 KB
**Average Compression Ratio**: 12.24×
**vs gzip-9**: 98.4%

## Summary Table

| Dataset | Logs | Original Size | Compressed Size | Ratio | vs gzip | Compression Speed | Decompression Speed | Templates |
|---------|------|---------------|-----------------|-------|---------|-------------------|---------------------|----------|
| Apache | 51,978 | 4.75 MB | 589.17 KB | 8.25× | 38.8% | 0.72 MB/s | 5.41 MB/s | 19 |
| HPC | 433,490 | 31.58 MB | 3677.94 KB | 8.79× | 79.2% | 0.55 MB/s | 5.31 MB/s | 49 |
| HealthApp | 212,394 | 19.53 MB | 2295.15 KB | 8.72× | 79.8% | 1.66 MB/s | 8.27 MB/s | 2 |
| Linux | 25,567 | 2.24 MB | 240.27 KB | 9.53× | 84.8% | 0.58 MB/s | 6.87 MB/s | 73 |
| Mac | 116,735 | 15.95 MB | 855.22 KB | 19.10× | 163.1% | 0.70 MB/s | 10.92 MB/s | 184 |
| OpenStack | 137,074 | 38.63 MB | 1899.04 KB | 20.83× | 166.8% | 1.20 MB/s | 12.65 MB/s | 35 |
| Proxifier | 21,320 | 2.40 MB | 203.41 KB | 12.09× | 77.1% | 0.75 MB/s | 8.13 MB/s | 26 |
| Zookeeper | 74,273 | 9.84 MB | 694.26 KB | 14.52× | 56.1% | 0.76 MB/s | 7.18 MB/s | 30 |

**Average** | 1,072,831 | 124.92 MB | 10454.47 KB | 12.24× | 98.4% | — | — | — |

## Per-Dataset Details

### Apache

- **Log Entries**: 51,978
- **Original Size**: 4,975,683 bytes (4.75 MB)
- **Compressed Size**: 603,315 bytes (589.17 KB)
- **Compression Ratio**: 8.25×
- **gzip-9 Size**: 234,368 bytes (228.88 KB)
- **gzip-9 Ratio**: 21.23×
- **vs gzip-9**: 38.8%
- **Compression Time**: 6.573s (0.72 MB/s)
- **Decompression Time**: 0.878s (5.41 MB/s)
- **Templates Extracted**: 19

### HPC

- **Log Entries**: 433,490
- **Original Size**: 33,119,214 bytes (31.58 MB)
- **Compressed Size**: 3,766,213 bytes (3677.94 KB)
- **Compression Ratio**: 8.79×
- **gzip-9 Size**: 2,981,182 bytes (2911.31 KB)
- **gzip-9 Ratio**: 11.11×
- **vs gzip-9**: 79.2%
- **Compression Time**: 57.805s (0.55 MB/s)
- **Decompression Time**: 5.949s (5.31 MB/s)
- **Templates Extracted**: 49

### HealthApp

- **Log Entries**: 212,394
- **Original Size**: 20,483,278 bytes (19.53 MB)
- **Compressed Size**: 2,350,232 bytes (2295.15 KB)
- **Compression Ratio**: 8.72×
- **gzip-9 Size**: 1,874,754 bytes (1830.81 KB)
- **gzip-9 Ratio**: 10.93×
- **vs gzip-9**: 79.8%
- **Compression Time**: 11.754s (1.66 MB/s)
- **Decompression Time**: 2.362s (8.27 MB/s)
- **Templates Extracted**: 2

### Linux

- **Log Entries**: 25,567
- **Original Size**: 2,344,672 bytes (2.24 MB)
- **Compressed Size**: 246,036 bytes (240.27 KB)
- **Compression Ratio**: 9.53×
- **gzip-9 Size**: 208,685 bytes (203.79 KB)
- **gzip-9 Ratio**: 11.24×
- **vs gzip-9**: 84.8%
- **Compression Time**: 3.824s (0.58 MB/s)
- **Decompression Time**: 0.326s (6.87 MB/s)
- **Templates Extracted**: 73

### Mac

- **Log Entries**: 116,735
- **Original Size**: 16,723,167 bytes (15.95 MB)
- **Compressed Size**: 875,747 bytes (855.22 KB)
- **Compression Ratio**: 19.10×
- **gzip-9 Size**: 1,428,148 bytes (1394.68 KB)
- **gzip-9 Ratio**: 11.71×
- **vs gzip-9**: 163.1%
- **Compression Time**: 22.827s (0.70 MB/s)
- **Decompression Time**: 1.460s (10.92 MB/s)
- **Templates Extracted**: 184

### OpenStack

- **Log Entries**: 137,074
- **Original Size**: 40,506,364 bytes (38.63 MB)
- **Compressed Size**: 1,944,619 bytes (1899.04 KB)
- **Compression Ratio**: 20.83×
- **gzip-9 Size**: 3,242,939 bytes (3166.93 KB)
- **gzip-9 Ratio**: 12.49×
- **vs gzip-9**: 166.8%
- **Compression Time**: 32.147s (1.20 MB/s)
- **Decompression Time**: 3.053s (12.65 MB/s)
- **Templates Extracted**: 35

### Proxifier

- **Log Entries**: 21,320
- **Original Size**: 2,519,085 bytes (2.40 MB)
- **Compressed Size**: 208,293 bytes (203.41 KB)
- **Compression Ratio**: 12.09×
- **gzip-9 Size**: 160,630 bytes (156.87 KB)
- **gzip-9 Ratio**: 15.68×
- **vs gzip-9**: 77.1%
- **Compression Time**: 3.205s (0.75 MB/s)
- **Decompression Time**: 0.295s (8.13 MB/s)
- **Templates Extracted**: 26

### Zookeeper

- **Log Entries**: 74,273
- **Original Size**: 10,319,891 bytes (9.84 MB)
- **Compressed Size**: 710,926 bytes (694.26 KB)
- **Compression Ratio**: 14.52×
- **gzip-9 Size**: 398,948 bytes (389.60 KB)
- **gzip-9 Ratio**: 25.87×
- **vs gzip-9**: 56.1%
- **Compression Time**: 12.888s (0.76 MB/s)
- **Decompression Time**: 1.371s (7.18 MB/s)
- **Templates Extracted**: 30

