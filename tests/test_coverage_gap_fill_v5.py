import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
import os
import sys
import copy
from sourcecombine import InvalidConfigError

# Adjust sys.path to include the project root
sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

import sourcecombine
import utils

def test_collect_git_files_progress():
    """Target sourcecombine.py line 505: progress.update(1)."""
    mock_result = MagicMock()
    mock_result.stdout = "file1.txt\n"
    mock_progress = MagicMock()

    with patch('subprocess.run', return_value=mock_result):
        root = Path("/fake/root")
        sourcecombine.collect_git_files(root, progress=mock_progress)
        mock_progress.update.assert_called_with(1)

def test_token_count_is_approx_single_mode_loop(tmp_path):
    """Target sourcecombine.py line 2027: stats['token_count_is_approx'] = True in single mode loop."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("some content", encoding="utf-8")

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    config['search']['root_folders'] = [str(tmp_path)]
    # Ensure no other triggers for token_count_is_approx
    config['output']['include_tree'] = False
    config['output']['table_of_contents'] = False
    config['filters']['max_total_lines'] = 0
    config['filters']['max_total_tokens'] = 0

    with patch("utils.tiktoken", None):
        stats = sourcecombine.find_and_combine_files(
            config,
            output_path=str(tmp_path / "combined.txt")
        )
    assert stats['token_count_is_approx'] is True

def test_main_logging_initialization_gap():
    """Target sourcecombine.py lines 2364-2367: logger handler initialization."""
    with patch('sourcecombine.logging.getLogger') as mock_get_logger:
        mock_root = MagicMock()
        mock_root.handlers = []
        mock_get_logger.return_value = mock_root

        with patch('sourcecombine.logging.StreamHandler'):
            with patch('sourcecombine.CLILogFormatter'):
                # Use a valid command that doesn't exit early in parse_args
                with patch('sys.argv', ['sourcecombine.py', '.']):
                    with patch('sourcecombine.find_and_combine_files', side_effect=SystemExit(0)):
                        try:
                            sourcecombine.main()
                        except SystemExit:
                            pass
        assert mock_root.addHandler.called

def test_main_search_missing_injection():
    """Target sourcecombine.py line 2459: config['search'] = {} if missing."""
    with patch('sourcecombine.load_and_validate_config', return_value={'filters': {}}):
        with patch('sourcecombine.find_and_combine_files', return_value={}):
             with patch('sys.argv', ['sourcecombine.py', 'config.yml', '.']):
                try:
                    sourcecombine.main()
                except (SystemExit, Exception):
                    pass

def test_cli_injection_null_sections(tmp_path):
    """Target sourcecombine.py lines 2500, 2505, 2515, 2528."""
    config_file = tmp_path / "config.yml"
    config_content = """
filters:
  exclusions: null
  inclusion_groups: null
