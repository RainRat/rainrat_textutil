import sys
import os
from pathlib import Path
from unittest.mock import patch
import pytest

# Adjust sys.path to include the project root
sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

from sourcecombine import main

@pytest.fixture
def temp_cwd(tmp_path):
    """Context manager to change current working directory."""
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(original_cwd)

@pytest.fixture
def mock_argv():
    """Context manager to mock sys.argv."""
    def _mock_argv(args):
        return patch.object(sys, 'argv', ['sourcecombine.py'] + args)
    return _mock_argv

def test_auto_detect_markdown(temp_cwd, mock_argv):
    """Verify -o out.md auto-detects markdown format."""
    with mock_argv(['.', '-o', 'out.md', '--dry-run']):
        with patch('sourcecombine.find_and_combine_files') as mock_combine:
            mock_combine.return_value = {}
            main()
            _, kwargs = mock_combine.call_args
            assert kwargs['output_format'] == 'markdown'

def test_auto_detect_json(temp_cwd, mock_argv):
    """Verify -o out.json auto-detects json format."""
    with mock_argv(['.', '-o', 'out.json', '--dry-run']):
        with patch('sourcecombine.find_and_combine_files') as mock_combine:
            mock_combine.return_value = {}
            main()
            _, kwargs = mock_combine.call_args
            assert kwargs['output_format'] == 'json'

def test_auto_detect_xml(temp_cwd, mock_argv):
    """Verify -o out.xml auto-detects xml format."""
    with mock_argv(['.', '-o', 'out.xml', '--dry-run']):
        with patch('sourcecombine.find_and_combine_files') as mock_combine:
            mock_combine.return_value = {}
            main()
            _, kwargs = mock_combine.call_args
            assert kwargs['output_format'] == 'xml'

def test_explicit_flag_overrides_extension(temp_cwd, mock_argv):
    """Verify -f text overrides .md extension."""
    with mock_argv(['.', '-o', 'out.md', '-f', 'text', '--dry-run']):
        with patch('sourcecombine.find_and_combine_files') as mock_combine:
            mock_combine.return_value = {}
            main()
            _, kwargs = mock_combine.call_args
            assert kwargs['output_format'] == 'text'

def test_config_override_by_extension(temp_cwd, mock_argv):
    """Verify extension auto-detect overrides config format if not explicitly set on CLI."""
    import yaml
    config_file = temp_cwd / "sourcecombine.yml"
    config_data = {
        'search': {'root_folders': ['.']},
        'output': {'format': 'text'}
    }
    with open(config_file, 'w') as f:
        yaml.dump(config_data, f)

    with mock_argv(['-o', 'out.json', '--dry-run']):
        with patch('sourcecombine.find_and_combine_files') as mock_combine:
            mock_combine.return_value = {}
            main()
            _, kwargs = mock_combine.call_args
            assert kwargs['output_format'] == 'json'
