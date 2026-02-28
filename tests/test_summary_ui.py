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

    # Check redesign of Largest Files: tokens should come first
    # 500 should be right-aligned in 11 columns, followed by percentage and size
    # With default 80 column terminal, large_file.py should not be truncated.
    assert "        500 ( 50.0%)  (1.95 KB)     large_file.py" in stderr
    assert "        300 ( 30.0%)  (1,000.00 B)  medium_file.py" in stderr

    # Check header data hint includes "tokens"
    assert "[1,000 tokens]" in stderr

    # Should NOT have the old format
    assert "large_file.py                                          500" not in stderr

def test_summary_total_found_label(monkeypatch, capsys):
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

    assert "Total Found:                    10" in stderr
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


def test_truncate_path():
    from sourcecombine import _truncate_path
    path = "a/very/long/path/to/a/file/with/a/long/name.py"
    # max_width 20: "a/very/...ng/name.py"
    # Path is 44 chars.
    # tail_len = min(44//2, 20//2) = 10
    # head_len = 20 - 10 - 3 = 7
    # path[:7] = "a/very/"
    # path[-10:] = "ng/name.py"
    # Result: "a/very/...ng/name.py"
    assert _truncate_path(path, 20) == "a/very/...ng/name.py"
    assert len(_truncate_path(path, 20)) == 20

    # Short width
    # 10 - 3 = 7
    # path[:7] = "a/very/"
    assert _truncate_path(path, 10) == "a/very/..."

    # No truncation needed
    assert _truncate_path("short.py", 20) == "short.py"


def test_summary_path_truncation(monkeypatch, capsys):
    stats = {
        'total_files': 1,
        'total_size_bytes': 1000,
        'files_by_extension': {'.py': 1},
        'total_tokens': 1000,
        'token_count_is_approx': False,
        'top_files': [
            (1000, 1000, 'a/very/long/path/that/needs/truncation/file.py'),
        ]
    }
    args = MagicMock()
    args.dry_run = False
    args.estimate_tokens = True
    args.list_files = False
    args.tree = False

    monkeypatch.setenv("NO_COLOR", "1")

    # Mock terminal size to 60 columns
    # path_width = max(30, 60 - 40) = 30
    import shutil
    original_get_terminal_size = shutil.get_terminal_size
    shutil.get_terminal_size = lambda fallback=(80, 20): MagicMock(columns=60)

    # We also need to ensure isatty returns True for the mock to be used
    monkeypatch.setattr(sys.stderr, "isatty", lambda: True)

    try:
        sourcecombine._print_execution_summary(stats, args, pairing_enabled=False)
    finally:
        shutil.get_terminal_size = original_get_terminal_size

    captured = capsys.readouterr()
    stderr = captured.err

    # path_width 30. Path is 46 chars.
    # tail_len = min(46//2, 30//2) = 15
    # head_len = 30 - 15 - 3 = 12
    # path[:12] = 'a/very/long/'
    # path[-15:] = 'ncation/file.py'
    # Result: 'a/very/long/...ncation/file.py'
    assert "a/very/long/...ncation/file.py" in stderr
