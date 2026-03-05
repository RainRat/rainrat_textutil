import subprocess
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
import os
import sys

# Adjust sys.path to include the project root
sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

import sourcecombine
import utils

def test_collect_git_files_success():
    """Test successful git file discovery."""
    mock_result = MagicMock()
    mock_result.stdout = "file1.txt\nfolder/file2.txt\n"

    with patch('subprocess.run', return_value=mock_result) as mock_run:
        root = Path("/fake/root")
        files, root_out, excluded = sourcecombine.collect_git_files(root)

        assert files == [root / "file1.txt", root / "folder/file2.txt"]
        assert root_out == root
        assert excluded == 0
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert 'git' in args
        assert 'ls-files' in args

def test_collect_git_files_failure():
    """Test fallback when git fails (e.g., not a git repo)."""
    with patch('subprocess.run', side_effect=subprocess.CalledProcessError(1, 'git')):
        root = Path("/fake/root")
        result = sourcecombine.collect_git_files(root)
        assert result is None

def test_collect_git_files_not_found():
    """Test fallback when git command is not found."""
    with patch('subprocess.run', side_effect=FileNotFoundError()):
        root = Path("/fake/root")
        result = sourcecombine.collect_git_files(root)
        assert result is None

def test_collect_file_paths_with_git_enabled(tmp_path):
    """Test collect_file_paths uses git discovery when requested."""
    # Create some files
    (tmp_path / "tracked.txt").write_text("tracked")
    (tmp_path / "ignored.log").write_text("ignored")

    # Mock collect_git_files to return only tracked.txt
    git_results = ([tmp_path / "tracked.txt"], tmp_path, 0)

    with patch('sourcecombine.collect_git_files', return_value=git_results) as mock_git:
        files, root, excluded = sourcecombine.collect_file_paths(
            tmp_path, recursive=True, exclude_folders=[], use_git=True
        )
        assert files == [tmp_path / "tracked.txt"]
        mock_git.assert_called_once_with(tmp_path, progress=None)

def test_collect_file_paths_git_fallback(tmp_path):
    """Test collect_file_paths falls back to standard scan when git fails."""
    (tmp_path / "file.txt").write_text("hello")

    with patch('sourcecombine.collect_git_files', return_value=None):
        files, root, excluded = sourcecombine.collect_file_paths(
            tmp_path, recursive=True, exclude_folders=[], use_git=True
        )
        # Standard scan should find file.txt
        assert any(f.name == "file.txt" for f in files)

def test_collect_file_paths_git_max_depth(tmp_path):
    """Test that max_depth is applied to git results."""
    root = tmp_path
    git_files = [
        root / "level1.txt",
        root / "dir1" / "level2.txt",
        root / "dir1" / "dir2" / "level3.txt"
    ]

    with patch('sourcecombine.collect_git_files', return_value=(git_files, root, 0)):
        # Depth 1: should only see level1.txt
        files, _, _ = sourcecombine.collect_file_paths(
            root, recursive=True, exclude_folders=[], use_git=True, max_depth=1
        )
        assert files == [root / "level1.txt"]

        # Depth 2: should see level1.txt and level2.txt
        files, _, _ = sourcecombine.collect_file_paths(
            root, recursive=True, exclude_folders=[], use_git=True, max_depth=2
        )
        assert files == [root / "level1.txt", root / "dir1" / "level2.txt"]

def test_collect_file_paths_git_folder_exclusion(tmp_path):
    """Test that folder exclusions are applied to git results."""
    root = tmp_path
    git_files = [
        root / "included.txt",
        root / "excluded_dir" / "file.txt",
        root / "nested" / "excluded_dir" / "file.txt"
    ]

    with patch('sourcecombine.collect_git_files', return_value=(git_files, root, 0)):
        # Exclude 'excluded_dir'
        files, _, _ = sourcecombine.collect_file_paths(
            root, recursive=True, exclude_folders=['excluded_dir'], use_git=True
        )
        assert files == [root / "included.txt"]

def test_cli_git_files_flag():
    """Test that -G flag sets use_git in config."""
    mock_stats = {
        'total_files': 0,
        'total_discovered': 0,
        'total_size_bytes': 0,
        'total_tokens': 0,
        'total_lines': 0,
        'top_files': [],
        'files_by_extension': {},
    }
    with patch('sourcecombine.find_and_combine_files', return_value=mock_stats) as mock_find:
        with patch('sys.argv', ['sourcecombine.py', '.', '-G']):
            try:
                sourcecombine.main()
            except SystemExit:
                pass

            assert mock_find.called
            config = mock_find.call_args[0][0]
            assert config['search']['use_git'] is True

def test_utils_config_validation():
    """Test that use_git is validated in config."""
    config = {
        'search': {'use_git': 'invalid'}
    }
    with pytest.raises(utils.InvalidConfigError, match="search.use_git must be true or false"):
        utils.validate_config(config)

    config = {'search': {'use_git': True}}
    utils.validate_config(config) # Should not raise
