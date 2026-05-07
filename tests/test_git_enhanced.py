from unittest.mock import MagicMock, patch
from pathlib import Path
import sourcecombine
import utils

def test_collect_git_diff_files_staged(tmp_path):
    """Test collect_git_diff_files with staged_only=True."""
    root = tmp_path

    # Mocking subprocess for 'git diff --name-only --cached'
    mock_diff = MagicMock()
    mock_diff.stdout = "staged.py\n"

    (root / "staged.py").touch()

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = mock_diff

        # We haven't updated the function signature yet, but this defines our goal
        file_paths, root_path, excluded = sourcecombine.collect_git_diff_files(root, staged_only=True)

        assert len(file_paths) == 1
        assert file_paths[0].name == "staged.py"
        mock_run.assert_called_with(
            ['git', 'diff', '--name-only', '--cached', '--relative'],
            cwd=root, capture_output=True, text=True, check=True
        )

def test_collect_git_diff_files_unstaged(tmp_path):
    """Test collect_git_diff_files with unstaged_only=True."""
    root = tmp_path

    # Mocking subprocess for 'git diff --name-only' (unstaged)
    mock_diff = MagicMock()
    mock_diff.stdout = "unstaged.py\n"

    # Mocking subprocess for 'git ls-files --others --exclude-standard' (untracked)
    mock_ls = MagicMock()
    mock_ls.stdout = "untracked.py\n"

    (root / "unstaged.py").touch()
    (root / "untracked.py").touch()

    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [mock_diff, mock_ls]

        file_paths, root_path, excluded = sourcecombine.collect_git_diff_files(root, unstaged_only=True)

        assert len(file_paths) == 2
        assert any(p.name == "unstaged.py" for p in file_paths)
        assert any(p.name == "untracked.py" for p in file_paths)

        mock_run.assert_any_call(
            ['git', 'diff', '--name-only', '--relative'],
            cwd=root, capture_output=True, text=True, check=True
        )
        mock_run.assert_any_call(
            ['git', 'ls-files', '--others', '--exclude-standard', '--', '.'],
            cwd=root, capture_output=True, text=True, check=True
        )

def test_git_metadata_placeholders():
    """Test that Git metadata placeholders are correctly rendered."""
    stats = {
        'total_files': 1,
        'total_size_bytes': 100,
        'total_tokens': 50,
        'total_lines': 10,
        'git_branch': 'feature-branch',
        'git_commit': 'abcdef1234567890abcdef1234567890abcdef12',
        'git_commit_short': 'abcdef1'
    }

    template = "Branch: {{GIT_BRANCH}}, Commit: {{GIT_COMMIT_SHORT}} ({{GIT_COMMIT}})"
    rendered = sourcecombine._render_global_template(template, stats)

    assert "Branch: feature-branch" in rendered
    assert "Commit: abcdef1" in rendered
    assert "abcdef1234567890abcdef1234567890abcdef12" in rendered

def test_get_git_info_success(tmp_path):
    """Test _get_git_info when git commands succeed."""
    root = tmp_path

    mock_root = MagicMock()
    mock_root.stdout = str(tmp_path) + "\n"

    mock_branch = MagicMock()
    mock_branch.stdout = "main\n"

    mock_commit = MagicMock()
    mock_commit.stdout = "1234567890abcdef1234567890abcdef12345678\n"

    mock_remote = MagicMock()
    mock_remote.stdout = "https://github.com/User/Repo.git\n"

    mock_status = MagicMock()
    mock_status.stdout = " M file1.txt\n?? file2.txt\n"

    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [mock_root, mock_branch, mock_commit, mock_remote, mock_status]

        info = sourcecombine._get_git_info(root)

        assert info['git_branch'] == 'main'
        assert info['git_commit'] == '1234567890abcdef1234567890abcdef12345678'
        assert info['git_commit_short'] == '1234567'
        assert info['git_status'] == "1 modified, 1 untracked"
        assert info['file_statuses'] == {"file1.txt": "M", "file2.txt": "??"}

def test_get_git_info_failure(tmp_path):
    """Test _get_git_info when not in a git repo."""
    root = tmp_path

    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = FileNotFoundError() # git not installed or similar

        info = sourcecombine._get_git_info(root)

        assert info['git_branch'] == 'N/A'
        assert info['git_commit'] == 'N/A'
        assert info['git_commit_short'] == 'N/A'
