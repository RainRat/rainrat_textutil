import sys
import os
import logging
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
import yaml

# Adjust sys.path to include the project root
sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

from sourcecombine import main, InvalidConfigError

@pytest.fixture
def temp_cwd(tmp_path):
    """Context manager to change current working directory."""
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(original_cwd)

def test_main_with_compact_flag_no_processing(temp_cwd):
    """Test main() with --compact flag when processing config is missing (line 1907)."""
    (temp_cwd / "test.txt").write_text("content", encoding="utf-8")

    # Mock load_and_validate_config AND validate_config to return a dict without 'processing'
    config = {'search': {'root_folders': ['.']}}
    with patch('sourcecombine.load_and_validate_config', return_value=config):
        with patch('sourcecombine.validate_config'):
            with patch('sourcecombine.find_and_combine_files') as mock_combine:
                mock_combine.return_value = {'total_files': 1, 'total_tokens': 10, 'files_by_extension': {'.txt': 1}}
                with patch.object(sys, 'argv', ['sourcecombine.py', 'config.yml', '--compact']):
                    main()

    args, _ = mock_combine.call_args
    config = args[0]
    assert config['processing']['compact_whitespace'] is True

def test_main_with_toc_flag(temp_cwd):
    """Test main() with --toc flag to cover line 1900 (formerly 1907)."""
    (temp_cwd / "test.txt").write_text("content", encoding="utf-8")

    # Mock find_and_combine_files to verify the config
    with patch('sourcecombine.find_and_combine_files') as mock_combine:
        mock_combine.return_value = {'total_files': 1, 'total_tokens': 10, 'files_by_extension': {'.txt': 1}}
        with patch.object(sys, 'argv', ['sourcecombine.py', '.', '--toc']):
            main()

    args, _ = mock_combine.call_args
    config = args[0]
    assert config['output']['table_of_contents'] is True

def test_main_invalid_config_error_handling(temp_cwd, caplog):
    """Test main() handles InvalidConfigError during find_and_combine_files (lines 2044-2046)."""
    (temp_cwd / "test.txt").write_text("content", encoding="utf-8")

    # Force find_and_combine_files to raise InvalidConfigError
    with patch('sourcecombine.find_and_combine_files', side_effect=InvalidConfigError("Forced Error")):
        with patch.object(sys, 'argv', ['sourcecombine.py', '.']):
            with pytest.raises(SystemExit) as excinfo:
                main()

    assert excinfo.value.code == 1
    assert "Forced Error" in caplog.text

def test_output_truncated_warning(temp_cwd, capsys):
    """Test summary shows truncation warning (line 2265)."""
    stats = {
        'total_files': 1,
        'total_size_bytes': 10,
        'files_by_extension': {'.txt': 1},
        'budget_exceeded': True,
        'total_tokens': 100,
        'max_total_tokens': 50
    }

    from sourcecombine import _print_execution_summary
    args = MagicMock()
    args.list_files = False
    args.tree = False

    with patch.dict(os.environ, {"NO_COLOR": "1"}):
        _print_execution_summary(stats, args, pairing_enabled=False)

    captured = capsys.readouterr()
    assert "WARNING: Output truncated due to token budget." in captured.err

def test_budget_bar_no_color(temp_cwd, capsys):
    """Test budget bar with NO_COLOR=1 (line 2321)."""
    stats = {
        'total_files': 1,
        'total_size_bytes': 10,
        'files_by_extension': {'.txt': 1},
        'total_tokens': 50,
        'max_total_tokens': 100
    }

    from sourcecombine import _print_execution_summary
    args = MagicMock()
    args.list_files = False
    args.tree = False

    with patch.dict(os.environ, {"NO_COLOR": "1"}):
        _print_execution_summary(stats, args, pairing_enabled=False)

    captured = capsys.readouterr()
    assert "Budget Usage:" in captured.err
    assert "[#####-----]" in captured.err

def test_summary_terminal_size_fallback(temp_cwd, capsys):
    """Test terminal size fallback in extensions grid (lines 2351-2354)."""
    stats = {
        'total_files': 1,
        'total_size_bytes': 10,
        'files_by_extension': {'.txt': 1}
    }

    from sourcecombine import _print_execution_summary
    args = MagicMock()
    args.list_files = False
    args.tree = False

    with patch('sys.stderr.isatty', return_value=True):
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            with patch('shutil.get_terminal_size', side_effect=Exception("Terminal error")):
                _print_execution_summary(stats, args, pairing_enabled=False)

    captured = capsys.readouterr()
    assert "Extensions" in captured.err
    assert ".txt:     1" in captured.err

def test_global_header_footer_token_approx_single_mode(temp_cwd, monkeypatch):
    """Test token approximation of global header/footer in single mode (lines 1392, 1397)."""
    import utils
    from sourcecombine import find_and_combine_files

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

    # Force tiktoken to None and ensure no budgeting pass is performed
    monkeypatch.setattr(utils, "tiktoken", None)

    stats = find_and_combine_files(
        config,
        output_path=str(temp_cwd / "out.txt"),
        estimate_tokens=False
    )

    assert stats['token_count_is_approx'] is True
