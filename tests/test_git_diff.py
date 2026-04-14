from unittest.mock import MagicMock, patch
import sourcecombine

def test_collect_git_diff_files_current(tmp_path):
    """Test collect_git_diff_files without a reference (current changes)."""
    root = tmp_path

    # Mocking subprocess for 'git diff --name-only HEAD'
    mock_diff = MagicMock()
    mock_diff.stdout = "file1.py\nfile2.txt\n"

    # Mocking subprocess for 'git ls-files --others --exclude-standard'
    mock_ls = MagicMock()
    mock_ls.stdout = "untracked.py\n"

    # Create the files so p.is_file() returns True
    (root / "file1.py").touch()
    (root / "file2.txt").touch()
    (root / "untracked.py").touch()

    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [mock_diff, mock_ls]

        file_paths, root_path, excluded = sourcecombine.collect_git_diff_files(root)

        assert len(file_paths) == 3
        assert any(p.name == "file1.py" for p in file_paths)
        assert any(p.name == "file2.txt" for p in file_paths)
        assert any(p.name == "untracked.py" for p in file_paths)
        assert root_path == root
        assert excluded == 0

def test_collect_git_diff_files_ref(tmp_path):
    """Test collect_git_diff_files with a reference branch."""
    root = tmp_path

    # Mocking subprocess for 'git diff --name-only main'
    mock_diff = MagicMock()
    mock_diff.stdout = "changed_since_main.py\n"

    # Mocking subprocess for 'git ls-files --others --exclude-standard'
    mock_ls = MagicMock()
    mock_ls.stdout = ""

    (root / "changed_since_main.py").touch()

    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [mock_diff, mock_ls]

        file_paths, root_path, excluded = sourcecombine.collect_git_diff_files(root, diff_ref="main")

        assert len(file_paths) == 1
        assert file_paths[0].name == "changed_since_main.py"
        mock_run.assert_any_call(['git', 'diff', '--name-only', '--relative', 'main'], cwd=root, capture_output=True, text=True, check=True)

def test_collect_git_diff_files_filter_deleted(tmp_path):
    """Test that deleted files are filtered out."""
    root = tmp_path

    mock_diff = MagicMock()
    mock_diff.stdout = "existing.py\ndeleted.py\n"

    mock_ls = MagicMock()
    mock_ls.stdout = ""

    (root / "existing.py").touch()
    # deleted.py is NOT touched

    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [mock_diff, mock_ls]

        file_paths, root_path, excluded = sourcecombine.collect_git_diff_files(root)

        assert len(file_paths) == 1
        assert file_paths[0].name == "existing.py"

def test_collect_file_paths_with_git_diff(tmp_path):
    """Test collect_file_paths integration with use_git_diff."""
    root = tmp_path

    with patch("sourcecombine.collect_git_diff_files") as mock_collect:
        mock_collect.return_value = ([root / "file.py"], root, 0)

        paths, root_path, excluded = sourcecombine.collect_file_paths(
            root, recursive=True, exclude_folders=[], use_git_diff=True, git_diff_ref="some-ref"
        )

        assert paths == [root / "file.py"]
        mock_collect.assert_called_once_with(
            root, diff_ref="some-ref", progress=None,
            staged_only=False, unstaged_only=False
        )
