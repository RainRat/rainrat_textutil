import sys
import os
from pathlib import Path
import json
from unittest.mock import patch
import pytest

sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

from sourcecombine import main

@pytest.fixture
def temp_cwd(tmp_path):
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(original_cwd)

@pytest.fixture
def mock_argv():
    def _mock_argv(args):
        return patch.object(sys, 'argv', ['sourcecombine.py'] + args)
    return _mock_argv

def test_verify_with_y_shortcut(temp_cwd, mock_argv):
    target_dir = temp_cwd / "target"
    target_dir.mkdir()

    # Create the expected file
    test_file = target_dir / "test_file.txt"
    test_file.write_text("hello shorty", encoding="utf-8")

    manifest_data = [
        {
            "path": "test_file.txt",
            "content": "hello shorty",
            "size_bytes": 12
        }
    ]
    manifest_file = temp_cwd / "combined_files.json"
    manifest_file.write_text(json.dumps(manifest_data), encoding="utf-8")

    # Call with -y
    with mock_argv(["-y", "--output", str(target_dir), str(manifest_file)]):
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 0

def test_repair_with_P_shortcut(temp_cwd, mock_argv):
    target_dir = temp_cwd / "target"
    target_dir.mkdir()

    manifest_data = [
        {
            "path": "repaired_file.txt",
            "content": "perfectly repaired",
            "size_bytes": 18
        }
    ]
    manifest_file = temp_cwd / "combined_files.json"
    manifest_file.write_text(json.dumps(manifest_data), encoding="utf-8")

    # Call with -P
    with mock_argv(["-P", "--output", str(target_dir), str(manifest_file)]):
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 0

    repaired_file = target_dir / "repaired_file.txt"
    assert repaired_file.exists()
    assert repaired_file.read_text(encoding="utf-8") == "perfectly repaired"
