# Changelog

All notable changes to logpress will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 2025-11-28

### Changed
- Recommend PyPI installation (`pip install LogPress`) as the preferred install method in the main README and deployment README.
- Bump package version to `1.0.1`.

## [0.1.0] - 2025-11-28

### Added
- Initial release of logpress
- Automatic schema extraction from unstructured logs
- Semantic-aware columnar compression
- Queryable compressed storage with field-level access
- Interactive CLI with menu-driven interface
- Comprehensive benchmarking framework
- Support for 8 diverse log datasets (Apache, HealthApp, HPC, Linux, Mac, OpenStack, Proxifier, Zookeeper)
- Template extraction with alignment algorithm
- Six specialized encoding techniques:
  - Delta encoding for timestamps
  - Dictionary encoding for categorical fields
  - Varint/Zigzag encoding for integers
  - Run-length encoding for repetitive values
  - Token-pool deduplication for messages
  - Optional Burrows-Wheeler Transform preprocessing
- Zstandard compression as final layer
- Query engine with predicate pushdown and column pruning
- Evaluation framework with accuracy metrics
- Tool installation helper (interactive menu)
- Benchmark comparisons with 5 generic compression tools (gzip, bzip2, xz, zstd, lz4)

### Performance
- Average compression ratio: 12.24× across 8 datasets
- 1.07M+ logs compressed from 124.92 MB to 10.21 MB
- Template extraction: 100% coverage (all logs matched)
- Field-level queries without full decompression

### Documentation
- Comprehensive README with usage examples
- API documentation for core classes
- Benchmark documentation
- Implementation status tracking

### Testing
- 285 unit tests across all modules
- Integration tests for end-to-end workflows
- Benchmark validation tests

[0.1.0]: https://github.com/adam-bouafia/logpress/releases/tag/v0.1.0
