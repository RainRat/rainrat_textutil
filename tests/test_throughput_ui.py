import sys; import os; from pathlib import Path; sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

from unittest.mock import MagicMock
import sys
import os
from pathlib import Path
import sourcecombine

def test_throughput_with_tokens(monkeypatch, capsys):
    # Mock stats
    stats = {
        'total_files': 10,
        'total_discovered': 10,
        'total_size_bytes': 10240, # 10 KB
        'files_by_extension': {'.py': 10},
        'total_tokens': 5000,
        'token_count_is_approx': False,
        'top_files': []
    }

    # Mock args
    args = MagicMock()
    args.dry_run = False
    args.estimate_tokens = True
    args.list_files = False
    args.tree = False
    args.extract = False

    # Force NO_COLOR to avoid ANSI codes in test check
    monkeypatch.setenv("NO_COLOR", "1")

    # Call with duration
    sourcecombine._print_execution_summary(stats, args, pairing_enabled=False, duration=2.0)

    captured = capsys.readouterr()
    stderr = captured.err

    # Check for Throughput line
    assert "Throughput:" in stderr
    # 10 files / 2.0s = 5.0 files/s
    assert "5.0 files/s" in stderr
    # 10 KB / 2.0s = 5.00 KB/s
    assert "5.00 KB/s" in stderr
    # 5000 tokens / 2.0s = 2500 tokens/s
    assert "2,500 tokens/s" in stderr

    # Check parenthetical format
    assert "(5.00 KB/s • 2,500 tokens/s)" in stderr

def test_throughput_without_tokens(monkeypatch, capsys):
    # Mock stats
    stats = {
        'total_files': 10,
        'total_discovered': 10,
        'total_size_bytes': 10240, # 10 KB
        'files_by_extension': {'.py': 10},
        'total_tokens': 0,
        'token_count_is_approx': False,
        'top_files': []
    }

    # Mock args
    args = MagicMock()
    args.dry_run = False
    args.estimate_tokens = False
    args.list_files = False
    args.tree = False
    args.extract = False

    # Force NO_COLOR to avoid ANSI codes in test check
    monkeypatch.setenv("NO_COLOR", "1")

    # Call with duration
    sourcecombine._print_execution_summary(stats, args, pairing_enabled=False, duration=2.0)

    captured = capsys.readouterr()
    stderr = captured.err

    # Check for Throughput line
    assert "Throughput:" in stderr
    assert "5.0 files/s" in stderr
    assert "(5.00 KB/s)" in stderr
    assert "tokens/s" not in stderr
