import sys
import os
import logging
import shutil
import subprocess
import runpy
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

# Adjust sys.path to include the project root
sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

from sourcecombine import main, find_and_combine_files, InvalidConfigError, _print_execution_summary

@pytest.fixture
def mock_stats():
    return {
        'total_files': 1,
        'total_discovered': 2,
        'total_size_bytes': 100,
        'files_by_extension': {'.txt': 1},
        'total_tokens': 50,
        'token_count_is_approx': False,
        'top_files': [(50, 100, 'file.txt')],
        'filter_reasons': {},
        'max_total_tokens': 100,
        'budget_exceeded': False
    }

def test_summary_budget_exceeded_warning(mock_stats, capsys):
    """Test line 2254: budget_exceeded warning."""
    mock_stats['budget_exceeded'] = True
    args = MagicMock()
    args.dry_run = False
    args.estimate_tokens = False
    args.list_files = False
    args.tree = False

    with patch('sys.stderr.isatty', return_value=True):
        with patch.dict(os.environ, {}, clear=True):
            _print_execution_summary(mock_stats, args, pairing_enabled=False)

    captured = capsys.readouterr()
    assert "WARNING: Output truncated due to token budget" in captured.err

def test_main_invalid_config_error_handling(monkeypatch, caplog):
    """Test lines 2033-2035: InvalidConfigError in main()."""
    # Trigger an InvalidConfigError during find_and_combine_files
    # We must provide a config file path so that load_and_validate_config is called.
    monkeypatch.setattr(sys, 'argv', ['sourcecombine.py', 'config.yml', '--output', '-', '--include', '*.txt'])
    # Need to mock the config to have pairing enabled
    mock_config = {
        'pairing': {'enabled': True},
        'output': {'folder': '-', 'file': None},
        'search': {'root_folders': ['.']}
    }
    with patch('sourcecombine.load_and_validate_config', return_value=mock_config):
        with pytest.raises(SystemExit) as excinfo:
            main()

    assert excinfo.value.code == 1
    assert "Stdout output is not available in pairing mode" in caplog.text

def test_summary_terminal_size_exception(mock_stats, capsys):
    """Test lines 2340-2343: shutil.get_terminal_size exception."""
    args = MagicMock()
    args.dry_run = False
    args.estimate_tokens = False
    args.list_files = False
    args.tree = False

    with patch('sys.stderr.isatty', return_value=True):
        with patch('shutil.get_terminal_size', side_effect=Exception("Terminal error")):
            _print_execution_summary(mock_stats, args, pairing_enabled=False)

    captured = capsys.readouterr()
    assert "Execution Summary" in captured.err

def test_global_header_footer_approx_fallback(tmp_path, monkeypatch):
    """Test lines 1392, 1397: is_approx in global templates when budget pass skipped."""
    root = tmp_path / "root"
    root.mkdir()
    (root / "f1.txt").write_text("hello")

    config = {
        'search': {'root_folders': [str(root)]},
        'output': {
            'format': 'text',
            'global_header_template': 'HEADER',
            'global_footer_template': 'FOOTER'
        },
        'filters': {}
    }

    # Force tiktoken to None for approx tokens
    import utils
    monkeypatch.setattr(utils, 'tiktoken', None)

    stats = find_and_combine_files(
        config,
        output_path=str(tmp_path / "out.txt"),
        estimate_tokens=False
    )

    assert stats['token_count_is_approx'] is True

def test_summary_no_color_budget_usage(mock_stats, capsys):
    """Test line 2310: bar_color = "" when no color."""
    mock_stats['total_tokens'] = 50
    mock_stats['max_total_tokens'] = 100
    args = MagicMock()
    args.dry_run = False
    args.estimate_tokens = True
    args.list_files = False
    args.tree = False

    with patch('sys.stderr.isatty', return_value=False):
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            _print_execution_summary(mock_stats, args, pairing_enabled=False)

    captured = capsys.readouterr()
    assert "[#####-----]" in captured.err

def test_sourcecombine_main_entry():
    """Test line 2365: if __name__ == "__main__": main()."""
    with patch.object(sys, 'argv', ['sourcecombine.py', '--version']):
        with pytest.raises(SystemExit) as excinfo:
            runpy.run_path("sourcecombine.py", run_name="__main__")
        assert excinfo.value.code == 0
