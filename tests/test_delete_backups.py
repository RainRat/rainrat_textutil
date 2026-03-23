import os
import sys
import logging
from pathlib import Path
import pytest
from unittest.mock import patch

sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

from sourcecombine import delete_backups, main

def test_delete_backups_recursive(tmp_path):
    sub = tmp_path / "subdir"
    sub.mkdir()

    bak1 = tmp_path / "file1.txt.bak"
    bak1.write_text("Backup 1")

    bak2 = sub / "file2.txt.bak"
    bak2.write_text("Backup 2")

    file1 = tmp_path / "file1.txt"
    file1.write_text("Normal file")

    deleted, errors = delete_backups([str(tmp_path)])

    assert deleted == 2
    assert errors == 0
    assert not bak1.exists()
    assert not bak2.exists()
    assert file1.exists()

def test_delete_backups_single_file(tmp_path):
    bak1 = tmp_path / "file1.txt.bak"
    bak1.write_text("Backup 1")

    deleted, errors = delete_backups([str(bak1)])

    assert deleted == 1
    assert errors == 0
    assert not bak1.exists()

def test_delete_backups_dry_run(tmp_path):
    bak1 = tmp_path / "file1.txt.bak"
    bak1.write_text("Backup 1")

    deleted, errors = delete_backups([str(tmp_path)], dry_run=True)

    assert deleted == 1
    assert errors == 0
    assert bak1.exists()

def test_delete_backups_defaults_to_current_folder_when_targets_empty():
    with patch("sourcecombine.Path") as mock_path:
        mock_instance = mock_path.return_value
        mock_instance.exists.return_value = False

        deleted, errors = delete_backups([])

        assert deleted == 0
        assert errors == 0
        mock_path.assert_any_call(".")

def test_delete_backups_logs_warning_on_non_existent_target(tmp_path, caplog):
    non_existent = tmp_path / "does_not_exist"
    caplog.set_level(logging.WARNING)
    deleted, errors = delete_backups([str(non_existent)])
    assert deleted == 0
    assert errors == 0
    assert f"Target folder not found: {non_existent}" in caplog.text

def test_delete_backups_no_backups(tmp_path, caplog):
    caplog.set_level(logging.INFO)
    deleted, errors = delete_backups([str(tmp_path)])
    assert deleted == 0
    assert errors == 0
    assert "No backup files (.bak) found" in caplog.text

def test_delete_backups_error_handling(tmp_path):
    bak1 = tmp_path / "file1.txt.bak"
    bak1.write_text("Backup 1")

    with patch("os.remove", side_effect=OSError("Permission denied")):
        deleted, errors = delete_backups([str(tmp_path)])
        assert deleted == 0
        assert errors == 1
        assert bak1.exists()

def test_delete_backups_cli_integration(tmp_path):
    bak1 = tmp_path / "file1.txt.bak"
    bak1.write_text("Backup 1")

    with patch("sys.argv", ["sourcecombine.py", str(tmp_path), "--delete-backups"]):
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 0

    assert not bak1.exists()
