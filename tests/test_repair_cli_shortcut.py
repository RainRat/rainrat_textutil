import sys
import os
from pathlib import Path

sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

from unittest.mock import patch
import pytest
import json

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

def test_repair_without_verify_shortcut(temp_cwd, mock_argv):
    target_dir = temp_cwd / "target"
    target_dir.mkdir()

    manifest_data = [
        {
            "path": "new_file.txt",
            "content": "shortcut content",
            "size_bytes": 16
        }
    ]
    manifest_file = temp_cwd / "combined_files.json"
    manifest_file.write_text(json.dumps(manifest_data), encoding="utf-8")

    with mock_argv(["--repair", "--output", str(target_dir), str(manifest_file)]):
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 0

    restored_file = target_dir / "new_file.txt"
    assert restored_file.exists()
    assert restored_file.read_text(encoding="utf-8") == "shortcut content"
