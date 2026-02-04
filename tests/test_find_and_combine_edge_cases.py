import logging
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

from sourcecombine import (
    find_and_combine_files,
    _SilentProgress,
    _matches_file_glob_cached,
    _matches_folder_glob_cached
)
import sourcecombine

def test_find_and_combine_continues_to_next_root_if_first_is_empty(tmp_path):
    root1 = tmp_path / "empty"
    root1.mkdir()

    root2 = tmp_path / "full"
    root2.mkdir()
    (root2 / "file.txt").write_text("content", encoding="utf-8")

    output_path = tmp_path / "output.txt"
    config = {
        "search": {"root_folders": [os.fspath(root1), os.fspath(root2)], "recursive": True},
        "output": {"file": os.fspath(output_path), "header_template": "", "footer_template": ""},
    }

    find_and_combine_files(config, output_path, dry_run=False)

    assert output_path.read_text(encoding="utf-8") == "content"

def test_find_and_combine_skips_non_existent_root_folder(tmp_path, caplog):
    missing_root = tmp_path / "missing_root"

    output_path = tmp_path / "output.txt"
    config = {
        "search": {"root_folders": [os.fspath(missing_root)], "recursive": True},
        "output": {"file": os.fspath(output_path)},
    }

    with caplog.at_level(logging.WARNING):
        find_and_combine_files(config, output_path, dry_run=False)

    assert "The folder" in caplog.text
    assert "was not found" in caplog.text
    assert output_path.exists()

def test_silent_progress_implementation():
    # Directly test _SilentProgress to ensure full coverage of its methods
    sp = _SilentProgress(["a", "b"])
    assert list(sp) == ["a", "b"]
    assert sp.update(1) is None
    assert sp.close() is None

    with _SilentProgress() as sp_ctx:
        assert isinstance(sp_ctx, _SilentProgress)

def test_matches_glob_cached_defensive_guards():
    # Test internal functions directly to cover defensive guards for empty patterns
    assert _matches_file_glob_cached("file.txt", "file.txt", ()) is False
    assert _matches_folder_glob_cached("folder", ("folder",), ()) is False
