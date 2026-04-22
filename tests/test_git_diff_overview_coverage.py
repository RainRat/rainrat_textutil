import subprocess
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
import sourcecombine
import utils
import argparse
import sys
import io

def test_get_git_info_diff_branches(tmp_path):
    """Test all branches of git diff command construction in _get_git_info."""
    root = tmp_path

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="dummy", returncode=0)

        # Branch: staged=True, diff_ref=None
        sourcecombine._get_git_info(root, include_diff=True, staged=True)
        assert ['git', 'diff', '--relative', '--cached'] in [call.args[0] for call in mock_run.call_args_list]

        mock_run.reset_mock()
        # Branch: staged=True, diff_ref='main'
        sourcecombine._get_git_info(root, include_diff=True, staged=True, diff_ref='main')
        assert ['git', 'diff', '--relative', '--cached', 'main'] in [call.args[0] for call in mock_run.call_args_list]

        mock_run.reset_mock()
        # Branch: unstaged=True
        sourcecombine._get_git_info(root, include_diff=True, unstaged=True)
        assert ['git', 'diff', '--relative'] in [call.args[0] for call in mock_run.call_args_list]

        mock_run.reset_mock()
        # Branch: diff_ref='main', not staged/unstaged
        sourcecombine._get_git_info(root, include_diff=True, diff_ref='main')
        assert ['git', 'diff', '--relative', 'main'] in [call.args[0] for call in mock_run.call_args_list]

        mock_run.reset_mock()
        # Branch: default (no ref, no staged/unstaged) -> HEAD
        sourcecombine._get_git_info(root, include_diff=True)
        assert ['git', 'diff', '--relative', 'HEAD'] in [call.args[0] for call in mock_run.call_args_list]

def test_generate_project_overview_with_diff():
    """Test including git diff in project overview (text and markdown)."""
    stats = {
        'tokens': 100,
        'lines': 10,
        'size': 1024,
        'is_approx': False,
        'git_branch': 'main',
        'git_commit_short': 'abc1234',
        'git_log': 'Some log',
        'git_diff': 'diff --git a/file b/file\n+new line',
        'files': [],
        'top_files': [],
        'files_by_extension': {},
        'total_tokens': 100,
        'total_size_bytes': 1024
    }

    # Text format
    overview_text = sourcecombine._generate_project_overview(stats, output_format='text')
    assert "Current Changes:" in overview_text
    assert "    +new line" in overview_text

    # Markdown format
    overview_md = sourcecombine._generate_project_overview(stats, output_format='markdown')
    assert "### Current Changes" in overview_md
    assert "```diff" in overview_md
    assert "+new line" in overview_md

def test_utils_validate_include_diff():
    """Test validation of output.include_diff in utils.py."""
    config = {
        'output': {
            'include_diff': 'not-a-boolean'
        }
    }
    # Direct call to _validate_output_section
    with pytest.raises(utils.InvalidConfigError, match="'output.include_diff' must be true or false."):
        utils._validate_output_section(config)

def test_main_include_diff_flag(tmp_path):
    """Test that --include-diff flag sets include_diff in config."""
    import sys
    # Use a dummy root folder that is a git repo to avoid git check failures
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "a.txt").write_text("hello")

    with patch.object(sys, 'argv', ['sourcecombine.py', str(repo), '--include-diff']):
        with patch('sourcecombine.load_and_validate_config', return_value=utils.DEFAULT_CONFIG.copy()):
            with patch('sourcecombine.find_and_combine_files', return_value={'included': [], 'total_included': 0, 'total_found': 0, 'skipped': [], 'skipped_folders': 0, 'duration': 0.1, 'total_tokens': 0, 'total_size_bytes': 0, 'total_lines': 0, 'is_approx': False, 'top_files': [], 'files_by_extension': {}}) as mock_combine:
                with patch('sourcecombine._get_git_info', return_value={}):
                    with patch('sys.stderr', new_callable=io.StringIO):
                        try:
                            sourcecombine.main()
                        except SystemExit:
                            pass

                    config = mock_combine.call_args[0][0]
                    assert config['output']['include_diff'] is True

def test_main_verbs_coverage(tmp_path):
    """Test the dry-run and success verbs for apply_in_place in _print_execution_summary."""

    mock_args = argparse.Namespace(
        dry_run=True,
        apply_in_place=True,
        extract=False,
        targets=[str(tmp_path)],
        output=None,
        files_from=None,
        include=[],
        exclude=[],
        language=[],
        max_tokens=None,
        max_total_size=None,
        max_total_lines=None,
        limit=None,
        json_summary=None,
        skip_binary=True,
        unique=False,
        git_log=0,
        show_config=False,
        json=False,
        xml=False,
        markdown=False,
        estimate_tokens=False,
        list_files=False,
        tree=False,
        compact=False,
        replace=[],
        replace_line=[],
        sort=None,
        reverse=False
    )

    stats = {
        'total_included': 1,
        'total_found': 1,
        'included': [{'path': 'a.txt', 'tokens': 10, 'size': 100, 'lines': 5}],
        'skipped': [],
        'skipped_folders': 0,
        'token_limit_reached': False,
        'size_limit_reached': False,
        'line_limit_reached': False,
        'limit_reached': False,
        'duration': 0.1,
        'total_tokens': 10,
        'total_size_bytes': 100,
        'total_lines': 5,
        'is_approx': False,
        'top_files': [],
        'files_by_extension': {}
    }

    # Use a string buffer to capture stderr
    stderr_buf = io.StringIO()
    with patch('sys.stderr', stderr_buf):
        # Dry run with apply_in_place
        sourcecombine._print_execution_summary(stats, mock_args, pairing_enabled=False)
        output = stderr_buf.getvalue()
        assert "would update in-place" in output.lower()

        # Success with apply_in_place
        stderr_buf.truncate(0)
        stderr_buf.seek(0)
        mock_args.dry_run = False
        sourcecombine._print_execution_summary(stats, mock_args, pairing_enabled=False)
        output = stderr_buf.getvalue()
        assert "updated in-place" in output.lower()
