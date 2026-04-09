import subprocess
import logging
from unittest.mock import MagicMock, patch
import sourcecombine
import utils

def test_collect_git_diff_files_progress(tmp_path):
    """Test collect_git_diff_files calls progress.update(1)."""
    root = tmp_path
    mock_progress = MagicMock()

    mock_diff = MagicMock()
    mock_diff.stdout = "file1.py\n"
    mock_ls = MagicMock()
    mock_ls.stdout = "untracked.py\n"

    (root / "file1.py").touch()
    (root / "untracked.py").touch()

    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [mock_diff, mock_ls]
        sourcecombine.collect_git_diff_files(root, progress=mock_progress)

        # Should be called twice, once for each file found and verified with is_file()
        assert mock_progress.update.call_count == 2
        mock_progress.update.assert_called_with(1)

def test_collect_git_diff_files_error(tmp_path, caplog):
    """Test collect_git_diff_files returns None and logs warning on subprocess error."""
    root = tmp_path
    caplog.set_level(logging.WARNING)

    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, "git diff")

        result = sourcecombine.collect_git_diff_files(root)

        assert result is None
        assert "Finding changed files with Git failed" in caplog.text

def test_collect_file_paths_git_diff_max_depth(tmp_path):
    """Test max_depth filtering in collect_file_paths when using git diff."""
    root = tmp_path
    file_in_root = root / "file1.py"
    file_in_subdir = root / "subdir" / "file2.py"
    file_in_root.touch()
    file_in_subdir.parent.mkdir()
    file_in_subdir.touch()

    with patch("sourcecombine.collect_git_diff_files") as mock_collect:
        mock_collect.return_value = ([file_in_root, file_in_subdir], root, 0)

        # Max depth 1 should exclude file_in_subdir
        paths, _, _ = sourcecombine.collect_file_paths(
            root, recursive=True, exclude_folders=[], use_git_diff=True, max_depth=1
        )

        assert paths == [file_in_root]

def test_collect_file_paths_git_diff_exclude_folders(tmp_path):
    """Test exclude_folders filtering in collect_file_paths when using git diff."""
    root = tmp_path
    file_in_root = root / "file1.py"
    file_in_excluded = root / "excluded" / "file2.py"
    file_in_root.touch()
    file_in_excluded.parent.mkdir()
    file_in_excluded.touch()

    with patch("sourcecombine.collect_git_diff_files") as mock_collect:
        mock_collect.return_value = ([file_in_root, file_in_excluded], root, 0)

        # Exclude 'excluded' folder
        paths, _, _ = sourcecombine.collect_file_paths(
            root, recursive=True, exclude_folders=["excluded"], use_git_diff=True
        )

        assert paths == [file_in_root]

def test_main_git_diff_flag(tmp_path):
    """Test --git-diff flag handling in main()."""
    import sys

    # Test --git-diff without ref (boolean)
    with patch.object(sys, 'argv', ['sourcecombine.py', '--git-diff']):
        with patch('sourcecombine.find_and_combine_files', return_value={}) as mock_combine:
            # We need to bypass some other main logic or provide enough environment
            with patch('sourcecombine.load_and_validate_config') as mock_load:
                # Provide a minimal valid config
                mock_load.return_value = utils.DEFAULT_CONFIG.copy()
                try:
                    sourcecombine.main()
                except SystemExit:
                    pass

                config = mock_combine.call_args[0][0]
                assert config['search']['use_git_diff'] is True
                assert config['search']['git_diff_ref'] is None

    # Test --git-diff with ref
    with patch.object(sys, 'argv', ['sourcecombine.py', '--git-diff', 'main']):
        with patch('sourcecombine.find_and_combine_files', return_value={}) as mock_combine:
            with patch('sourcecombine.load_and_validate_config') as mock_load:
                mock_load.return_value = utils.DEFAULT_CONFIG.copy()
                try:
                    sourcecombine.main()
                except SystemExit:
                    pass

                config = mock_combine.call_args[0][0]
                assert config['search']['use_git_diff'] is True
                assert config['search']['git_diff_ref'] == 'main'
