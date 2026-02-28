from unittest.mock import MagicMock, patch
import sys
import os
from pathlib import Path

# Adjust sys.path to include the project root
sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

import sourcecombine
import pytest

def test_summary_redesign_largest_files(monkeypatch, capsys):
    # Mock stats
    stats = {
        'total_files': 10,
        'total_size_bytes': 10000,
        'files_by_extension': {'.py': 5, '.md': 5},
        'total_tokens': 2500,
        'token_count_is_approx': False,
        'top_files': [
            (1000, 5000, "a/very/long/path/to/some/file/that/should/trigger/truncation/file.py"),
            (500, 2000, "short.py"),
        ]
    }

    # Mock args
    args = MagicMock()
    args.dry_run = False
    args.estimate_tokens = True
    args.list_files = False
    args.tree = False

    # Force NO_COLOR to avoid ANSI codes in test check
    monkeypatch.setenv("NO_COLOR", "1")

    sourcecombine._print_execution_summary(stats, args, pairing_enabled=False)

    captured = capsys.readouterr()
    stderr = captured.err

    # Check for the new sections
    assert "TOKEN ESTIMATION COMPLETE" in stderr
    assert "Largest Files" in stderr
    
    # Check for values
    assert "1,000" in stderr
    assert "40.0%" in stderr # (1000/2500)
    assert "4.88 KB" in stderr # (5000 bytes)
    assert "500" in stderr
    assert "20.0%" in stderr # (500/2500)
    assert "1.95 KB" in stderr # (2000 bytes)

    # Check for truncated path
    assert "a/very/long/path/...r/truncation/file.py" in stderr

def test_summary_printing(monkeypatch, capsys):
    # Mock stats
    stats = {
        'total_files': 123,
        'total_size_bytes': 1024 * 1024 * 1.5, # 1.5 MB
        'files_by_extension': {
            '.py': 10, '.txt': 5, '.md': 3, '.c': 1, '.h': 1,
            '.cpp': 1, '.hpp': 1, '.java': 1, '.js': 1, '.ts': 1,
            '.css': 1, '.html': 1, '.json': 1, '.xml': 1, '.yml': 1
        },
        'total_tokens': 5000,
        'token_count_is_approx': True,
        'excluded_folder_count': 2,
        'top_files': []
    }

    # Mock args
    args = MagicMock()
    args.dry_run = False
    args.estimate_tokens = False
    args.list_files = False
    args.tree = False

    # Force NO_COLOR to avoid ANSI codes in test check
    monkeypatch.setenv("NO_COLOR", "1")

    sourcecombine._print_execution_summary(stats, args, pairing_enabled=False)

    captured = capsys.readouterr()
    stderr = captured.err

    assert "SUCCESS: Combined 123 files" in stderr
    assert "Included:                      123" in stderr
    assert "Total Size:                1.50 MB" in stderr
    assert "Extensions" in stderr
    assert "Excluded Folders:                2" in stderr
    assert "Token Count:                ~5,000" in stderr

    # Check wrapping (grid layout)
    assert "\n    " in stderr

def test_summary_printing_dry_run(monkeypatch, capsys):
    stats = {
        'total_files': 0,
        'total_size_bytes': 0,
        'files_by_extension': {},
        'total_tokens': 0,
        'token_count_is_approx': False,
        'top_files': []
    }
    args = MagicMock()
    args.dry_run = True
    args.estimate_tokens = False
    args.list_files = False
    args.tree = False

    monkeypatch.setenv("NO_COLOR", "1")

    sourcecombine._print_execution_summary(stats, args, pairing_enabled=False)

    captured = capsys.readouterr()
    stderr = captured.err

    assert "DRY RUN COMPLETE" in stderr
    assert "Included:                        0" in stderr
    assert "Token Count" not in stderr

def test_output_truncated_warning(capsys):
    """Test summary shows truncation warning (line 2265)."""
    stats = {
        'total_files': 1,
        'total_size_bytes': 10,
        'files_by_extension': {'.txt': 1},
        'token_limit_reached': True,
        'total_tokens': 100,
        'max_total_tokens': 50,
        'top_files': []
    }

    from sourcecombine import _print_execution_summary
    args = MagicMock()
    args.list_files = False
    args.tree = False

    with patch.dict(os.environ, {"NO_COLOR": "1"}):
        _print_execution_summary(stats, args, pairing_enabled=False)

    captured = capsys.readouterr()
    assert "WARNING: Output truncated due to token limit." in captured.err

def test_limit_bar_no_color(capsys):
    """Test limit bar with NO_COLOR=1 (line 2321)."""
    stats = {
        'total_files': 1,
        'total_size_bytes': 10,
        'files_by_extension': {'.txt': 1},
        'total_tokens': 50,
        'max_total_tokens': 100,
        'top_files': []
    }

    from sourcecombine import _print_execution_summary
    args = MagicMock()
    args.list_files = False
    args.tree = False

    with patch.dict(os.environ, {"NO_COLOR": "1"}):
        _print_execution_summary(stats, args, pairing_enabled=False)

    captured = capsys.readouterr()
    assert "Token Limit Usage:" in captured.err
    assert "[#####-----]" in captured.err

def test_summary_terminal_size_fallback(capsys):
    """Test terminal size fallback in extensions grid (lines 2351-2354)."""
    stats = {
        'total_files': 1,
        'total_size_bytes': 10,
        'files_by_extension': {'.txt': 1},
        'top_files': []
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
