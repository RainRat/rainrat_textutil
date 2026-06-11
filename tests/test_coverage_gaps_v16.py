import pytest
import subprocess
import sys
from unittest.mock import MagicMock, patch
from sourcecombine import (
    _format_metadata_summary,
    _get_git_info,
    _generate_project_overview,
    _print_execution_summary,
    _print_diff,
    find_and_combine_files,
)
from argparse import Namespace
from pathlib import Path

def test_format_metadata_summary_gaps():
    # line 395: both status and summary
    assert _format_metadata_summary({'status': 'M', 'files': 1}) == " [M]  (1 file)"

    # line 397: status only
    assert _format_metadata_summary({'status': 'A'}) == " [A]"

    # line 400: neither
    assert _format_metadata_summary({}) == ""

def test_get_git_info_status_parsing_gaps():
    mock_status = (
        "M  modified.txt\n"   # X='M', Y=' '
        " A added.txt\n"      # X=' ', Y='A'
        "R  old.txt -> new.txt\n" # X='R', Y=' '
        "R  rename_no_arrow.txt\n" # X='R', but no " -> " (covers 837->845 branch)
        " D deleted.txt\n"    # X=' ', Y='D'
        "?? untracked.txt\n"  # X='?', Y='?'
        "XY\n"                # len < 4, should be skipped (line 818)
        "!! ignored.txt\n"    # Unknown status (line 843)
    )

    with patch('subprocess.run') as mock_run:
        def side_effect(cmd, **kwargs):
            m = MagicMock()
            if cmd[1] == 'rev-parse':
                if '--show-toplevel' in cmd:
                    m.stdout = "/repo"
                elif '--abbrev-ref' in cmd:
                    m.stdout = "main"
                else:
                    m.stdout = "abcdef123456"
            elif cmd[1] == 'status':
                m.stdout = mock_status
            m.returncode = 0
            return m

        mock_run.side_effect = side_effect

        info = _get_git_info("/repo")

        assert info['file_statuses']['modified.txt'] == 'M'
        assert info['file_statuses']['added.txt'] == 'A'
        assert info['file_statuses']['new.txt'] == 'R'
        assert info['file_statuses']['deleted.txt'] == 'D'
        assert info['file_statuses']['untracked.txt'] == '??'
        assert 'XY' not in info['file_statuses']
        assert 'ignored.txt' not in info['file_statuses']

    # Test empty status (line 814 branch)
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(stdout="", returncode=0)
        info = _get_git_info("/repo")
        assert info['file_statuses'] == {}

def test_generate_project_overview_git_status_gaps():
    stats = {
        'total_files': 1,
        'total_size_bytes': 10,
        'total_tokens': 1,
        'total_lines': 1,
        'git_status': 'Working tree clean',
        'git_branch': 'feat/branch',
        'git_commit_short': 'abc1234'
    }

    # Covered: 1924, 1926, 1928, 1951, 1953, 1955
    overview_md = _generate_project_overview(stats, output_format='markdown')
    assert "- **Git Branch:** feat/branch" in overview_md
    assert "- **Git Commit:** abc1234" in overview_md
    assert "- **Git Status:** Working tree clean" in overview_md

    overview_text = _generate_project_overview(stats, output_format='text')
    assert "  Git Branch:   feat/branch" in overview_text
    assert "  Git Commit:   abc1234" in overview_text
    assert "  Git Status:   Working tree clean" in overview_text

    # Test branches where they are NOT present or 'N/A' (line 1924->1930 skip and other items)
    stats_empty = {
        'total_files': 1,
        'total_size_bytes': 10,
        'total_tokens': 1,
        'total_lines': 1,
        'git_branch': 'N/A',
        'git_commit_short': None,
        'git_status': None
    }
    overview_md_empty = _generate_project_overview(stats_empty, output_format='markdown')
    assert "Git Branch" not in overview_md_empty
    assert "Git Commit" not in overview_md_empty
    assert "Git Status" not in overview_md_empty

def test_print_execution_summary_limits_mock_gap():
    # line 5004-5006: val is a Mock (truthy but raises TypeError on comparison)
    stats = {
        'total_included': 1,
        'total_size_bytes': 100,
        'total_tokens': 0,
        'total_lines': 0,
        'files_by_language': {},
        'top_files': [],
        'tokens_by_language': {},
        'size_by_language': {},
    }

    args = Namespace(
        dry_run=False,
        estimate_tokens=False,
        list_files=False,
        tree=False,
        clipboard=False,
        git_log=None,
        limit=MagicMock(), # This should be truthy but fails int conversion
        max_tokens="", # Raises ValueError on int conversion, but falsy (covers 5004->4995 branch)
        max_total_size=0,
        max_total_lines=0,
        json_summary=None,
        extract=False,
        apply_in_place=False,
    )

    with patch('sys.stderr', new_callable=MagicMock):
        # We just want to ensure it covers the 'except' block and doesn't crash
        _print_execution_summary(stats, args, pairing_enabled=False)

def test_print_diff_no_diff_after_all():
    # Trigger line 121->exit by having has_diff remain False
    with patch('difflib.unified_diff', return_value=[]):
        with patch('sys.stderr') as mock_stderr:
            _print_diff("old", "new", "file.txt")
            # If unified_diff is empty, sys.stderr.write should NOT be called with "\n" at the end
            # though it might not be called at all.
            # We just care about the coverage of the line 121 check.
            mock_stderr.write.assert_not_called()

def test_find_and_combine_dry_run_no_estimate_gaps(tmp_path):
    # Coverage for lines 2912, 2938, 2951, 2965 (branches skipping token estimation)
    (tmp_path / "f1.txt").write_text("hello", encoding="utf-8")
    (tmp_path / "f2.txt").write_text("world", encoding="utf-8")
    config = {
        'search': {
            'root_folders': [str(tmp_path)],
            'exclusions': ['f2.txt'] # Trigger should_include = False (covers 1135->1137)
        },
        'output': {
            'project_overview': True,
            'include_tree': True,
            'table_of_contents': True,
            'format': 'text'
        }
    }
    # dry_run=True, estimate_tokens=False
    find_and_combine_files(config, None, dry_run=True, estimate_tokens=False)
