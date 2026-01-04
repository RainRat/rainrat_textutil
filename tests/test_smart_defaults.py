import os
import shutil
from pathlib import Path
import pytest
from sourcecombine import find_and_combine_files
from utils import DEFAULT_CONFIG

@pytest.fixture
def temp_workspace(tmp_path):
    # Create a workspace with standard ignored folders
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("config")

    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "foo.pyc").write_text("binary")

    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "pkg.json").write_text("{}")

    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('hello')")

    return tmp_path

def test_defaults_ignore_noise(temp_workspace):
    """Test that default configuration ignores common noise folders/files."""

    # Use a copy of DEFAULT_CONFIG to ensure we are testing the actual defaults
    # (Note: We expect the defaults to be updated in utils.py)
    config = DEFAULT_CONFIG.copy()
    config['search'] = {'root_folders': [str(temp_workspace)]}

    output_path = temp_workspace / "combined.txt"

    # Using dry_run=False to actually traverse, but we check stats
    stats = find_and_combine_files(
        config,
        output_path=str(output_path),
        dry_run=True  # Dry run is sufficient to get stats
    )

    # We expect only src/main.py to be processed
    # .git, __pycache__, node_modules should be ignored by default

    # Currently (before fix), this will include .git/config, __pycache__/foo.pyc, node_modules/pkg.json
    # So total files would be 4.
    # After fix, total files should be 1.

    processed_files = []
    # We can't easily inspect the 'stats' for filenames, but we can rely on total_files count
    # provided we know exactly what's there.

    assert stats['total_files'] == 1, f"Expected 1 file, got {stats['total_files']}"
