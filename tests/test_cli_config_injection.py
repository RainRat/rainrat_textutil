import sys
import os
import logging
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
import yaml

# Adjust sys.path to include the project root
sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

from sourcecombine import main, find_and_combine_files, InvalidConfigError, _generate_tree_string

@pytest.fixture
def temp_cwd(tmp_path):
    """Context manager to change current working directory."""
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(original_cwd)

@pytest.fixture
def mock_stats():
    return {
        'total_files': 0,
        'total_discovered': 0,
        'total_size_bytes': 0,
        'files_by_extension': {},
        'total_tokens': 0,
        'token_count_is_approx': False,
        'top_files': [],
        'filter_reasons': {}
    }

def test_cli_exclude_file_filters_is_none(temp_cwd, mock_stats):
    """Test --exclude-file when 'filters' is null in config (covers line 1849)."""
    config_file = temp_cwd / "config.yml"
    config_file.write_text("filters: null\nsearch: {root_folders: ['.']}", encoding="utf-8")

    with patch('sourcecombine.find_and_combine_files', return_value=mock_stats) as mock_combine:
        with patch.object(sys, 'argv', ['sourcecombine.py', str(config_file), '--exclude-file', 'foo.py']):
            main()

    args, _ = mock_combine.call_args
    config = args[0]
    assert isinstance(config['filters'], dict)
    assert 'foo.py' in config['filters']['exclusions']['filenames']

def test_cli_exclude_file_exclusions_is_none(temp_cwd, mock_stats):
    """Test --exclude-file when 'filters.exclusions' is null in config (covers line 1853)."""
    config_file = temp_cwd / "config.yml"
    config_file.write_text("filters: {exclusions: null}\nsearch: {root_folders: ['.']}", encoding="utf-8")

    with patch('sourcecombine.find_and_combine_files', return_value=mock_stats) as mock_combine:
        with patch.object(sys, 'argv', ['sourcecombine.py', str(config_file), '--exclude-file', 'foo.py']):
            main()

    args, _ = mock_combine.call_args
    config = args[0]
    assert isinstance(config['filters']['exclusions'], dict)
    assert 'foo.py' in config['filters']['exclusions']['filenames']

def test_cli_exclude_file_filenames_is_none(temp_cwd, mock_stats):
    """Test --exclude-file when 'filters.exclusions.filenames' is null in config (covers line 1858)."""
    config_file = temp_cwd / "config.yml"
    config_file.write_text("filters: {exclusions: {filenames: null}}\nsearch: {root_folders: ['.']}", encoding="utf-8")

    with patch('sourcecombine.find_and_combine_files', return_value=mock_stats) as mock_combine:
        with patch.object(sys, 'argv', ['sourcecombine.py', str(config_file), '--exclude-file', 'foo.py']):
            main()

    args, _ = mock_combine.call_args
    config = args[0]
    assert isinstance(config['filters']['exclusions']['filenames'], list)
    assert 'foo.py' in config['filters']['exclusions']['filenames']

def test_cli_exclude_folder_folders_is_none(temp_cwd, mock_stats):
    """Test --exclude-folder when 'filters.exclusions.folders' is null in config (covers line 1868)."""
    config_file = temp_cwd / "config.yml"
    config_file.write_text("filters: {exclusions: {folders: null}}\nsearch: {root_folders: ['.']}", encoding="utf-8")

    with patch('sourcecombine.find_and_combine_files', return_value=mock_stats) as mock_combine:
        with patch.object(sys, 'argv', ['sourcecombine.py', str(config_file), '--exclude-folder', 'bar/']):
            main()

    args, _ = mock_combine.call_args
    config = args[0]
    assert isinstance(config['filters']['exclusions']['folders'], list)
    assert 'bar/' in config['filters']['exclusions']['folders']

