import sys
import os
from pathlib import Path
sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

import json
import logging
import pytest
from unittest.mock import patch

from sourcecombine import list_backups, main

def test_list_backups_recursive(tmp_path, capsys, caplog):
    caplog.set_level(logging.INFO)
    sub = tmp_path / "subdir"
    sub.mkdir()

    bak1 = tmp_path / "file1.txt.bak"
    bak1.write_text("Backup 1 content")

    bak2 = sub / "file2.py.bak"
    bak2.write_text("Backup 2 python content")

    count = list_backups([str(tmp_path)])
    assert count == 2

    captured = capsys.readouterr()
    assert "Original File" in captured.out
    assert "file1.txt" in captured.out
    assert "subdir/file2.py" in captured.out
    assert "Total backup files: 2" in caplog.text

def test_list_backups_single_file(tmp_path, capsys):
    bak1 = tmp_path / "file1.txt.bak"
    bak1.write_text("Backup 1 content")

    count = list_backups([str(bak1)])
    assert count == 1

    captured = capsys.readouterr()
    assert "Original File" in captured.out
    assert "file1.txt" in captured.out

def test_list_backups_with_query_filtering(tmp_path, capsys, caplog):
    caplog.set_level(logging.INFO)
    sub = tmp_path / "subdir"
    sub.mkdir()

    bak1 = tmp_path / "file1.txt.bak"
    bak1.write_text("Backup 1")

    bak2 = sub / "utils.py.bak"
    bak2.write_text("Backup 2")

    # Match utils
    count = list_backups([str(tmp_path)], query="utils")
    assert count == 1
    captured = capsys.readouterr()
    assert "utils.py" in captured.out
    assert "file1.txt" not in captured.out

    # No match query
    count2 = list_backups([str(tmp_path)], query="non_existent_pattern")
    assert count2 == 0
    assert "No backup files (.bak) matched query 'non_existent_pattern'" in caplog.text

def test_list_backups_json_format(tmp_path, capsys):
    bak1 = tmp_path / "file1.txt.bak"
    bak1.write_text("Backup 1")

    count = list_backups([str(tmp_path)], json_format=True)
    assert count == 1

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "backups" in data
    assert data["total"] == 1
    assert data["backups"][0]["original_path"] == "file1.txt"
    assert data["backups"][0]["size"] == 8

def test_list_backups_non_existent_target(tmp_path, caplog):
    caplog.set_level(logging.WARNING)
    non_existent = tmp_path / "not_here"
    count = list_backups([str(non_existent)])
    assert count == 0
    assert f"Target folder not found: {non_existent}" in caplog.text

def test_list_backups_os_error_handling(tmp_path, caplog):
    caplog.set_level(logging.ERROR)
    bak1 = tmp_path / "file1.txt.bak"
    bak1.write_text("Backup 1")

    orig_stat = Path.stat
    def mock_stat(self, *args, **kwargs):
        if self.suffix == ".bak":
            raise OSError("Permission denied")
        return orig_stat(self, *args, **kwargs)

    with patch.object(Path, "stat", mock_stat):
        count = list_backups([str(tmp_path)])
        assert count == 0
        assert "Failed to read stats for" in caplog.text

def test_list_backups_cli_integration(tmp_path, capsys):
    bak1 = tmp_path / "file1.txt.bak"
    bak1.write_text("Backup 1")

    with patch("sys.argv", ["sourcecombine.py", str(tmp_path), "--list-backups"]):
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 0

    captured = capsys.readouterr()
    assert "file1.txt" in captured.out

def test_list_backups_cli_json_integration(tmp_path, capsys):
    bak1 = tmp_path / "file1.txt.bak"
    bak1.write_text("Backup 1")

    with patch("sys.argv", ["sourcecombine.py", str(tmp_path), "--list-backups", "--json"]):
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 0

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["total"] == 1
    assert data["backups"][0]["original_path"] == "file1.txt"
