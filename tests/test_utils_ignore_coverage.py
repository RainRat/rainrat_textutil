import logging
from pathlib import Path
from unittest.mock import patch
import pytest
import utils

def test_parse_ignore_file_not_found(tmp_path):
    assert utils.parse_ignore_file(tmp_path / "does_not_exist") == []

def test_parse_ignore_file_skips_comments_and_empty_lines(tmp_path):
    ignore_file = tmp_path / ".ignore"
    ignore_file.write_text("  \n# Comment\nfile.txt\n  # Nested comment\n")
    patterns = utils.parse_ignore_file(ignore_file)
    assert patterns == ["file.txt"]

def test_parse_ignore_file_handles_read_errors(tmp_path, caplog):
    dir_path = tmp_path / "my_dir"
    dir_path.mkdir()

    with caplog.at_level(logging.WARNING):
        with patch("utils.read_file_best_effort", side_effect=Exception("Simulated error")):
            fake_file = tmp_path / "fake.txt"
            fake_file.touch()
            patterns = utils.parse_ignore_file(fake_file)
            assert patterns == []
            assert "Could not read ignore file" in caplog.text
            assert "Simulated error" in caplog.text
