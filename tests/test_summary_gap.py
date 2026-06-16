import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

# Adjust sys.path to include the project root
sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

import sourcecombine

def test_summary_extension_truncation(monkeypatch, capsys):
    long_ext = ".verylongextensionname"
    stats = {
        'total_files': 1,
        'total_discovered': 1,
        'total_size_bytes': 100,
        'files_by_language': {long_ext: 1},
        'tokens_by_language': {long_ext: 10},
        'total_tokens': 10,
        'token_count_is_approx': False,
        'top_files': []
    }

    args = MagicMock()
    args.dry_run = False
    args.estimate_tokens = True
    args.list_files = False
    args.tree = False
    args.extract = False
    args.format = 'text'

    monkeypatch.setenv("NO_COLOR", "1")

    sourcecombine._print_execution_summary(stats, args, pairing_enabled=False)

    captured = capsys.readouterr()
    stderr = captured.err

    # The redesigned table puts LANGUAGE at the end, and _truncate_path
    # might result in different ellipsis placement depending on width.
    # We check that it's truncated.
    assert ".verylo" in stderr and "name" in stderr and "..." in stderr
    assert "Languages" in stderr
