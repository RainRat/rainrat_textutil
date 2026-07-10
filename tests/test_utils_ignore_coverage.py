import logging
from unittest.mock import patch
import utils

def test_parse_ignore_file_non_existent(tmp_path):
    assert utils.parse_ignore_file(tmp_path / "missing_ignore_file") == []

def test_parse_ignore_file_comments_and_empty_lines(tmp_path):
    ignore_file = tmp_path / ".ignore"
    ignore_file.write_text("file1.txt\n\n# comment\n  \nfile2.txt  \n", encoding="utf-8")

    patterns = utils.parse_ignore_file(ignore_file)
    assert patterns == ["file1.txt", "file2.txt"]

def test_parse_ignore_file_exception(tmp_path, caplog):
    ignore_file = tmp_path / ".ignore"
    ignore_file.write_text("some content", encoding="utf-8")

    with patch("utils.read_file_best_effort", side_effect=Exception("Read error")):
        with caplog.at_level(logging.WARNING):
            patterns = utils.parse_ignore_file(ignore_file)

    assert patterns == []
    assert "Could not read ignore file" in caplog.text
    assert "Read error" in caplog.text
