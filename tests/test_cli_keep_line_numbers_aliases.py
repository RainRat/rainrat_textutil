import sys
import os
from pathlib import Path
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

def test_extract_keep_lines_alias(temp_cwd, mock_argv):
    """Test --keep-lines shortcut alias preserves line numbers during extraction."""
    extracted_dir = temp_cwd / "extracted_lines"
    extracted_dir.mkdir()

    combined_content = "## test.py\n\n```python\n 1 | def foo():\n 2 |     return True\n```\n"
    combined_file = temp_cwd / "combined_files.md"
    combined_file.write_text(combined_content, encoding="utf-8")

    with mock_argv(["--extract", str(combined_file), "--output", str(extracted_dir), "--keep-lines"]):
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 0

    extracted_file = extracted_dir / "test.py"
    assert extracted_file.exists()
    content = extracted_file.read_text(encoding="utf-8")
    assert " 1 | def foo():" in content
    assert " 2 |     return True" in content

def test_extract_keep_ln_alias(temp_cwd, mock_argv):
    """Test --keep-ln shortcut alias preserves line numbers during extraction."""
    extracted_dir = temp_cwd / "extracted_ln"
    extracted_dir.mkdir()

    combined_content = "## test.py\n\n```python\n 1 | def foo():\n 2 |     return True\n```\n"
    combined_file = temp_cwd / "combined_files.md"
    combined_file.write_text(combined_content, encoding="utf-8")

    with mock_argv(["--extract", str(combined_file), "--output", str(extracted_dir), "--keep-ln"]):
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 0

    extracted_file = extracted_dir / "test.py"
    assert extracted_file.exists()
    content = extracted_file.read_text(encoding="utf-8")
    assert " 1 | def foo():" in content
    assert " 2 |     return True" in content
