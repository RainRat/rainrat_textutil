import logging
import os
import sys
from unittest.mock import Mock, MagicMock
from pathlib import Path, PurePath

import pytest

# Ensure sourcecombine is importable
sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

from sourcecombine import collect_file_paths, should_include

def test_collect_file_paths_root_does_not_exist(caplog):
    """Test that collect_file_paths handles non-existent root folder gracefully."""
    non_existent_path = "non_existent_folder_xyz_123"

    with caplog.at_level(logging.WARNING):
        collected, root_path, excluded = collect_file_paths(
            non_existent_path, recursive=True, exclude_folders=[]
        )

    assert collected == []
    assert root_path is None
    assert excluded == 0
    assert f"Root folder '{non_existent_path}' does not exist" in caplog.text

def test_collect_file_paths_root_access_error(monkeypatch, caplog):
    """Test that collect_file_paths handles OSError when checking root folder."""

    class MockPath:
        def __init__(self, *args, **kwargs):
            self.args = args

        def is_dir(self):
            raise OSError("Simulated Access Denied")

    # Patch Path in sourcecombine to use our MockPath
    monkeypatch.setattr("sourcecombine.Path", MockPath)

    root_folder = "/protected/folder"

    with caplog.at_level(logging.WARNING):
        collected, root_path, excluded = collect_file_paths(
            root_folder, recursive=True, exclude_folders=[]
        )

    assert collected == []
    assert root_path is None
    assert excluded == 0
    assert f"Unable to access root folder '{root_folder}'" in caplog.text
    assert "Simulated Access Denied" in caplog.text

def test_should_include_stat_error():
    """Test that should_include handles OSError during file stat."""

    # Mock a file path that raises OSError on stat()
    mock_path = MagicMock(spec=Path)
    mock_path.is_file.return_value = True
    mock_path.name = "test.py"
    mock_path.suffix = ".py"
    mock_path.stat.side_effect = OSError("Stat failed")

    filter_opts = {
        "min_size_bytes": 0,
        "max_size_bytes": 100,
    }
    search_opts = {}

    # Test simple return
    result = should_include(
        mock_path,
        PurePath("test.py"),
        filter_opts,
        search_opts,
        return_reason=False
    )
    assert result is False

    # Test return with reason
    result_with_reason = should_include(
        mock_path,
        PurePath("test.py"),
        filter_opts,
        search_opts,
        return_reason=True
    )
    assert result_with_reason == (False, 'stat_error')
