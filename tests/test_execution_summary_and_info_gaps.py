import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

import sourcecombine

def test_print_project_info_multiline_fields(capsys):
    stats = {
        'project_name': 'My Project',
        'project_version': '1.0.0',
        'project_author': 'Author One\nAuthor Two',
        'project_description': 'This is line 1.\nThis is line 2.',
    }
    sourcecombine.print_project_info(stats)
    out, _ = capsys.readouterr()
    assert "Author One" in out
    assert "Author Two" in out
    assert "This is line 1." in out
    assert "This is line 2." in out

def test_print_execution_summary_truncation_long_destination(capsys):
    stats = {
        'total_files': 10,
        'total_size_bytes': 1000,
        'total_lines': 500,
        'total_tokens': 200,
        'project_name': 'A' * 150,
        'git_branch': 'B' * 150,
    }
    args = MagicMock()
    args.dry_run = False
    args.estimate_tokens = False
    args.list_files = False
    args.tree = False
    args.extract = True
    args.apply_in_place = False

    with patch('shutil.get_terminal_size', return_value=MagicMock(columns=80)):
        dest_desc = "to '" + "C" * 100 + "'"
        sourcecombine._print_execution_summary(
            stats, args, pairing_enabled=False, destination_desc=dest_desc
        )
        out, err = capsys.readouterr()
        assert "to 'C" in err
        assert "..." in err

def test_print_execution_summary_truncation_long_mirrored_destination(capsys):
    stats = {
        'total_files': 10,
        'total_size_bytes': 1000,
        'total_lines': 500,
        'total_tokens': 200,
    }
    args = MagicMock()
    args.dry_run = False
    args.estimate_tokens = False
    args.list_files = False
    args.tree = False
    args.extract = True
    args.apply_in_place = False

    with patch('shutil.get_terminal_size', return_value=MagicMock(columns=80)):
        dest_desc = "to '" + "D" * 100 + "' (mirrored)"
        sourcecombine._print_execution_summary(
            stats, args, pairing_enabled=False, destination_desc=dest_desc
        )
        out, err = capsys.readouterr()
        assert "to 'D" in err
        assert "..." in err
        assert "(mirrored)" in err
