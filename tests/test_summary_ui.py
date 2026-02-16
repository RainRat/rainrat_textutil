from unittest.mock import MagicMock
import sys
import sourcecombine
import pytest

def test_summary_redesign_largest_files(monkeypatch, capsys):
    # Mock stats
    stats = {
        'total_files': 10,
        'total_size_bytes': 1000,
        'files_by_extension': {'.py': 10},
        'total_tokens': 1000,
        'token_count_is_approx': False,
        'top_files': [
            (500, 2000, 'large_file.py'),
            (300, 1000, 'medium_file.py'),
        ]
    }

    # Mock args
    args = MagicMock()
    args.dry_run = False
    args.estimate_tokens = True
    args.list_files = False
    args.tree = False

    monkeypatch.setenv("NO_COLOR", "1")

    sourcecombine._print_execution_summary(stats, args, pairing_enabled=False)

    captured = capsys.readouterr()
    stderr = captured.err

    # Check redesign of Largest Files: tokens should come first, followed by size
    # 500 should be right-aligned in 10 columns (plus 4 spaces indent)
    assert "           500     (1.95 KB)  large_file.py" in stderr
    assert "           300  (1,000.00 B)  medium_file.py" in stderr
    # Should NOT have the old format
    assert "large_file.py                                          500" not in stderr

def test_summary_total_discovered_label(monkeypatch, capsys):
    stats = {
        'total_files': 5,
        'total_size_bytes': 500,
        'files_by_extension': {'.py': 5},
        'total_discovered': 10,
        'filter_reasons': {'excluded_folder': 2, 'extension': 5}
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

    assert "Total Discovered:               10" in stderr
    # excluded_folder should be skipped in breakdown
    assert "- excluded folder" not in stderr
    # extension should be present
    assert "- extension" in stderr

def test_summary_extension_grid_alignment(monkeypatch, capsys):
    stats = {
        'total_files': 10,
        'total_size_bytes': 1000,
        'files_by_extension': {'.py': 100, '.js': 5},
    }
    args = MagicMock()
    args.dry_run = False
    args.estimate_tokens = False
    args.list_files = False
    args.tree = False

    monkeypatch.setenv("NO_COLOR", "1")

    sourcecombine._print_execution_summary(stats, args, pairing_enabled=False)

    captured = capsys.readouterr()
    stderr = captured.err

    # Check right alignment of counts in extensions grid
    # .py:   100
    # .js:     5
    assert ".py:   100" in stderr
    assert ".js:     5" in stderr
