import os
import sys
import logging
from pathlib import Path
import pytest
from unittest.mock import patch

# Adjust sys.path to include the project root
sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

from sourcecombine import restore_backups, main

def test_restore_backups_recursive(tmp_path):
    """Test recursive restoration of .bak files in a directory."""
    sub = tmp_path / "subdir"
    sub.mkdir()

    file1 = tmp_path / "file1.txt"
    bak1 = tmp_path / "file1.txt.bak"
    file1.write_text("Modified 1")
    bak1.write_text("Original 1")

    file2 = sub / "file2.txt"
    bak2 = sub / "file2.txt.bak"
    file2.write_text("Modified 2")
    bak2.write_text("Original 2")

    restored, errors = restore_backups([str(tmp_path)])

    assert restored == 2
    assert errors == 0
    assert file1.read_text() == "Original 1"
    assert file2.read_text() == "Original 2"
    assert not bak1.exists()
    assert not bak2.exists()

def test_restore_backups_single_file_target(tmp_path):
    """Test restoration when a single original file is targeted."""
    file1 = tmp_path / "file1.txt"
    bak1 = tmp_path / "file1.txt.bak"
    file1.write_text("Modified 1")
    bak1.write_text("Original 1")

    restored, errors = restore_backups([str(file1)])

    assert restored == 1
    assert errors == 0
    assert file1.read_text() == "Original 1"
    assert not bak1.exists()

def test_restore_backups_single_bak_target(tmp_path):
    """Test restoration when a single .bak file is targeted."""
    file1 = tmp_path / "file1.txt"
    bak1 = tmp_path / "file1.txt.bak"
    file1.write_text("Modified 1")
    bak1.write_text("Original 1")

    restored, errors = restore_backups([str(bak1)])

    assert restored == 1
    assert errors == 0
    assert file1.read_text() == "Original 1"
    assert not bak1.exists()

def test_restore_backups_dry_run(tmp_path):
    """Test restoration with dry_run=True."""
    file1 = tmp_path / "file1.txt"
    bak1 = tmp_path / "file1.txt.bak"
    file1.write_text("Modified 1")
    bak1.write_text("Original 1")

    restored, errors = restore_backups([str(tmp_path)], dry_run=True)

    assert restored == 1
    assert errors == 0
    assert file1.read_text() == "Modified 1"
    assert bak1.exists()

def test_restore_backups_no_backups(tmp_path, caplog):
    """Test restoration when no backups exist."""
    caplog.set_level(logging.INFO)
    restored, errors = restore_backups([str(tmp_path)])
    assert restored == 0
    assert errors == 0
    assert "No backup files (.bak) found" in caplog.text

def test_restore_backups_non_existent_target(caplog):
    """Test restoration with a non-existent target."""
    caplog.set_level(logging.WARNING)
    restored, errors = restore_backups(["/non/existent/path"])
    assert restored == 0
    assert errors == 0
    assert "Target folder not found" in caplog.text

def test_restore_cli_integration(tmp_path):
    """Test --restore CLI flag integration."""
    file1 = tmp_path / "file1.txt"
    bak1 = tmp_path / "file1.txt.bak"
    file1.write_text("Modified 1")
    bak1.write_text("Original 1")

    # We need to mock sys.exit(0) because --restore calls it
    with patch("sys.argv", ["sourcecombine.py", str(tmp_path), "--restore"]):
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 0

    assert file1.read_text() == "Original 1"
    assert not bak1.exists()

def test_restore_backups_error_handling(tmp_path):
    """Test restoration error handling (e.g., permission error)."""
    file1 = tmp_path / "file1.txt"
    bak1 = tmp_path / "file1.txt.bak"
    file1.write_text("Modified 1")
    bak1.write_text("Original 1")

    with patch("shutil.move", side_effect=OSError("Permission denied")):
        restored, errors = restore_backups([str(tmp_path)])
        assert restored == 0
        assert errors == 1
        assert file1.read_text() == "Modified 1"
        assert bak1.exists()
