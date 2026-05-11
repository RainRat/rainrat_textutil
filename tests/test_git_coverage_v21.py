import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch
import sourcecombine

def test_render_template_file_git_placeholders():
    """Cover sourcecombine.py lines 547-551."""
    template = "{{FILE_AUTHOR}} - {{FILE_AUTHOR_DATE}} - {{FILE_LOG}}"
    git_info = {"git_repo_root": "/tmp/repo"}
    filename = Path("test.py")

    mock_data = {
        'file_author': 'John Doe',
        'file_author_date': '2023-01-01',
        'file_log': 'Initial commit'
    }

    # Use a different name for the patch to avoid issues with lru_cache if any
    with patch("sourcecombine._get_file_git_info", return_value=mock_data):
        result = sourcecombine._render_template(template, filename, git_info=git_info)
        assert "John Doe - 2023-01-01 - Initial commit" in result

def test_get_file_git_info_success():
    """Cover sourcecombine.py lines 891-897."""
    sourcecombine._get_file_git_info.cache_clear()
    mock_res = MagicMock(stdout="Author Name\n2023-01-01\nCommit Msg\n")
    with patch("subprocess.run", return_value=mock_res):
        res = sourcecombine._get_file_git_info("test_success.py", "/tmp/repo")
        assert res['file_author'] == "Author Name"
        assert res['file_author_date'] == "2023-01-01"
        assert res['file_log'] == "Commit Msg"

def test_get_file_git_info_empty_inputs():
    """Cover sourcecombine.py lines 882-883."""
    sourcecombine._get_file_git_info.cache_clear()
    assert sourcecombine._get_file_git_info("", "/tmp/repo") == {}
    assert sourcecombine._get_file_git_info("test.py", "") == {}

def test_get_file_git_info_git_failure():
    """Cover sourcecombine.py lines 898-900."""
    sourcecombine._get_file_git_info.cache_clear()
    with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, 'git')):
        assert sourcecombine._get_file_git_info("test_fail.py", "/tmp/repo") == {}

    sourcecombine._get_file_git_info.cache_clear()
    with patch("subprocess.run", side_effect=FileNotFoundError()):
        assert sourcecombine._get_file_git_info("test_fail_fnf.py", "/tmp/repo") == {}

def test_get_file_git_info_malformed_output():
    """Cover sourcecombine.py lines 892 (len(lines) < 3)."""
    sourcecombine._get_file_git_info.cache_clear()
    mock_res = MagicMock(stdout="only one line\n")
    with patch("subprocess.run", return_value=mock_res):
        assert sourcecombine._get_file_git_info("test_malformed.py", "/tmp/repo") == {}

def test_get_git_info_fallback():
    """Cover sourcecombine.py lines 953-960."""
    # 1. git rev-parse --show-toplevel
    # 2. git rev-parse --abbrev-ref HEAD
    # 3. git log -1 --format=%H%n%an%n%ai (FAILURE)
    # 4. git rev-parse HEAD (SUCCESS - fallback)
    # 5. git remote get-url origin
    # 6. git status --porcelain -uall

    mock_root = MagicMock(stdout="/tmp/repo\n")
    mock_branch = MagicMock(stdout="main\n")
    mock_rev_parse = MagicMock(stdout="abcdef1234567890\n")
    mock_remote = MagicMock(stdout="https://github.com/user/repo\n")
    mock_status = MagicMock(stdout="")

    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            mock_root,
            mock_branch,
            subprocess.CalledProcessError(1, 'git log'),
            mock_rev_parse,
            mock_remote,
            mock_status
        ]

        info = sourcecombine._get_git_info("/tmp/repo")
        assert info['git_commit'] == "abcdef1234567890"
        assert info['git_commit_short'] == "abcdef1"
        assert info.get('git_author') == 'N/A'
