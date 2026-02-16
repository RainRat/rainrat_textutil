import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
import yaml

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

def test_smart_extension_markdown(temp_cwd, mock_argv):
    """Verify -m produces combined_files.md."""
    with mock_argv(['.','-m', '--dry-run']):
        with patch('sourcecombine.find_and_combine_files') as mock_combine:
            mock_combine.return_value = {}
            main()

            # Check the second argument to find_and_combine_files (output_path)
            args, _ = mock_combine.call_args
            assert args[1] == 'combined_files.md'
            # Also check if config was updated
            assert args[0]['output']['file'] == 'combined_files.md'

def test_smart_extension_json(temp_cwd, mock_argv):
    """Verify -j produces combined_files.json."""
    with mock_argv(['.','-j', '--dry-run']):
        with patch('sourcecombine.find_and_combine_files') as mock_combine:
            mock_combine.return_value = {}
            main()

            args, _ = mock_combine.call_args
            assert args[1] == 'combined_files.json'
            assert args[0]['output']['file'] == 'combined_files.json'

def test_smart_extension_xml(temp_cwd, mock_argv):
    """Verify -f xml produces combined_files.xml."""
    with mock_argv(['.','-f', 'xml', '--dry-run']):
        with patch('sourcecombine.find_and_combine_files') as mock_combine:
            mock_combine.return_value = {}
            main()

            args, _ = mock_combine.call_args
            assert args[1] == 'combined_files.xml'
            assert args[0]['output']['file'] == 'combined_files.xml'

def test_config_format_respect(temp_cwd, mock_argv):
    """Verify format: json in config is respected and produces .json."""
    config_file = temp_cwd / "sourcecombine.yml"
    config_data = {
        'search': {'root_folders': ['.']},
        'output': {'format': 'json'}
    }
    with open(config_file, 'w') as f:
        yaml.dump(config_data, f)

    with mock_argv(['--dry-run']):
        with patch('sourcecombine.find_and_combine_files') as mock_combine:
            mock_combine.return_value = {}
            main()

            args, kwargs = mock_combine.call_args
            assert args[1] == 'combined_files.json'
            assert kwargs['output_format'] == 'json'

def test_explicit_output_preserved(temp_cwd, mock_argv):
    """Verify explicit -o my.txt is NOT changed even for markdown."""
    with mock_argv(['.','-m', '-o', 'my.txt', '--dry-run']):
        with patch('sourcecombine.find_and_combine_files') as mock_combine:
            mock_combine.return_value = {}
            main()

            args, _ = mock_combine.call_args
            assert args[1] == 'my.txt'

def test_cli_override_config_format(temp_cwd, mock_argv):
    """Verify CLI -f text overrides config format: markdown."""
    config_file = temp_cwd / "sourcecombine.yml"
    config_data = {
        'search': {'root_folders': ['.']},
        'output': {'format': 'markdown'}
    }
    with open(config_file, 'w') as f:
        yaml.dump(config_data, f)

    with mock_argv(['-f', 'text', '--dry-run']):
        with patch('sourcecombine.find_and_combine_files') as mock_combine:
            mock_combine.return_value = {}
            main()

            args, kwargs = mock_combine.call_args
            assert args[1] == 'combined_files.txt'
            assert kwargs['output_format'] == 'text'

def test_summary_tokens_visible_in_pairing_mode(monkeypatch, capsys):
    # Mock stats
    stats = {
        'total_files': 10,
        'total_size_bytes': 1000,
        'files_by_extension': {'.py': 10},
        'total_tokens': 1234,
        'token_count_is_approx': False,
        'top_files': [(500, 2000, 'file.py')]
    }

    # Mock args
    args = MagicMock()
    args.dry_run = False
    args.estimate_tokens = True
    args.list_files = False
    args.tree = False

    monkeypatch.setenv("NO_COLOR", "1")

    # Call with pairing_enabled=True
    import sourcecombine
    sourcecombine._print_execution_summary(stats, args, pairing_enabled=True)

    captured = capsys.readouterr()
    stderr = captured.err

    # Token Count should now be visible even in pairing mode
    # 10 spaces from label padding + 7 spaces from value padding
    assert "Token Count:                 1,234" in stderr
    # Largest Files should also be visible
    assert "Largest Files (by tokens)" in stderr
    # 4 (indent) + 7 (padding) + 500 + 2 (spaces) + 3 (padding) + (1.95 KB)
    assert "           500     (1.95 KB)  file.py" in stderr

def test_summary_tokens_visible_with_list_files(monkeypatch, capsys):
    # Mock stats
    stats = {
        'total_files': 5,
        'total_size_bytes': 500,
        'files_by_extension': {'.md': 5},
        'total_tokens': 567,
        'token_count_is_approx': False,
        'top_files': [(100, 500, 'doc.md')]
    }

    # Mock args
    args = MagicMock()
    args.dry_run = False
    args.estimate_tokens = True
    args.list_files = True
    args.tree = False

    monkeypatch.setenv("NO_COLOR", "1")

    import sourcecombine
    sourcecombine._print_execution_summary(stats, args, pairing_enabled=False)

    captured = capsys.readouterr()
    stderr = captured.err

    # Token Count should now be visible even with --list-files
    # 10 spaces from label padding + 9 spaces from value padding
    assert "Token Count:                   567" in stderr
    # Largest Files should also be visible
    assert "Largest Files (by tokens)" in stderr
    # 4 (indent) + 7 (padding) + 100 + 2 (spaces) + 1 (padding) + (500.00 B)
    assert "           100    (500.00 B)  doc.md" in stderr
