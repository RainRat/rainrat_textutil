import sys
import os
from pathlib import Path
from unittest.mock import MagicMock

# Adjust sys.path to include the project root
sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

import sourcecombine

from unittest.mock import patch, MagicMock

def test_summary_status_column_visibility(monkeypatch, capsys):
    # Case 1: No status present
    stats_no_status = {
        'total_files': 1,
        'total_size_bytes': 100,
        'files_by_language': {'.py': 1},
        'total_tokens': 10,
        'token_count_is_approx': False,
        'top_files': [
            (10, 100, "file.py", None)
        ]
    }

    args = MagicMock()
    args.dry_run = False
    args.estimate_tokens = False
    args.list_files = False
    args.tree = False
    args.extract = False
    args.format = 'text'

    monkeypatch.setenv("NO_COLOR", "1")

    with patch('shutil.get_terminal_size', return_value=MagicMock(columns=120)):
        sourcecombine._print_execution_summary(stats_no_status, args, pairing_enabled=False)
    stderr_no_status = capsys.readouterr().err

    assert "STATUS" not in stderr_no_status
    # Verify alignment - Languages header should NOT have the status spacer
    # but still has padding from field widths: DISTRIBUTION (12) + " " + FILES (%) (15)
    # 1 space from join + 6 spaces from :>15 padding = 7 spaces
    assert "DISTRIBUTION       FILES (%)" in stderr_no_status

    # Case 2: Status present
    stats_with_status = {
        'total_files': 1,
        'total_size_bytes': 100,
        'files_by_language': {'.py': 1},
        'total_tokens': 10,
        'token_count_is_approx': False,
        'top_files': [
            (10, 100, "file.py", "M")
        ]
    }

    with patch('shutil.get_terminal_size', return_value=MagicMock(columns=120)):
        sourcecombine._print_execution_summary(stats_with_status, args, pairing_enabled=False)
    stderr_with_status = capsys.readouterr().err

    assert "STATUS" in stderr_with_status
    # Verify alignment - Languages header SHOULD have the status spacer (6)
    # DISTRIBUTION (12) + " " + FILES (%) (15)
    # The status spacer comes AFTER FILES (%) in Languages table now.
    assert "DISTRIBUTION       FILES (%)" in stderr_with_status
    # Check for the spacers after FILES (%)
    # FILES (%) (9 chars) + 1 (join) + spacer(6) + 1 (join) + lang_spacer(11) + 1 (join) + LANGUAGE (8) = 20 spaces
    assert "FILES (%)                    LANGUAGE" in stderr_with_status
    assert "[M]" in stderr_with_status