"""
    config_file.write_text(config_content)

    mock_stats = {'total_files': 0, 'total_discovered': 0, 'total_size_bytes': 0, 'files_by_extension': {}, 'total_tokens': 0, 'token_count_is_approx': False, 'top_files': [], 'filter_reasons': {}}

    with patch('sourcecombine.find_and_combine_files', return_value=mock_stats) as mock_find:
        with patch('sys.argv', ['sourcecombine.py', str(config_file), '.', '--exclude-file', 'f.py', '--exclude-folder', 'd/', '--include', '*.c']):
            try:
                sourcecombine.main()
            except SystemExit:
                pass

            args, _ = mock_find.call_args
            config = args[0]
            assert 'f.py' in config['filters']['exclusions']['filenames']
            assert 'd/' in config['filters']['exclusions']['folders']
            assert '_cli_includes' in config['filters']['inclusion_groups']

def test_utils_validation_gaps():
    """Target utils.py lines 375, 379, 449, 458, 461, 558, 562."""
    from utils import validate_config, InvalidConfigError

    with pytest.raises(InvalidConfigError, match="search.root_folders must be a list"):
        validate_config({'search': {'root_folders': 'not a list'}})

    with pytest.raises(InvalidConfigError, match="search.allowed_extensions must be a list"):
        validate_config({'search': {'allowed_extensions': 'not a list'}})

    with pytest.raises(InvalidConfigError, match="filters.exclusions must be a dictionary"):
        validate_config({'filters': {'exclusions': 'not a dict'}})

    with pytest.raises(InvalidConfigError, match="filters.inclusion_groups must be a dictionary"):
        validate_config({'filters': {'inclusion_groups': 'not a dict'}})

    with pytest.raises(InvalidConfigError, match="filters.inclusion_groups.test must be a dictionary"):
        validate_config({'filters': {'inclusion_groups': {'test': 'not a dict'}}})

    with pytest.raises(InvalidConfigError, match="pairing.source_extensions must be a list"):
        validate_config({'pairing': {'enabled': True, 'source_extensions': 'not a list'}})

    with pytest.raises(InvalidConfigError, match="pairing.header_extensions must be a list"):
        validate_config({'pairing': {'enabled': True, 'header_extensions': 'not a list'}})

def test_find_and_combine_files_invalid_config_error_handling():
    """Target sourcecombine.py lines 2790-2795."""
    with patch('sourcecombine.find_and_combine_files', side_effect=InvalidConfigError("Test error")):
        with patch('sys.argv', ['sourcecombine.py', '.']):
            with pytest.raises(SystemExit) as exc:
                sourcecombine.main()
            assert exc.value.code == 1

def test_print_execution_summary_terminal_size_exception():
    """Target sourcecombine.py line 3056: Exception in get_terminal_size."""
    mock_args = MagicMock()
    mock_args.extract = False
    mock_stats = {
        'total_files': 0,
        'files_by_extension': {}
    }
    with patch('shutil.get_terminal_size', side_effect=Exception("error")):
        with patch('sys.stderr', new=MagicMock()):
             sourcecombine._print_execution_summary(mock_stats, mock_args, False)

def test_main_config_validation_error_verbose(tmp_path):
    """Target sourcecombine.py line 2482: validation error with verbose."""
    config_file = tmp_path / "config.yml"
    config_file.write_text("search: {max_depth: -1}")
    with patch('sys.argv', ['sourcecombine.py', str(config_file), '.', '-v']):
        with patch('sourcecombine.find_and_combine_files'):
            with pytest.raises(SystemExit) as exc:
                sourcecombine.main()
            assert exc.value.code == 1

def test_main_max_total_size_invalid(caplog):
    """Target sourcecombine.py lines 2553-2559."""
    with patch('sys.argv', ['sourcecombine.py', '.', '--max-total-size', 'invalid']):
        with pytest.raises(SystemExit) as exc:
            sourcecombine.main()
        assert exc.value.code == 1
    assert "Invalid size value" in caplog.text

def test_main_max_total_lines_null_filters():
    """Target sourcecombine.py lines 2562-2564."""
    with patch('sourcecombine.load_and_validate_config', return_value={'filters': None, 'search': {'root_folders': ['.']}}):
        with patch('sourcecombine.find_and_combine_files', return_value={}):
            with patch('sys.argv', ['sourcecombine.py', 'config.yml', '--max-total-lines', '10']):
                try:
                    sourcecombine.main()
                except SystemExit:
                    pass

def test_line_limit_reached_warning_direct(capsys):
    """Target sourcecombine.py line 3111: Line limit warning in summary."""
    mock_stats = {
        'line_limit_reached': True,
        'total_files': 0,
        'files_by_extension': {}
    }
    mock_args = MagicMock()
    mock_args.extract = False

    with patch('sys.stderr.isatty', return_value=True):
        sourcecombine._print_execution_summary(mock_stats, mock_args, False)

    captured = capsys.readouterr()
    assert "WARNING: Output truncated due to total line limit." in captured.err
