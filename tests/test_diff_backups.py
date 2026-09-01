import sys; import os; from pathlib import Path; sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

import os
import sys
import logging
import json
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock

from sourcecombine import diff_backups, main
import utils

def test_diff_backups_states(tmp_path, capsys):
    # Setup files:
    # 1. Matching
    file_matching = tmp_path / "matching.txt"
    file_matching.write_text("Hello World\nLine 2\n", encoding="utf-8")
    bak_matching = tmp_path / "matching.txt.bak"
    bak_matching.write_text("Hello World\nLine 2\n", encoding="utf-8")

    # 2. Modified
    file_modified = tmp_path / "modified.txt"
    file_modified.write_text("Hello World\nLine 2 edited\n", encoding="utf-8")
    bak_modified = tmp_path / "modified.txt.bak"
    bak_modified.write_text("Hello World\nLine 2 original\n", encoding="utf-8")

    # 3. Orphaned
    bak_orphaned = tmp_path / "orphaned.txt.bak"
    bak_orphaned.write_text("Orphaned Content\n", encoding="utf-8")

    # Execute
    summary = diff_backups([str(tmp_path)], json_format=False)

    assert summary["matching"] == 1
    assert summary["modified"] == 1
    assert summary["orphaned"] == 1
    assert summary["error"] == 0
    assert summary["total"] == 3

    captured = capsys.readouterr()
    assert "[MATCHING]" in captured.out
    assert "[MODIFIED]" in captured.out
    assert "[ORPHANED]" in captured.out
    assert "Line 2 edited" in captured.out
    assert "Line 2 original" in captured.out

def test_diff_backups_single_file(tmp_path):
    bak = tmp_path / "file1.txt.bak"
    bak.write_text("backup")
    summary = diff_backups([str(bak)])
    assert summary["total"] == 1
    assert summary["orphaned"] == 1

def test_diff_backups_single_file_with_bak(tmp_path):
    file1 = tmp_path / "file1.txt"
    file1.write_text("normal")
    bak = tmp_path / "file1.txt.bak"
    bak.write_text("normal")
    summary = diff_backups([str(file1)])
    assert summary["total"] == 1
    assert summary["matching"] == 1

def test_diff_backups_json_format(tmp_path, capsys):
    file_modified = tmp_path / "modified.txt"
    file_modified.write_text("Hello\nWorld\n", encoding="utf-8")
    bak_modified = tmp_path / "modified.txt.bak"
    bak_modified.write_text("Hello\nThere\n", encoding="utf-8")

    diff_backups([str(tmp_path)], json_format=True)
    captured = capsys.readouterr()

    # Parse output as JSON
    data = json.loads(captured.out)
    assert data["title"] == "Backup Diffs Report"
    assert data["summary"]["modified"] == 1
    assert data["summary"]["total"] == 1
    assert data["diffs"][0]["status"] == "MODIFIED"
    assert "World" in data["diffs"][0]["diff"]
    assert "There" in data["diffs"][0]["diff"]

def test_diff_backups_error_handling(tmp_path):
    file1 = tmp_path / "error.txt"
    file1.write_text("original")
    bak = tmp_path / "error.txt.bak"
    bak.write_text("backup")

    def mock_read_file_best_effort(file_path):
        if "error.txt" in str(file_path):
            raise OSError("Permission denied")
        return "original", "utf-8"

    # Mock read_file_best_effort to raise OSError specifically for error.txt
    with patch("utils.read_file_best_effort", mock_read_file_best_effort):
        summary = diff_backups([str(tmp_path)])
        assert summary["error"] == 1
        assert summary["total"] == 1

def test_diff_backups_defaults_to_current_folder(capsys):
    with patch("sourcecombine.Path") as mock_path:
        mock_instance = mock_path.return_value
        mock_instance.exists.return_value = False

        summary = diff_backups([])
        assert summary["total"] == 0
        mock_path.assert_any_call(".")
        captured = capsys.readouterr()
        assert "No backup files (.bak) found." in captured.out

def test_diff_backups_logs_warning_on_non_existent_target(tmp_path, caplog):
    non_existent = tmp_path / "does_not_exist"
    caplog.set_level(logging.WARNING)
    summary = diff_backups([str(non_existent)])
    assert summary["total"] == 0
    assert f"Target folder not found: {non_existent}" in caplog.text

def test_diff_backups_cli_integration(tmp_path, capsys):
    file_modified = tmp_path / "file.txt"
    file_modified.write_text("Hello\nWorld\n", encoding="utf-8")
    bak = tmp_path / "file.txt.bak"
    bak.write_text("Hello\nThere\n", encoding="utf-8")

    with patch("sys.argv", ["sourcecombine.py", str(tmp_path), "--diff-backups"]):
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 0

    captured = capsys.readouterr()
    assert "BACKUP DIFFS REPORT" in captured.out
    assert "file.txt.bak" in captured.out
    assert "World" in captured.out

def test_diff_backups_cli_integration_json(tmp_path, capsys):
    bak = tmp_path / "file.txt.bak"
    bak.write_text("backup")

    with patch("sys.argv", ["sourcecombine.py", str(tmp_path), "--diff-backups", "--json"]):
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 0

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["title"] == "Backup Diffs Report"
    assert data["summary"]["orphaned"] == 1
