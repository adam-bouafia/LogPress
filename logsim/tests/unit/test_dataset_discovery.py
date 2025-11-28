"""
Unit tests for dataset discovery functionality
"""

import pytest
from pathlib import Path
from logsim.cli.interactive import InteractiveCLI, Dataset

class TestDatasetDiscovery:
    """Test dataset auto-discovery feature"""
    
    def test_scan_datasets_finds_valid_logs(self, test_data_dir, monkeypatch):
        """Test that scan_datasets finds all valid log files"""
        cli = InteractiveCLI()
        monkeypatch.setattr(cli, 'data_dir', test_data_dir)
        
        datasets = cli.scan_datasets()
        
        assert len(datasets) == 2
        assert any(ds.name == 'Apache' for ds in datasets)
        assert any(ds.name == 'HealthApp' for ds in datasets)
    
    def test_scan_datasets_calculates_size_correctly(self, test_data_dir, monkeypatch):
        """Test that dataset sizes are calculated in MB"""
        cli = InteractiveCLI()
        monkeypatch.setattr(cli, 'data_dir', test_data_dir)
        
        datasets = cli.scan_datasets()
        
        for ds in datasets:
            assert ds.size_mb > 0
            assert isinstance(ds.size_mb, float)
    
    def test_scan_datasets_counts_lines(self, test_data_dir, monkeypatch):
        """Test that log line counts are accurate"""
        cli = InteractiveCLI()
        monkeypatch.setattr(cli, 'data_dir', test_data_dir)
        
        datasets = cli.scan_datasets()
        apache = next(ds for ds in datasets if ds.name == 'Apache')
        
        # Check that lines are counted (exact count may vary based on fixture)
        assert apache.lines >= 300  # At least 300 lines
        assert apache.lines < 500   # But not too many
    
    def test_scan_datasets_empty_directory(self, tmp_path, monkeypatch):
        """Test handling of empty datasets directory"""
        cli = InteractiveCLI()
        empty_dir = tmp_path / "empty_datasets"
        empty_dir.mkdir()
        monkeypatch.setattr(cli, 'data_dir', empty_dir)
        
        datasets = cli.scan_datasets()
        
        assert len(datasets) == 0
    
    def test_scan_datasets_missing_directory(self, tmp_path, monkeypatch):
        """Test handling of missing datasets directory"""
        cli = InteractiveCLI()
        nonexistent = tmp_path / "nonexistent"
        monkeypatch.setattr(cli, 'data_dir', nonexistent)
        
        datasets = cli.scan_datasets()
        
        assert len(datasets) == 0
    
    def test_scan_datasets_ignores_invalid_files(self, tmp_path, monkeypatch):
        """Test that non-log files are ignored"""
        cli = InteractiveCLI()
        datasets_dir = tmp_path / "datasets"
        datasets_dir.mkdir()
        
        # Create invalid dataset (wrong filename pattern)
        invalid_dir = datasets_dir / "Invalid"
        invalid_dir.mkdir()
        (invalid_dir / "wrong_name.txt").write_text("test")
        
        monkeypatch.setattr(cli, 'data_dir', datasets_dir)
        datasets = cli.scan_datasets()
        
        assert len(datasets) == 0
    
    def test_datasets_sorted_alphabetically(self, test_data_dir, monkeypatch):
        """Test that datasets are returned in alphabetical order"""
        cli = InteractiveCLI()
        monkeypatch.setattr(cli, 'data_dir', test_data_dir)
        
        datasets = cli.scan_datasets()
        names = [ds.name for ds in datasets]
        
        assert names == sorted(names)

class TestDatasetValidation:
    """Test dataset file validation"""
    
    def test_validate_log_file_format(self, test_data_dir):
        """Test that log files have expected format"""
        apache_log = test_data_dir / "Apache" / "Apache_full.log"
        
        assert apache_log.exists()
        assert apache_log.suffix == ".log"
        
        with open(apache_log, 'r') as f:
            first_line = f.readline()
            assert first_line.startswith('[')
    
    def test_validate_log_file_readable(self, test_data_dir):
        """Test that log files are readable"""
        for dataset_dir in test_data_dir.iterdir():
            if dataset_dir.is_dir():
                log_file = dataset_dir / f"{dataset_dir.name}_full.log"
                
                assert log_file.exists()
                # Should not raise exception
                with open(log_file, 'r', errors='ignore') as f:
                    lines = f.readlines()
                    assert len(lines) > 0
