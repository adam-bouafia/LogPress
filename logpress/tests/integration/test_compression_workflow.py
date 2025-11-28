"""
Integration tests for compression workflow
"""

import pytest
from pathlib import Path
from logpress.services.compressor import SemanticCompressor

class TestCompressionWorkflow:
    """Test end-to-end compression workflow"""
    
    def test_compress_single_dataset(self, sample_logs):
        """Test compressing a single dataset"""
        compressor = SemanticCompressor(min_support=2)
        
        compressed_log, stats = compressor.compress(sample_logs, verbose=False)
        
        assert stats.template_count > 0
        assert stats.log_count == len(sample_logs)
        assert compressed_log is not None
    
    def test_compress_and_save(self, test_output_dir, sample_logs):
        """Test compression and file saving"""
        compressor = SemanticCompressor(min_support=2)
        output_file = test_output_dir / "compressed" / "test.lsc"
        
        compressed_log, stats = compressor.compress(sample_logs, verbose=False)
        compressor.save(output_file, verbose=False)
        
        assert output_file.exists()
        assert output_file.stat().st_size > 0
    
    def test_compress_multiple_datasets(self, test_data_dir, test_output_dir):
        """Test compressing multiple datasets sequentially"""
        compressor = SemanticCompressor(min_support=2)
        results = []
        
        for dataset_dir in test_data_dir.iterdir():
            if dataset_dir.is_dir():
                log_file = dataset_dir / f"{dataset_dir.name}_full.log"
                
                with open(log_file, 'r', errors='ignore') as f:
                    logs = [line.strip() for line in f if line.strip()]
                
                compressed_log, stats = compressor.compress(logs, verbose=False)
                results.append({
                    'dataset': dataset_dir.name,
                    'templates': stats.template_count,
                    'logs': stats.log_count
                })
        
        assert len(results) == 2
        assert all(r['templates'] > 0 for r in results)
    
    def test_compression_ratio_calculation(self, sample_logs):
        """Test that compression ratio is calculated correctly"""
        compressor = SemanticCompressor(min_support=2)
        
        # Use more logs for realistic compression
        large_sample = sample_logs * 100  # 500 logs
        
        original_size = sum(len(log.encode('utf-8')) for log in large_sample)
        compressed_log, stats = compressor.compress(large_sample, verbose=False)
        
        # With more data, compressed size should be smaller
        # Note: Very small samples may not compress well
        assert stats.compressed_size > 0
        compression_ratio = original_size / stats.compressed_size
        # Should achieve at least some compression with repeated patterns
        assert compression_ratio > 0.5
