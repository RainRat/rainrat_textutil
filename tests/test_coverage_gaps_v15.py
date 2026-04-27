import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch
import subprocess

# Adjust sys.path to include the project root
sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

import sourcecombine

def test_format_metadata_summary_gaps():
    # Gap: line 381 (status label), line 395 (both status and summary)
    meta_both = {'status': 'M', 'files': 1, 'size': 100}
    result = sourcecombine._format_metadata_summary(meta_both)
    assert "[M]" in result
    assert "1 file" in result
    assert "100.00 B" in result

    # Gap: line 397 (status label only)
    meta_status_only = {'status': '??'}
    result = sourcecombine._format_metadata_summary(meta_status_only)
    assert result == " [??]"

    # Gap: line 400 (empty metadata)
    meta_empty = {}
    result = sourcecombine._format_metadata_summary(meta_empty)
    assert result == ""

    # Gap: line 389 (lines), line 391 (tokens), line 399 (summary only)
    meta_summary_only = {'lines': 10, 'tokens': 20}
    result = sourcecombine._format_metadata_summary(meta_summary_only)
    assert result == " (10 lines • 20 tokens)"
    assert "[M]" not in result

def test_get_git_info_status_parsing_gaps():
    # Mock subprocess.run for git status --porcelain
    # Lines to cover:
    # 818: short line
    # 828-829: Added 'A'
    # 834-838: Renamed 'R' with " -> "
    # 840-841: Deleted 'D'
    # 843: status_code = None (unknown status)

    status_output = (
        "M  modified.txt\n"
        "A  added.txt\n"
        " R old.txt -> new.txt\n"
        "D  deleted.txt\n"
        "?? untracked.txt\n"
        "XY unknown.txt\n" # Should result in status_code = None
        "S\n"               # Short line (< 4 chars)
    )

    def mock_run(args, **kwargs):
        if 'status' in args:
            return MagicMock(stdout=status_output, returncode=0)
        elif 'rev-parse' in args:
            return MagicMock(stdout="main\n", returncode=0)
        elif 'log' in args:
            return MagicMock(stdout="commit hash\n", returncode=0)
        elif 'diff' in args:
            return MagicMock(stdout="some diff\n", returncode=0)
        return MagicMock(stdout="", returncode=0)

    with patch('subprocess.run', side_effect=mock_run):
        # We need to pass a directory that exists or mock Path.is_dir/is_file
        info = sourcecombine._get_git_info(Path('.'), log_count=0, include_diff=False)

        # Verify counts in git_status string (which comes from summary_parts)
        # modified, added, untracked, renamed, deleted
        assert "1 modified" in info['git_status']
        assert "1 added" in info['git_status']
        assert "1 untracked" in info['git_status']
        assert "1 renamed" in info['git_status']
        assert "1 deleted" in info['git_status']

        # Verify file_statuses
        assert info['file_statuses']['modified.txt'] == 'M'
        assert info['file_statuses']['added.txt'] == 'A'
        assert info['file_statuses']['new.txt'] == 'R' # Path should be new.txt
        assert info['file_statuses']['deleted.txt'] == 'D'
        assert info['file_statuses']['untracked.txt'] == '??'
        assert 'unknown.txt' not in info['file_statuses']

def test_get_git_info_renamed_quoted():
    # Test renamed with quotes
    status_output = ' R "old name.txt" -> "new name.txt"\n'

    def mock_run(args, **kwargs):
        if 'status' in args:
            return MagicMock(stdout=status_output, returncode=0)
        elif 'rev-parse' in args:
            return MagicMock(stdout="main\n", returncode=0)
        return MagicMock(stdout="", returncode=0)

    with patch('subprocess.run', side_effect=mock_run):
        info = sourcecombine._get_git_info(Path('.'), log_count=0, include_diff=False)
        assert info['file_statuses']['new name.txt'] == 'R'

def test_get_git_info_renamed_no_arrow():
    # Cover branch 837 -> 845 (R status but no " -> " in path)
    status_output = "R  renamed_no_arrow.txt\n"

    def mock_run(args, **kwargs):
        if 'status' in args:
            return MagicMock(stdout=status_output, returncode=0)
        elif 'rev-parse' in args:
            return MagicMock(stdout="main\n", returncode=0)
        return MagicMock(stdout="", returncode=0)

    with patch('subprocess.run', side_effect=mock_run):
        info = sourcecombine._get_git_info(Path('.'), log_count=0, include_diff=False)
        assert info['file_statuses']['renamed_no_arrow.txt'] == 'R'

def test_generate_project_overview_git_status_gaps():
    # Gap: line 1928 (Git Status in markdown), 1955 (Git Status in text)
    # Plus 1924, 1926, 1951, 1953 (Git Branch and Commit)
    stats = {
        'total_files': 1,
        'total_size_bytes': 100,
        'total_lines': 10,
        'total_tokens': 20,
        'token_count_is_approx': False,
        'git_status': '1 modified',
        'git_branch': 'feat-test',
        'git_commit_short': 'abc1234'
    }

    # Test Markdown
    overview_md = sourcecombine._generate_project_overview(stats, output_format='markdown')
    assert "- **Git Status:** 1 modified" in overview_md
    assert "- **Git Branch:** feat-test" in overview_md
    assert "- **Git Commit:** abc1234" in overview_md

    # Test Text
    overview_txt = sourcecombine._generate_project_overview(stats, output_format='text')
    assert "  Git Status:   1 modified" in overview_txt
    assert "  Git Branch:   feat-test" in overview_txt
    assert "  Git Commit:   abc1234" in overview_txt

def test_generate_project_overview_no_git_status():
    # Cover branch where git_status is NOT present
    stats = {
        'total_files': 1,
        'total_size_bytes': 100,
        'total_lines': 10,
        'total_tokens': 20,
        'token_count_is_approx': False,
        'git_status': None
    }
    # Test Markdown
    overview_md = sourcecombine._generate_project_overview(stats, output_format='markdown')
    assert "Git Status" not in overview_md

    # Test Text
    overview_txt = sourcecombine._generate_project_overview(stats, output_format='text')
    assert "Git Status" not in overview_txt

def test_get_git_info_no_status_lines():
    # Cover line 814 -> 859 (if not status_lines)
    def mock_run(args, **kwargs):
        if 'status' in args:
            return MagicMock(stdout="", returncode=0)
        elif 'rev-parse' in args:
            return MagicMock(stdout="main\n", returncode=0)
        return MagicMock(stdout="", returncode=0)

    with patch('subprocess.run', side_effect=mock_run):
        info = sourcecombine._get_git_info(Path('.'), log_count=0, include_diff=False)
        assert info['git_status'] is None

def test_get_git_info_no_summary_parts():
    # Cover branch 855 -> 859 (if status_lines but no summary_parts)
    # e.g. status code that is None
    status_output = "XX somefile.txt\n"

    def mock_run(args, **kwargs):
        if 'status' in args:
            return MagicMock(stdout=status_output, returncode=0)
        elif 'rev-parse' in args:
            return MagicMock(stdout="main\n", returncode=0)
        return MagicMock(stdout="", returncode=0)

    with patch('subprocess.run', side_effect=mock_run):
        info = sourcecombine._get_git_info(Path('.'), log_count=0, include_diff=False)
        assert info['git_status'] is None
