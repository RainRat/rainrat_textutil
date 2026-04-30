import subprocess
from unittest.mock import MagicMock, patch
from pathlib import Path
import sourcecombine

def test_get_git_info_various_statuses(tmp_path):
    """Test _get_git_info with various Git statuses to ensure full coverage of parsing logic."""

    # Mocking subprocess.run to return a variety of git status --porcelain lines
    # Line < 4 chars (ignored)
    # Added (A)
    # Renamed (R)
    # Deleted (D)
    # Modified (M) - already covered but good for summary
    # Untracked (??) - already covered but good for summary

    mock_status_output = (
        "X\n"                      # too short, should be skipped (line 817)
        "A  added_file.py\n"       # Added (line 827)
        "R  old.py -> new.py\n"    # Renamed (line 833)
        " D deleted_file.py\n"     # Deleted (line 839)
        "M  modified_file.py\n"    # Modified
        "?? untracked_file.py\n"   # Untracked
    )

    def mock_run(args, **kwargs):
        mock = MagicMock()
        if args == ['git', 'rev-parse', '--is-inside-work-tree']:
            mock.stdout = "true\n"
        elif args == ['git', 'rev-parse', '--abbrev-ref', 'HEAD']:
            mock.stdout = "main\n"
        elif args == ['git', 'rev-parse', 'HEAD']:
            mock.stdout = "abcdef1234567890\n"
        elif args == ['git', 'status', '--porcelain', '-uall']:
            mock.stdout = mock_status_output
        elif args == ['git', 'log', '-n', '5', '--format=%h: %s / %an, %ar']:
            mock.stdout = "abc: commit msg\n"
        elif args == ['git', 'diff', '--no-color']:
            mock.stdout = "some diff\n"
        else:
            mock.stdout = ""
        mock.returncode = 0
        return mock

    with patch("subprocess.run", side_effect=mock_run):
        info = sourcecombine._get_git_info(tmp_path)

        # Verify file statuses
        assert info['file_statuses']['added_file.py'] == 'A'
        assert info['file_statuses']['new.py'] == 'R'
        assert info['file_statuses']['deleted_file.py'] == 'D'
        assert info['file_statuses']['modified_file.py'] == 'M'
        assert info['file_statuses']['untracked_file.py'] == '??'

        # Verify summary string
        # counts: M=1, A=1, ?=1, R=1, D=1
        # Order in code: modified, added, untracked, renamed, deleted
        expected_status = "1 modified, 1 added, 1 untracked, 1 renamed, 1 deleted"
        assert info['git_status'] == expected_status

def test_get_git_info_rename_quoted(tmp_path):
    """Test _get_git_info with a renamed file that has spaces/quotes."""

    mock_status_output = 'R  "old file.py" -> "new file.py"\n'

    def mock_run(args, **kwargs):
        mock = MagicMock()
        if args == ['git', 'status', '--porcelain', '-uall']:
            mock.stdout = mock_status_output
        elif args == ['git', 'rev-parse', '--is-inside-work-tree']:
            mock.stdout = "true\n"
        else:
            mock.stdout = ""
        return mock

    with patch("subprocess.run", side_effect=mock_run):
        info = sourcecombine._get_git_info(tmp_path)
        assert info['file_statuses']['new file.py'] == 'R'
