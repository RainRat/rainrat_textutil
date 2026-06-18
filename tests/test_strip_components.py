import sys; import os; from pathlib import Path; sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

import logging
import pytest
from unittest.mock import patch
from pathlib import Path
import io
import json

from sourcecombine import main

@pytest.fixture(autouse=True)
def reset_logging():
    """Reset logging before and after each test."""
    root = logging.getLogger()
    for h in root.handlers[:]:
        root.removeHandler(h)
    root.setLevel(logging.NOTSET)
    yield
    for h in root.handlers[:]:
        root.removeHandler(h)

@pytest.fixture
def mock_argv():
    """Context manager to mock sys.argv."""
    def _mock_argv(args):
        return patch.object(sys, 'argv', ['sourcecombine.py'] + args)
    return _mock_argv

@pytest.fixture
def temp_cwd(tmp_path):
    """Context manager to change current working directory."""
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(original_cwd)

def test_extract_strip_components(temp_cwd, mock_argv):
    """Test extracting files with --strip-components."""
    # Create a manifest with nested paths
    manifest = [
        {"path": "src/main.py", "content": "print('hello')", "size_bytes": 14},
        {"path": "tests/test_main.py", "content": "def test_hello(): pass", "size_bytes": 22}
    ]
    manifest_file = temp_cwd / "combined.json"
    manifest_file.write_text(json.dumps(manifest), encoding="utf-8")

    # Extract with --strip-components 1
    output_dir = temp_cwd / "out"
    output_dir.mkdir()

    with mock_argv(['--extract', str(manifest_file), '--output', str(output_dir), '--strip-components', '1']):
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 0

    # Check that src/main.py became out/main.py
    assert (output_dir / "main.py").exists()
    assert (output_dir / "test_main.py").exists()
    assert not (output_dir / "src").exists()
    assert not (output_dir / "tests").exists()

    assert (output_dir / "main.py").read_text() == "print('hello')"

def test_verify_strip_components(temp_cwd, mock_argv):
    """Test verifying files with --strip-components."""
    # Create a manifest with nested paths
    manifest = [
        {"path": "long/path/to/file.txt", "content": "content", "size_bytes": 7, "sha256": "ed7002b439e9ac845f22357d822baa14447c03341ed069ba0c2bb4507306c6c2"}
    ]
    manifest_file = temp_cwd / "combined.json"
    manifest_file.write_text(json.dumps(manifest), encoding="utf-8")

    # Create the file on disk at a different location (stripped)
    file_on_disk = temp_cwd / "file.txt"
    file_on_disk.write_text("content", encoding="utf-8")

    # Verify with --strip-components 3
    with mock_argv(['--verify', str(manifest_file), '--strip-components', '3']):
        with patch('sys.exit') as mock_exit:
            main()
            # If verify fails, it might call sys.exit(1). If it passes, it shouldn't or it might exit(0)
            if mock_exit.called:
                assert mock_exit.call_args[0][0] == 0

def test_strip_components_too_many(temp_cwd, mock_argv, caplog):
    """Test warning when path has fewer components than the strip limit."""
    caplog.set_level(logging.WARNING)
    manifest = [
        {"path": "file.txt", "content": "content", "size_bytes": 7}
    ]
    manifest_file = temp_cwd / "combined.json"
    manifest_file.write_text(json.dumps(manifest), encoding="utf-8")

    output_dir = temp_cwd / "out2"
    output_dir.mkdir()

    with mock_argv(['--extract', str(manifest_file), '--output', str(output_dir), '--strip-components', '2']):
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 0

    assert "Skipping path with fewer than 2 components: file.txt" in caplog.text
    assert not (output_dir / "file.txt").exists()
