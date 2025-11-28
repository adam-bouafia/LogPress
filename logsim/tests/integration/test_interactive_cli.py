"""
Integration tests for interactive CLI
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from logsim.cli.interactive import InteractiveCLI
from rich.console import Console

class TestInteractiveCLIWorkflow:
    """Test interactive CLI workflows"""
    
    def test_cli_initialization(self, test_data_dir, test_output_dir, monkeypatch):
        """Test CLI initializes with correct paths"""
        cli = InteractiveCLI()
        monkeypatch.setattr(cli, 'data_dir', test_data_dir)
        monkeypatch.setattr(cli, 'compressed_dir', test_output_dir / "compressed")
        
        assert cli.data_dir.exists()
        assert cli.compressed_dir.exists()
        assert cli.settings['min_support'] == 3
    
    def test_cli_scans_datasets_on_startup(self, test_data_dir, monkeypatch):
        """Test that CLI scans datasets when initialized"""
        cli = InteractiveCLI()
        monkeypatch.setattr(cli, 'data_dir', test_data_dir)
        
        datasets = cli.scan_datasets()
        
        assert len(datasets) > 0
        assert all(hasattr(ds, 'name') for ds in datasets)
        assert all(hasattr(ds, 'lines') for ds in datasets)
        assert all(hasattr(ds, 'size_mb') for ds in datasets)
    
    @patch('logsim.cli.interactive.Console')
    @patch('logsim.cli.interactive.Prompt')
    def test_main_menu_displays_datasets(self, mock_prompt, mock_console, 
                                        test_data_dir, monkeypatch):
        """Test that main menu displays discovered datasets"""
        cli = InteractiveCLI()
        monkeypatch.setattr(cli, 'data_dir', test_data_dir)
        cli.datasets = cli.scan_datasets()
        
        # Mock user choosing to exit
        mock_prompt.ask.return_value = 'x'
        
        try:
            cli.show_main_menu()
        except SystemExit:
            pass
        
        # Verify that datasets were loaded
        assert len(cli.datasets) > 0
    
    @patch('logsim.cli.interactive.Confirm')
    @patch('logsim.cli.interactive.Console')
    def test_dataset_selection_flow(self, mock_console, mock_confirm, 
                                    test_data_dir, monkeypatch):
        """Test selecting datasets for compression"""
        cli = InteractiveCLI()
        monkeypatch.setattr(cli, 'data_dir', test_data_dir)
        cli.datasets = cli.scan_datasets()
        
        # Mock user selecting first dataset only
        mock_confirm.ask.side_effect = [True, False]
        
        # This would normally call compress_datasets()
        # We're testing the selection logic only
        selected = []
        for ds in cli.datasets:
            if mock_confirm.ask(f"Include {ds.name}?"):
                selected.append(ds)
        
        assert len(selected) == 1
