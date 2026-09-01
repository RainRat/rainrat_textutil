import sys; import os; from pathlib import Path; sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

import os
import sys
import logging
import json
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock

from sourcecombine import list_backups, main

def test_list_backups_states(tmp_path):
    # Setup files:
    # 1. Matching
    file_matching = tmp_path / "matching.txt"
    file_matching.write_text("Hello World", encoding="utf-8")
    bak_matching = tmp_path / "matching.txt.bak"
    bak_matching.write_text("Hello World", encoding="utf-8")

    # 2. Modified
    file_modified = tmp_path / "modified.txt"
    file_modified.write_text("New Content", encoding="utf-8")
    bak_modified = tmp_path / "modified.txt.bak"
    bak_modified.write_text("Old Content", encoding="utf-8")

    # 3. Orphaned
    bak_orphaned = tmp_path / "orphaned.txt.bak"
    bak_orphaned.write_text("Orphaned Content", encoding="utf-8")

    # Execute
    summary = list_backups([str(tmp_path)])

    assert summary["matching"] == 1
    assert summary["modified"] == 1
    assert summary["orphaned"] == 1
    assert summary["error"] == 0
    assert summary["total"] == 3

def test_list_backups_single_file(tmp_path):
    bak = tmp_path / "file1.txt.bak"
    bak.write_text("backup")
    summary = list_backups([str(bak)])
    assert summary["total"] == 1
    assert summary["orphaned"] == 1

def test_list_backups_single_file_with_bak(tmp_path):
    file1 = tmp_path / "file1.txt"
    file1.write_text("normal")
    bak = tmp_path / "file1.txt.bak"
    bak.write_text("normal")
    summary = list_backups([str(file1)])
    assert summary["total"] == 1
    assert summary["matching"] == 1

def test_list_backups_json_format(tmp_path, capsys):
    file_matching = tmp_path / "matching.txt"
    file_matching.write_text("Hello", encoding="utf-8")
    bak_matching = tmp_path / "matching.txt.bak"
    bak_matching.write_text("Hello", encoding="utf-8")

    list_backups([str(tmp_path)], json_format=True)
    captured = capsys.readouterr()

    # Parse output as JSON
    data = json.loads(captured.out)
    assert data["title"] == "Backup Files Report"
    assert data["summary"]["matching"] == 1
    assert data["summary"]["total"] == 1
    assert data["backups"][0]["status"] == "MATCHING"

def test_list_backups_error_handling(tmp_path):
    bak = tmp_path / "error.txt.bak"
    bak.write_text("broken")

    real_stat = Path.stat
    def mock_stat(self, *args, **kwargs):
        if self.name == "error.txt.bak":
            raise OSError("Permission denied")
        return real_stat(self, *args, **kwargs)

    # Mock stat() to raise OSError specifically for error.txt.bak
    with patch.object(Path, "stat", mock_stat):
        summary = list_backups([str(tmp_path)])
        assert summary["error"] == 1
        assert summary["total"] == 1

def test_list_backups_defaults_to_current_folder(capsys):
    with patch("sourcecombine.Path") as mock_path:
        mock_instance = mock_path.return_value
        mock_instance.exists.return_value = False

        summary = list_backups([])
        assert summary["total"] == 0
        mock_path.assert_any_call(".")
        captured = capsys.readouterr()
        assert "No backup files (.bak) found." in captured.out

def test_list_backups_logs_warning_on_non_existent_target(tmp_path, caplog):
    non_existent = tmp_path / "does_not_exist"
    caplog.set_level(logging.WARNING)
    summary = list_backups([str(non_existent)])
    assert summary["total"] == 0
    assert f"Target folder not found: {non_existent}" in caplog.text

def test_list_backups_cli_integration(tmp_path, capsys):
    bak = tmp_path / "file.txt.bak"
    bak.write_text("backup")

    with patch("sys.argv", ["sourcecombine.py", str(tmp_path), "--list-backups"]):
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 0

    captured = capsys.readouterr()
    assert "BACKUP FILES REPORT" in captured.out
    assert "file.txt.bak" in captured.out

def test_list_backups_cli_integration_alias(tmp_path, capsys):
    bak = tmp_path / "file.txt.bak"
    bak.write_text("backup")

    with patch("sys.argv", ["sourcecombine.py", str(tmp_path), "--list-bak"]):
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 0

    captured = capsys.readouterr()
    assert "BACKUP FILES REPORT" in captured.out
    assert "file.txt.bak" in captured.out

def test_list_backups_cli_integration_json(tmp_path, capsys):
    bak = tmp_path / "file.txt.bak"
    bak.write_text("backup")

    with patch("sys.argv", ["sourcecombine.py", str(tmp_path), "--list-backups", "--json"]):
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 0

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["title"] == "Backup Files Report"
    assert data["summary"]["orphaned"] == 1
