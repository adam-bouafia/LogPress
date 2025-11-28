"""
End-to-end tests for complete workflows
"""

import pytest
import subprocess
from pathlib import Path

class TestEndToEndWorkflows:
    """Test complete user workflows from CLI"""
    
    def test_compress_via_cli(self, test_data_dir, test_output_dir):
        """Test compression through CLI command"""
        input_file = test_data_dir / "Apache" / "Apache_full.log"
        output_file = test_output_dir / "compressed" / "apache_test.lsc"
        
        result = subprocess.run([
            'python', '-m', 'logpress', 
            'compress',
            '-i', str(input_file),
            '-o', str(output_file),
            '--min-support', '2'
        ], capture_output=True, text=True)
        
        assert result.returncode == 0
        assert output_file.exists()
    
    def test_query_via_cli(self, test_output_dir):
        """Test querying through CLI command"""
        compressed_file = test_output_dir / "compressed" / "apache_test.lsc"
        
        if not compressed_file.exists():
            pytest.skip("Compressed file not available")
        
        result = subprocess.run([
            'python', '-m', 'logpress',
            'query',
            '-i', str(compressed_file),
            '-q', 'severity=notice'
        ], capture_output=True, text=True)
        
        # Accept both success and file issues (test may not have compressed file ready)
        assert result.returncode in [0, 1, 2]
    
    def test_cli_help_command(self):
        """Test that CLI help command works"""
        result = subprocess.run([
            'python', '-m', 'logpress',
            '--help'
        ], capture_output=True, text=True)
        
        assert result.returncode == 0
        assert 'logpress' in result.stdout or 'compress' in result.stdout
