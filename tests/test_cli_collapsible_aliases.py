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

def test_cli_collapsible_details_alias(temp_cwd, mock_argv):
    """Test --details shortcut alias enables collapsible HTML blocks in Markdown output."""
    src_dir = temp_cwd / "src"
    src_dir.mkdir()
    file_a = src_dir / "a.py"
    file_a.write_text("print('hello')", encoding="utf-8")

    output_file = temp_cwd / "combined.md"

    with mock_argv([
        str(src_dir),
        "--output", str(output_file),
        "--format", "markdown",
        "--details"
    ]):
        try:
            main()
        except SystemExit as e:
            assert e.code == 0

    combined_content = output_file.read_text(encoding="utf-8")
    assert "<details><summary><b>a.py</b>" in combined_content
    assert "</details>" in combined_content

def test_cli_collapsible_col_alias(temp_cwd, mock_argv):
    """Test --col shortcut alias enables collapsible HTML blocks in Markdown output."""
    src_dir = temp_cwd / "src"
    src_dir.mkdir()
    file_b = src_dir / "b.py"
    file_b.write_text("print('world')", encoding="utf-8")

    output_file = temp_cwd / "combined.md"

    with mock_argv([
        str(src_dir),
        "--output", str(output_file),
        "--format", "markdown",
        "--col"
    ]):
        try:
            main()
        except SystemExit as e:
            assert e.code == 0

    combined_content = output_file.read_text(encoding="utf-8")
    assert "<details><summary><b>b.py</b>" in combined_content
    assert "</details>" in combined_content
