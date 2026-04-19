import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

# Adjust sys.path to include the project root
sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

import sourcecombine

def test_summary_new_features(monkeypatch, capsys):
    # Mock stats
    stats = {
        'total_files': 10,
        'total_discovered': 10,
        'total_size_bytes': 1024,
        'files_by_extension': {'.py': 10},
        'total_tokens': 1000,
        'total_lines': 500,
        'top_files': []
    }

    # Mock args for standard run without limits
    args = MagicMock()
    args.dry_run = False
    args.estimate_tokens = False
    args.list_files = False
    args.tree = False
    args.extract = False
    args.apply_in_place = False
    args.max_files = 0
    args.max_total_tokens = 0
    args.max_total_size_bytes = 0
    args.max_total_lines = 0

    monkeypatch.setenv("NO_COLOR", "1")

    # 1. Test "Execution" header (no limits)
    sourcecombine._print_execution_summary(stats, args, pairing_enabled=False, duration=1.0)
    captured = capsys.readouterr()
    assert "Execution" in captured.err
    assert "Time and Limits" not in captured.err
    # Throughput check
    assert "500 lines/s" in captured.err

    # 2. Test "Time and Limits" header (with limit)
    args.limit = 100
    sourcecombine._print_execution_summary(stats, args, pairing_enabled=False, duration=1.0)
    captured = capsys.readouterr()
    assert "Time and Limits" in captured.err
    assert "Execution" not in captured.err

    # 3. Test "Updated in-place" verb
    args.apply_in_place = True
    args.max_files = 0
    sourcecombine._print_execution_summary(stats, args, pairing_enabled=False)
    captured = capsys.readouterr()
    assert "SUCCESS: Updated in-place 10 files" in captured.err

    # 4. Test "Would update in-place" verb (dry run)
    args.dry_run = True
    sourcecombine._print_execution_summary(stats, args, pairing_enabled=False)
    captured = capsys.readouterr()
    assert "DRY RUN COMPLETE: Would update in-place 10 files" in captured.err

if __name__ == "__main__":
    import pytest
    pytest.main([__file__])