def test_cli_include_filters_is_none(temp_cwd, mock_stats):
    """Test --include when 'filters' is null in config (covers line 1879)."""
    config_file = temp_cwd / "config.yml"
    config_file.write_text("filters: null\nsearch: {root_folders: ['.']}", encoding="utf-8")

    with patch('sourcecombine.find_and_combine_files', return_value=mock_stats) as mock_combine:
        with patch.object(sys, 'argv', ['sourcecombine.py', str(config_file), '--include', '*.txt']):
            main()

    args, _ = mock_combine.call_args
    config = args[0]
    assert isinstance(config['filters'], dict)
    assert '*.txt' in config['filters']['inclusion_groups']['_cli_includes']['filenames']

def test_cli_include_inclusion_groups_is_none(temp_cwd, mock_stats):
    """Test --include when 'filters.inclusion_groups' is null in config (covers line 1884)."""
    config_file = temp_cwd / "config.yml"
    config_file.write_text("filters: {inclusion_groups: null}\nsearch: {root_folders: ['.']}", encoding="utf-8")

    with patch('sourcecombine.find_and_combine_files', return_value=mock_stats) as mock_combine:
        with patch.object(sys, 'argv', ['sourcecombine.py', str(config_file), '--include', '*.txt']):
            main()

    args, _ = mock_combine.call_args
    config = args[0]
    assert isinstance(config['filters']['inclusion_groups'], dict)
    assert '*.txt' in config['filters']['inclusion_groups']['_cli_includes']['filenames']

def test_cli_max_tokens_filters_is_none(temp_cwd, mock_stats):
    """Test --max-tokens when 'filters' is null in config (covers line 1906-1907)."""
    config_file = temp_cwd / "config.yml"
    config_file.write_text("filters: null\nsearch: {root_folders: ['.']}", encoding="utf-8")

    with patch('sourcecombine.find_and_combine_files', return_value=mock_stats) as mock_combine:
        with patch.object(sys, 'argv', ['sourcecombine.py', str(config_file), '--max-tokens', '100']):
            main()

    args, _ = mock_combine.call_args
    config = args[0]
    assert config['filters']['max_total_tokens'] == 100

def test_cli_include_tree(temp_cwd, mock_stats):
    """Test --include-tree (covers line 1914)."""
    with patch('sourcecombine.find_and_combine_files', return_value=mock_stats) as mock_combine:
        with patch.object(sys, 'argv', ['sourcecombine.py', '--include-tree']):
            main()

    args, _ = mock_combine.call_args
    config = args[0]
    assert config['output']['include_tree'] is True

def test_cli_clipboard_desc(temp_cwd, caplog, mock_stats):
    """Test destination_desc for --clipboard (covers line 1975)."""
    caplog.set_level(logging.INFO)
    with patch.dict(sys.modules, {'pyperclip': MagicMock()}):
        with patch('sourcecombine.find_and_combine_files', return_value=mock_stats):
            with patch.object(sys, 'argv', ['sourcecombine.py', '--clipboard']):
                main()

    assert "to clipboard" in caplog.text

def test_cli_estimate_tokens_output(temp_cwd, caplog, mock_stats):
    """Test log message for --estimate-tokens (covers line 1995)."""
    caplog.set_level(logging.INFO)
    with patch('sourcecombine.find_and_combine_files', return_value=mock_stats):
        with patch.object(sys, 'argv', ['sourcecombine.py', '--estimate-tokens']):
            main()

    assert "Output: Token estimation only (no files will be written)" in caplog.text

def test_main_invalid_config_validation_hit_1835(temp_cwd, caplog):
    """Test InvalidConfigError in main() at line 1835."""
    config_file = temp_cwd / "dummy.yml"
    config_file.write_text("search: {root_folders: ['.']}", encoding="utf-8")

    # Patch validate_config where it's used in sourcecombine.main
    with patch('sourcecombine.validate_config', side_effect=InvalidConfigError("Forced validation error")):
        with patch.object(sys, 'argv', ['sourcecombine.py', str(config_file)]):
            with pytest.raises(SystemExit) as excinfo:
                main()

    assert excinfo.value.code == 1
    assert "The configuration is not valid: Forced validation error" in caplog.text

