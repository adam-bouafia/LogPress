"""
Pytest configuration and shared fixtures for LogSim tests
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict
import json

@pytest.fixture(scope="session")
def test_data_dir(tmp_path_factory):
    """Create temporary test data directory structure"""
    data_dir = tmp_path_factory.mktemp("test_data")
    datasets_dir = data_dir / "datasets"
    datasets_dir.mkdir()
    
    # Create mock datasets
    apache_dir = datasets_dir / "Apache"
    apache_dir.mkdir()
    apache_log = apache_dir / "Apache_full.log"
    apache_log.write_text(
        "[Thu Jun 09 06:07:04 2005] [notice] LDAP: Built with OpenLDAP\n"
        "[Thu Jun 09 06:07:05 2005] [error] Factory error creating channel\n"
        "[Thu Jun 09 06:07:19 2005] [notice] Apache/2.0.49 configured\n" * 100
    )
    
    healthapp_dir = datasets_dir / "HealthApp"
    healthapp_dir.mkdir()
    healthapp_log = healthapp_dir / "HealthApp_full.log"
    healthapp_log.write_text(
        "20171223-22:15:29:606|Step_LSC|30002312|onStandStepChanged 3579\n"
        "20171223-22:15:29:633|Step_StandReportReceiver|30002312|onReceive action\n"
        "20171223-22:15:29:635|Step_StandStepCounter|30002312|flush sensor data\n" * 50
    )
    
    return datasets_dir

@pytest.fixture(scope="session")
def test_output_dir(tmp_path_factory):
    """Create temporary output directory for compressed files"""
    output_dir = tmp_path_factory.mktemp("test_output")
    compressed_dir = output_dir / "compressed"
    compressed_dir.mkdir()
    results_dir = output_dir / "results"
    results_dir.mkdir()
    return output_dir

@pytest.fixture
def sample_logs() -> List[str]:
    """Sample log lines for testing"""
    return [
        "[Thu Jun 09 06:07:04 2005] [notice] LDAP: Built with OpenLDAP",
        "[Thu Jun 09 06:07:05 2005] [error] Factory error creating channel",
        "[Thu Jun 09 06:07:19 2005] [notice] Apache/2.0.49 configured",
        "20171223-22:15:29:606|Step_LSC|30002312|onStandStepChanged 3579",
        "20171223-22:15:29:633|Step_StandReportReceiver|30002312|onReceive",
    ]

@pytest.fixture
def mock_settings() -> Dict:
    """Default settings for testing"""
    return {
        'min_support': 3,
        'zstd_level': 15,
        'measure': True,
        'enable_bwt': True,
    }
