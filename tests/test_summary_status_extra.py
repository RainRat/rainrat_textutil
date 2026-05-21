import sys
import os
from pathlib import Path
from unittest.mock import MagicMock

# Adjust sys.path to include the project root
sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

import sourcecombine

def test_print_execution_summary_status_other(capsys):
    # Tests the 'else' branch for status coloring (status not A, ??, M, R, D)
    stats = {
        'total_files': 1,
        'total_size_bytes': 100,
        'files_by_extension': {'.py': 1},
        'total_tokens': 10,
        'token_count_is_approx': False,
        'top_files': [
            (10, 100, "file.py", "X") # 'X' is not in the handled list
        ]
    }

    args = MagicMock()
    args.dry_run = False
    args.estimate_tokens = False
    args.list_files = False
    args.tree = False
    args.extract = False
    args.format = 'text'

    # We want to see if the status is printed without special colors but with the label
    # C_RESET might still be present if NO_COLOR is not set, but let's just check the content
    sourcecombine._print_execution_summary(stats, args, pairing_enabled=False)
    stderr = capsys.readouterr().err

    assert "[X]" in stderr

def test_print_execution_summary_status_empty(capsys):
    # Tests the 'else' branch when status is empty but has_status was true
    # (has_status is True if ANY file has status, but this specific file might not)
    stats = {
        'total_files': 2,
        'total_size_bytes': 200,
        'files_by_extension': {'.py': 2},
        'total_tokens': 20,
        'token_count_is_approx': False,
        'top_files': [
            (10, 100, "file1.py", "M"),
            (10, 100, "file2.py", "") # Empty status for this file
        ]
    }

    args = MagicMock()
    args.dry_run = False
    args.estimate_tokens = False
    args.list_files = False
    args.tree = False
    args.extract = False
    args.format = 'text'

    sourcecombine._print_execution_summary(stats, args, pairing_enabled=False)
    stderr = capsys.readouterr().err

    assert "[M]" in stderr
    # Check that for the second file, we have spaces instead of a status label
    # The status column is 6 characters wide (" " + 5 spaces)
    assert "      file2.py" in stderr
