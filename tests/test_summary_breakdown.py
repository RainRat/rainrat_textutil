from unittest.mock import MagicMock
import sys
import sourcecombine
import io
import re

def test_summary_filtering_breakdown(monkeypatch, capsys):
    # Mock stats with various filtering reasons
    stats = {
        'total_files': 10,
        'total_discovered': 25,
        'total_size_bytes': 1024 * 50,
        'files_by_extension': {'.py': 10},
        'filter_reasons': {
            'binary': 5,
            'too_large': 3,
            'excluded': 2,
            'budget_limit': 5
        },
        'total_tokens': 1000,
        'token_count_is_approx': False
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

    # Check for main headers
    assert "=== Execution Summary ===" in stderr
    # Use regex to be more robust against exact space counts
    assert re.search(r"Included:\s+10", stderr)
    assert re.search(r"Filtered:\s+15", stderr)
    assert re.search(r"Total:\s+25", stderr)

    # Check for breakdown
    # The formatting is: 6 spaces, then '- ', then label (width 18), then count (width 12)
    # Binary file (11 chars) -> 7 spaces padding + 11 spaces padding for '5' = 18 spaces
    assert re.search(r"-\s+Binary file\s+5", stderr)
    assert re.search(r"-\s+Token budget limit\s+5", stderr)
    assert re.search(r"-\s+Above maximum size\s+3", stderr)
    assert re.search(r"-\s+Excluded by pattern\s+2", stderr)

    assert "      - Binary file" in stderr

def test_summary_no_filtering_breakdown_if_zero(monkeypatch, capsys):
    stats = {
        'total_files': 10,
        'total_discovered': 10,
        'total_size_bytes': 1024 * 50,
        'files_by_extension': {'.py': 10},
        'filter_reasons': {
            'binary': 5
        },
        'total_tokens': 1000,
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

    assert re.search(r"Included:\s+10", stderr)
    assert re.search(r"Filtered:\s+0", stderr)
    assert "- Binary file" not in stderr
