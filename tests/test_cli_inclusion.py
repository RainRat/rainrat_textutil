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

def test_cli_inclusion_inject_into_config(temp_cwd, mock_argv):
    """Test that CLI inclusions are correctly injected into the configuration."""
    config_file = temp_cwd / "config.yml"
    config_data = {
        'search': {'root_folders': ['.']},
        'filters': {
            'inclusion_groups': {
                'existing_group': {
                    'enabled': True,
                    'filenames': ['*.py']
                }
            }
        }
    }
    with open(config_file, 'w') as f:
        yaml.dump(config_data, f)

    with patch('sourcecombine.find_and_combine_files') as mock_combine:
        mock_combine.return_value = {}

        args = [
            str(config_file),
            '--include', '*.txt',
            '-i', '*.md'
        ]

        with mock_argv(args):
            main()

        assert mock_combine.called
        config_passed = mock_combine.call_args[0][0]
        groups = config_passed['filters']['inclusion_groups']

        # Check original group is preserved
        assert 'existing_group' in groups
        assert groups['existing_group']['enabled'] is True
        assert '*.py' in groups['existing_group']['filenames']

        # Check CLI group is added
        assert '_cli_includes' in groups
        assert groups['_cli_includes']['enabled'] is True
        assert '*.txt' in groups['_cli_includes']['filenames']
        assert '*.md' in groups['_cli_includes']['filenames']

def test_cli_inclusion_sanitize_patterns(temp_cwd, mock_argv, caplog):
    """Test that CLI inclusions are sanitized."""
    config_file = temp_cwd / "config.yml"
    with open(config_file, 'w') as f:
        yaml.dump({'search': {'root_folders': ['.']}}, f)

    caplog.set_level(logging.WARNING)

    with patch('sourcecombine.find_and_combine_files') as mock_combine:
        mock_combine.return_value = {}

        args = [str(config_file), '--include', 'src\\**\\*.py']

        with mock_argv(args):
            main()

        config_passed = mock_combine.call_args[0][0]
        filenames = config_passed['filters']['inclusion_groups']['_cli_includes']['filenames']

        assert 'src/**/*.py' in filenames
        assert "uses backslashes" in caplog.text

def test_cli_inclusion_create_filters_section(temp_cwd, mock_argv):
    """Test that CLI inclusions work even if 'filters' section is missing."""
    config_file = temp_cwd / "minimal.yml"
    with open(config_file, 'w') as f:
        yaml.dump({'search': {'root_folders': ['.']}}, f)

    with patch('sourcecombine.find_and_combine_files') as mock_combine:
        mock_combine.return_value = {}

        with mock_argv([str(config_file), '--include', '*.py']):
            main()

        config_passed = mock_combine.call_args[0][0]
        assert 'filters' in config_passed
        assert 'inclusion_groups' in config_passed['filters']
        assert '_cli_includes' in config_passed['filters']['inclusion_groups']
        assert '*.py' in config_passed['filters']['inclusion_groups']['_cli_includes']['filenames']
