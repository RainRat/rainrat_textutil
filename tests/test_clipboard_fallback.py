import sys
import os
from pathlib import Path
import logging
from unittest.mock import patch, MagicMock
import pytest

sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

import sourcecombine
import utils

@pytest.fixture
def temp_cwd(tmp_path):
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(original_cwd)

def test_clipboard_fallback_on_copy_exception(temp_cwd, caplog):
    caplog.set_level(logging.INFO)

    # Create a dummy file to scan
    sample_file = temp_cwd / "hello.py"
    sample_file.write_text("print('hello')", encoding="utf-8")

    config = {
        "search": {"root_folders": [os.fspath(temp_cwd)], "recursive": True},
        "filters": {},
        "processing": {},
        "output": {"file": "combined_files.txt", "header_template": "", "footer_template": ""},
    }

    # Mock pyperclip copy to raise an Exception
    mock_pyperclip = MagicMock()
    mock_pyperclip.copy.side_effect = Exception("Clipboard is not available on headless display")

    with patch("sourcecombine._get_pyperclip", return_value=mock_pyperclip):
        sourcecombine.find_and_combine_files(
            config,
            output_path="fallback_combined.txt",
            dry_run=False,
            clipboard=True,
            output_format="text"
        )

    # Check that error was logged
    assert "Failed to copy combined output to clipboard" in caplog.text
    assert "Fallback: Saved combined output" in caplog.text

    # Check that fallback file was written correctly
    fallback_file = temp_cwd / "fallback_combined.txt"
    assert fallback_file.exists()
    assert fallback_file.read_text(encoding="utf-8") == "print('hello')"


def test_clipboard_fallback_on_missing_pyperclip(temp_cwd, caplog):
    caplog.clear()
    caplog.set_level(logging.INFO)

    # Create a dummy file to scan
    sample_file = temp_cwd / "hello.py"
    sample_file.write_text("print('hello')", encoding="utf-8")

    config = {
        "search": {"root_folders": [os.fspath(temp_cwd)], "recursive": True},
        "filters": {},
        "processing": {},
        "output": {"file": "combined_files.txt", "header_template": "", "footer_template": ""},
    }

    with patch("sourcecombine._get_pyperclip", return_value=None):
        sourcecombine.find_and_combine_files(
            config,
            output_path="fallback_missing.txt",
            dry_run=False,
            clipboard=True,
            output_format="text"
        )

    assert "We need the 'pyperclip' library to copy to the clipboard" in caplog.text
    assert "Fallback: Saved combined output" in caplog.text

    fallback_file = temp_cwd / "fallback_missing.txt"
    assert fallback_file.exists()
    assert fallback_file.read_text(encoding="utf-8") == "print('hello')"


def test_clipboard_fallback_with_none_or_dash_output_path(temp_cwd, caplog):
    caplog.clear()
    caplog.set_level(logging.INFO)

    sample_file = temp_cwd / "hello.py"
    sample_file.write_text("print('hello')", encoding="utf-8")

    config = {
        "search": {"root_folders": [os.fspath(temp_cwd)], "recursive": True},
        "filters": {},
        "processing": {},
        "output": {"header_template": "", "footer_template": ""},
    }

    # Test for markdown format fallback path (None or '-')
    with patch("sourcecombine._get_pyperclip", return_value=None):
        sourcecombine.find_and_combine_files(
            config,
            output_path=None,
            dry_run=False,
            clipboard=True,
            output_format="markdown"
        )

    assert "Fallback: Saved combined output to 'combined_files.md' instead." in caplog.text
    fallback_file = temp_cwd / "combined_files.md"
    assert fallback_file.exists()
    assert "print('hello')" in fallback_file.read_text(encoding="utf-8")
