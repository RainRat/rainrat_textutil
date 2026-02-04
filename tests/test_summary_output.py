from unittest.mock import MagicMock
import sys
import sourcecombine
import io

def test_summary_printing(monkeypatch, capsys):
    # Mock stats
    stats = {
        'total_files': 123,
        'total_discovered': 150,
        'total_size_bytes': 1024 * 1024 * 1.5, # 1.5 MB
        'files_by_extension': {
            '.py': 10, '.txt': 5, '.md': 3, '.c': 1, '.h': 1,
            '.cpp': 1, '.hpp': 1, '.java': 1, '.js': 1, '.ts': 1,
            '.css': 1, '.html': 1, '.json': 1, '.xml': 1, '.yml': 1
        },
        'total_tokens': 5000,
        'token_count_is_approx': True,
        'excluded_folder_count': 2
    }

    # Mock args
    args = MagicMock()
    args.dry_run = False
    args.estimate_tokens = False
    args.list_files = False
    args.tree = False

    # Mock stderr to capture output (capsys works too but let's be explicit if needed)
    # Actually capsys captures sys.stderr

    # Force NO_COLOR to avoid ANSI codes in test check
    monkeypatch.setenv("NO_COLOR", "1")

    sourcecombine._print_execution_summary(stats, args, pairing_enabled=False)

    captured = capsys.readouterr()
    stderr = captured.err

    assert "=== Execution Summary ===" in stderr
    assert "Included:   123" in stderr
    assert "Filtered:   27" in stderr
    assert "Total:      150 discovered" in stderr
    assert "Total Size: 1.50 MB" in stderr
    assert "Extensions:" in stderr
    assert "Folders:    2" in stderr
    assert "Tokens:     ~5,000" in stderr

    # Check wrapping (heuristic: check if .yml is on a new line or far right)
    # The list is long, so it should wrap.
    # We can check that the output contains the indent for the second line
    # The new grid layout uses 4 spaces indentation for the lines.
    assert "\n    " in stderr

def test_summary_printing_dry_run(monkeypatch, capsys):
    stats = {
        'total_files': 0,
        'total_size_bytes': 0,
        'files_by_extension': {},
        'total_tokens': 0,
        'token_count_is_approx': False,
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

    assert "=== Dry-Run Summary ===" in stderr
    assert "Included:   0" in stderr
    # Token count should NOT appear in dry run unless requested (but logic says: not dry_run or estimate_tokens)
    # Wait, check logic: `if not pairing_enabled and (not args.dry_run or args.estimate_tokens)`
    # So if dry_run=True and estimate=False, it should NOT show tokens.
    assert "Tokens:" not in stderr
