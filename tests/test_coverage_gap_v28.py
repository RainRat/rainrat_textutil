import sys
import os
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

from sourcecombine import (
    main,
    extract_files,
    _print_execution_summary,
)

@pytest.fixture
def temp_cwd(tmp_path):
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(original_cwd)

@pytest.fixture
def mock_stats():
    return {
        'total_files': 1,
        'total_discovered': 1,
        'total_size_bytes': 100,
        'files_by_language': {},
        'total_tokens': 0,
        'token_count_is_approx': False,
        'top_files': [],
        'filter_reasons': {}
    }

def test_cli_ignore_file_search_ignore_files_is_none(temp_cwd, mock_stats):
    config_file = temp_cwd / "config.yml"
    config_file.write_text("search: {ignore_files: null, root_folders: ['.']}", encoding="utf-8")

    with patch('utils.validate_config', return_value=None):
        with patch('sourcecombine.validate_config', return_value=None):
            with patch('sourcecombine.find_and_combine_files', return_value=mock_stats) as mock_combine:
                with patch.object(sys, 'argv', ['sourcecombine.py', str(config_file), '--ignore-file', 'foo.txt']):
                    main()

    args, _ = mock_combine.call_args
    config = args[0]
    assert isinstance(config['search']['ignore_files'], list)
    assert 'foo.txt' in config['search']['ignore_files']

def test_cli_exclude_extension_is_none(temp_cwd, mock_stats):
    config_file = temp_cwd / "config.yml"
    config_file.write_text("search: {exclude_extensions: null, root_folders: ['.']}", encoding="utf-8")

    with patch('utils.validate_config', return_value=None):
        with patch('sourcecombine.validate_config', return_value=None):
            with patch('sourcecombine.find_and_combine_files', return_value=mock_stats) as mock_combine:
                with patch.object(sys, 'argv', ['sourcecombine.py', str(config_file), '--exclude-ext', 'py']):
                    main()

    args, _ = mock_combine.call_args
    config = args[0]
    assert isinstance(config['search']['exclude_extensions'], list)
    assert 'py' in config['search']['exclude_extensions']

def test_extension_normalization_edge_cases(temp_cwd, mock_stats):
    config_file = temp_cwd / "config.yml"
    config_file.write_text("""
search:
  root_folders: ['.']
  allowed_extensions: [123, '.py']
  exclude_extensions: [456, '.js']
""", encoding="utf-8")

    with patch('utils.validate_config', return_value=None):
        with patch('sourcecombine.validate_config', return_value=None):
            with patch('sourcecombine.find_and_combine_files', return_value=mock_stats) as mock_combine:
                with patch.object(sys, 'argv', ['sourcecombine.py', str(config_file)]):
                    main()

    args, _ = mock_combine.call_args
    config = args[0]
    assert config['search']['effective_allowed_extensions'] == ('.py',)
    assert config['search']['effective_exclude_extensions'] == ('.js',)

def test_pairing_extension_normalization_edge_cases(temp_cwd, mock_stats):
    config_file = temp_cwd / "config.yml"
    config_file.write_text("""
search:
  root_folders: ['.']
pairing:
  enabled: true
  source_extensions: [789, 'cpp']
  header_extensions: ['.h']
""", encoding="utf-8")

    with patch('utils.validate_config', return_value=None):
        with patch('sourcecombine.validate_config', return_value=None):
            with patch('sourcecombine.find_and_combine_files', return_value=mock_stats) as mock_combine:
                with patch.object(sys, 'argv', ['sourcecombine.py', str(config_file)]):
                    main()

    args, _ = mock_combine.call_args
    config = args[0]
    assert '.cpp' in config['search']['effective_allowed_extensions']
    assert '.h' in config['search']['effective_allowed_extensions']

def test_extract_files_content_is_none(tmp_path, caplog):
    output_dir = tmp_path / "extracted"
    content = '[{"path": "test.txt", "content": null}]'

    with caplog.at_level(logging.INFO):
        stats = extract_files(content, str(output_dir))

    assert "Skipping extraction for file without content: test.txt" in caplog.text

def test_execution_summary_secondary_tokens(capsys):
    stats = {
        'total_files': 1,
        'total_discovered': 1,
        'total_size_bytes': 500,
        'total_lines': 50,
        'total_tokens': 100,
        'top_files': [
            (100, 500, "dir/file.py", "OK", 50)
        ],
        'files_by_language': {'python': 1},
        'tokens_by_language': {'python': 100},
        'lines_by_language': {'python': 50},
        'size_by_language': {'python': 500},
    }
    args = MagicMock()
    args.dry_run = False
    args.estimate_tokens = False
    args.list_files = False
    args.tree = False
    args.extract = True
    args.apply_in_place = False

    with patch('shutil.get_terminal_size', return_value=MagicMock(columns=120)):
        with patch('sourcecombine._get_primary_metric', return_value='lines'):
            _print_execution_summary(
                stats, args, pairing_enabled=False, destination_desc="to 'out.txt'"
            )
            out, err = capsys.readouterr()
            assert "TOKENS" in err
            assert "100" in err
            assert "LINES" in err
            assert "dir/file.py" in err

def test_execution_summary_lang_lines_only(capsys):
    stats = {
        'total_files': 1,
        'total_discovered': 1,
        'total_size_bytes': 500,
        'total_lines': 50,
        'total_tokens': 0,
        'top_files': [
            (0, 500, "dir/file.py", "OK", 50)
        ],
        'files_by_language': {'python': 1},
        'tokens_by_language': {'python': 0},
        'lines_by_language': {'python': 50},
        'size_by_language': {'python': 500},
    }
    args = MagicMock()
    args.dry_run = False
    args.estimate_tokens = False
    args.list_files = False
    args.tree = False
    args.extract = True
    args.apply_in_place = False

    with patch('shutil.get_terminal_size', return_value=MagicMock(columns=120)):
        _print_execution_summary(
            stats, args, pairing_enabled=False, destination_desc="to 'out.txt'"
        )
        out, err = capsys.readouterr()
        assert "Languages (by lines)" in err
        assert "50" in err

def test_execution_summary_footer_truncation(capsys):
    stats = {
        'total_files': 1,
        'total_discovered': 1,
        'total_size_bytes': 100,
        'total_lines': 10,
        'total_tokens': 20,
        'top_files': [],
    }
    args = MagicMock()
    args.dry_run = False
    args.estimate_tokens = False
    args.list_files = False
    args.tree = False
    args.extract = True
    args.apply_in_place = False

    long_path = "to " + "/some/very/long/path/" * 10
    with patch('shutil.get_terminal_size', return_value=MagicMock(columns=50)):
        _print_execution_summary(
            stats, args, pairing_enabled=False, destination_desc=long_path
        )
        out, err = capsys.readouterr()
        # Verify that output was generated and contains truncated top header
        assert "EXTRACTION SUCCESS" in err
        assert "..." in err
