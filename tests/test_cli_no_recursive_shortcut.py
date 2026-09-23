import os
import sys
from pathlib import Path
from unittest.mock import patch
import pytest
import sourcecombine


@pytest.fixture
def temp_cwd(tmp_path):
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(original_cwd)


@pytest.fixture
def mock_argv(monkeypatch):
    def _mock_argv(args):
        monkeypatch.setattr(sys, "argv", args)
    return _mock_argv


@pytest.mark.parametrize("flag", ["--no-recursive", "--no-rec", "--nr", "--flat"])
def test_cli_no_recursive_aliases_disable_recursion(temp_cwd, mock_argv, flag):
    """Verify that passing '--no-rec', '--nr', or '--flat' disables recursive search in CLI arguments."""
    sub_dir = temp_cwd / "subdir"
    sub_dir.mkdir()
    (temp_cwd / "root.py").write_text("print('root')", encoding="utf-8")
    (sub_dir / "child.py").write_text("print('child')", encoding="utf-8")

    mock_argv(["sourcecombine.py", ".", flag])

    captured_config = None

    def mock_find_and_combine(config, output_path, **kwargs):
        nonlocal captured_config
        captured_config = config
        return {"total_files": 1}

    with patch("sourcecombine.find_and_combine_files", side_effect=mock_find_and_combine):
        sourcecombine.main()

    assert captured_config is not None
    assert captured_config["search"]["recursive"] is False


def test_flat_alias_file_scanning_omits_subdirectories(temp_cwd, mock_argv):
    """Verify that '--flat' alias limits file scanning to top-level files."""
    sub_dir = temp_cwd / "nested"
    sub_dir.mkdir()
    (temp_cwd / "top.py").write_text("print('top')", encoding="utf-8")
    (sub_dir / "nested.py").write_text("print('nested')", encoding="utf-8")

    out_file = temp_cwd / "out.txt"
    mock_argv(["sourcecombine.py", ".", "--flat", "-o", str(out_file)])

    sourcecombine.main()

    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "top.py" in content
    assert "nested.py" not in content
