import sys
import os
import logging
import pytest
from unittest.mock import patch
from pathlib import Path
import yaml
import sourcecombine
from sourcecombine import main

@pytest.fixture
def mock_argv():
    """Context manager to mock sys.argv."""
    def _mock_argv(args):
        return patch.object(sys, 'argv', ['sourcecombine.py'] + args)
    return _mock_argv

@pytest.fixture(autouse=True)
def reset_logging():
    """Reset logging before and after each test."""
    root = logging.getLogger()
    for h in root.handlers[:]:
        root.removeHandler(h)
    root.setLevel(logging.NOTSET)
    yield
    for h in root.handlers[:]:
        root.removeHandler(h)

@pytest.fixture
def temp_cwd(tmp_path):
    """Context manager to change current working directory."""
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(original_cwd)

def test_cli_exclusions_inject_into_config(temp_cwd, mock_argv):
    """Test that CLI exclusions are correctly injected into the configuration."""
    config_file = temp_cwd / "config.yml"
    config_data = {
        'search': {'root_folders': ['.']},
        'filters': {
            'exclusions': {
                'filenames': ['existing_file.txt'],
                'folders': ['existing_folder']
            }
        }
    }
    with open(config_file, 'w') as f:
        yaml.dump(config_data, f)

    with patch('sourcecombine.find_and_combine_files') as mock_combine:
        mock_combine.return_value = {}

        args = [
            str(config_file),
            '--exclude-file', 'cli_file.py',
            '--exclude-folder', 'cli_folder',
            '--exclude-file', 'another_file.js'
        ]

        with mock_argv(args):
            main()

        assert mock_combine.called
        config_passed = mock_combine.call_args[0][0]
        exclusions = config_passed['filters']['exclusions']

        # Check original config is preserved
        assert 'existing_file.txt' in exclusions['filenames']
        assert 'existing_folder' in exclusions['folders']

        # Check CLI args are added
        assert 'cli_file.py' in exclusions['filenames']
        assert 'another_file.js' in exclusions['filenames']
        assert 'cli_folder' in exclusions['folders']

def test_cli_exclusions_sanitize_patterns(temp_cwd, mock_argv, caplog):
    """Test that CLI exclusions are sanitized (e.g. backslashes replaced)."""
    config_file = temp_cwd / "config.yml"
    with open(config_file, 'w') as f:
        yaml.dump({'search': {'root_folders': ['.']}}, f)

    caplog.set_level(logging.WARNING)

    with patch('sourcecombine.find_and_combine_files') as mock_combine:
        mock_combine.return_value = {}

        # Using backslashes which should be sanitized to forward slashes
        args = [str(config_file), '--exclude-file', 'win\\style\\path.txt']

        with mock_argv(args):
            main()

        config_passed = mock_combine.call_args[0][0]
        filenames = config_passed['filters']['exclusions']['filenames']

        assert 'win/style/path.txt' in filenames
        assert "uses backslashes" in caplog.text

def test_cli_exclusions_create_filters_section(temp_cwd, mock_argv):
    """Test that CLI exclusions work even if 'filters' section is missing in config."""
    config_file = temp_cwd / "minimal.yml"
    with open(config_file, 'w') as f:
        yaml.dump({'search': {'root_folders': ['.']}}, f)

    with patch('sourcecombine.find_and_combine_files') as mock_combine:
        mock_combine.return_value = {}

        with mock_argv([str(config_file), '--exclude-file', '*.tmp']):
            main()

        config_passed = mock_combine.call_args[0][0]
        assert 'filters' in config_passed
        assert 'exclusions' in config_passed['filters']
        assert '*.tmp' in config_passed['filters']['exclusions']['filenames']