def test_cli_extract_file_hit_1727(temp_cwd):
    """Test --extract with a file target (covers lines 1727-1728)."""
    input_file = temp_cwd / "combined.json"
    input_file.write_text('[{"path": "test.txt", "content": "hello"}]', encoding="utf-8")

    output_dir = temp_cwd / "out"

    with patch.object(sys, 'argv', ['sourcecombine.py', '--extract', str(input_file), '-o', str(output_dir)]):
        with pytest.raises(SystemExit) as excinfo:
            main()

    assert excinfo.value.code == 0
    assert (output_dir / "test.txt").read_text(encoding="utf-8") == "hello"

def test_generate_tree_string_metadata_gap_850(temp_cwd):
    """Test gap at line 850 in _generate_tree_string."""
    # Use relative path to avoid OS portability issues with absolute paths
    root = Path("app_root").resolve()
    f1 = root / "f1.txt"
    paths = [f1]

    # Metadata has something but NOT for f1.txt
    metadata = {root / "other.txt": {'size': 100}}

    res = _generate_tree_string(paths, root, metadata=metadata)
    assert "f1.txt" in res

def test_find_and_combine_files_size_placeholder_approx_1326(temp_cwd, monkeypatch):
    """Test gap at line 1326 in find_and_combine_files."""
    root = temp_cwd / "root"
    root.mkdir()
    f1 = root / "f1.txt"
    f1.write_text("very long content")

    config = {
        'search': {'root_folders': [str(root)]},
        'filters': {'max_size_bytes': 1}, # Force size exclusion
        'output': {
            'format': 'text',
            'max_size_placeholder': "Skipped {{FILENAME}} ({{SIZE}})"
        }
    }

    # Force tiktoken to None for approx tokens
    monkeypatch.setattr('utils.tiktoken', None)

    stats = find_and_combine_files(
        config,
        output_path=str(temp_cwd / "out.txt"),
        estimate_tokens=True
    )

    assert stats['token_count_is_approx'] is True

def test_global_header_footer_tokens_approx_1385_1390(temp_cwd, monkeypatch):
    """Test gap at lines 1385 and 1390."""
    root = temp_cwd / "root"
    root.mkdir()
    (root / "f1.txt").write_text("hello")

    config = {
        'search': {'root_folders': [str(root)]},
        'output': {
            'format': 'text',
            'global_header_template': 'HEADER',
            'global_footer_template': 'FOOTER'
        }
    }

    monkeypatch.setattr('utils.tiktoken', None)

    stats = find_and_combine_files(
        config,
        output_path=str(temp_cwd / "out.txt"),
        estimate_tokens=True
    )
    assert stats['token_count_is_approx'] is True

def test_summary_high_budget_bar_2183(temp_cwd, mock_stats, capsys):
    """Test yellow budget bar when percent > 90% (line 2183)."""
    mock_stats['total_tokens'] = 95
    mock_stats['max_total_tokens'] = 100

    with patch('sourcecombine.find_and_combine_files', return_value=mock_stats):
        with patch.object(sys, 'argv', ['sourcecombine.py']):
             # We need to ensure isatty is True for colors to be applied
             with patch('sys.stderr.isatty', return_value=True):
                 with patch.dict(os.environ, {}, clear=True):
                     main()

    captured = capsys.readouterr()
    # Flexible assertion for progress bar and percentage
    assert "[#########-]" in captured.err
    assert "95.0%" in captured.err
    # Check for yellow color code (\x1b[33m or \033[33m)
    assert "\x1b[33m" in captured.err or "\033[33m" in captured.err

def test_summary_top_files_loop_2232(temp_cwd, mock_stats, capsys):
    """Test top_files loop in summary (lines 2232-2240)."""
    long_path = "very/long/path/to/some/file/that/should/be/truncated/eventually/file2.txt"
    mock_stats['top_files'] = [
        (100, 1000, "file1.txt"),
        (200, 2000, long_path)
    ]

    with patch('sourcecombine.find_and_combine_files', return_value=mock_stats):
        with patch.object(sys, 'argv', ['sourcecombine.py']):
            main()

    captured = capsys.readouterr()
    assert "file1.txt" in captured.err
    # Check for truncation of long path (now truncated at 40 chars)
    assert "very/long/path/to/some/file/that/should/..." in captured.err
    assert "200" in captured.err
