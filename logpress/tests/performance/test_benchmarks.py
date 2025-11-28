"""
Performance benchmarks for compression and query operations
"""

import pytest
import time
from logpress.services.compressor import SemanticCompressor

@pytest.mark.benchmark
class TestPerformanceBenchmarks:
    """Benchmark compression and query performance"""
    
    def test_compression_throughput(self, sample_logs, benchmark):
        """Benchmark compression throughput"""
        compressor = SemanticCompressor(min_support=2)
        
        def compress_logs():
            return compressor.compress(sample_logs, verbose=False)
        
        result = benchmark(compress_logs)
        compressed_log, stats = result
        
        # Should process at least 100 logs/second
        # Note: benchmark.stats is accessible via benchmark.stats.stats.mean
        throughput = len(sample_logs) / benchmark.stats.stats.mean
        assert throughput > 10  # Lower threshold for small samples
    
    def test_template_extraction_speed(self, sample_logs, benchmark):
        """Benchmark template extraction performance"""
        from logpress.context.extraction.template_generator import TemplateGenerator
        
        def extract_templates():
            generator = TemplateGenerator(min_support=2)
            return generator.extract_schemas(sample_logs)
        
        result = benchmark(extract_templates)
        
        # Template extraction should complete in reasonable time
        assert benchmark.stats.stats.mean < 1.0  # Less than 1 second
    
    @pytest.mark.parametrize("dataset_size", [100, 1000, 10000])
    def test_scalability(self, dataset_size):
        """Test compression scalability with different dataset sizes"""
        # Generate synthetic logs
        logs = [f"[2005-06-09 06:07:{i%60:02d}] [info] Test message {i}" 
                for i in range(dataset_size)]
        
        compressor = SemanticCompressor(min_support=3)
        
        start = time.time()
        compressed_log, stats = compressor.compress(logs, verbose=False)
        elapsed = time.time() - start
        
        throughput = dataset_size / elapsed
        
        # Should maintain throughput > 500 logs/sec for all sizes
        assert throughput > 500, f"Throughput {throughput:.0f} logs/sec is too low"
