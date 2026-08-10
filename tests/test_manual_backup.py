import sys
import os
import logging
import json
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

from sourcecombine import create_backups_for_targets, main
import utils

def test_manual_backup_recursive(tmp_path):
    sub = tmp_path / "subdir"
    sub.mkdir()

    file1 = tmp_path / "file1.txt"
    file1.write_text("Hello file 1")

    file2 = sub / "file2.txt"
    file2.write_text("Hello file 2")

    config = utils.DEFAULT_CONFIG.copy()

    backed_up, errors = create_backups_for_targets([str(tmp_path)], config)

    assert backed_up == 2
    assert errors == 0
    assert Path(f"{file1}.bak").exists()
    assert Path(f"{file2}.bak").exists()
    assert Path(f"{file1}.bak").read_text() == "Hello file 1"
    assert Path(f"{file2}.bak").read_text() == "Hello file 2"

def test_manual_backup_single_file(tmp_path):
    file1 = tmp_path / "file1.txt"
    file1.write_text("Hello file 1")

    config = utils.DEFAULT_CONFIG.copy()

    backed_up, errors = create_backups_for_targets([str(file1)], config)

    assert backed_up == 1
    assert errors == 0
    assert Path(f"{file1}.bak").exists()
    assert Path(f"{file1}.bak").read_text() == "Hello file 1"

def test_manual_backup_dry_run(tmp_path):
    file1 = tmp_path / "file1.txt"
    file1.write_text("Hello file 1")

    config = utils.DEFAULT_CONFIG.copy()

    backed_up, errors = create_backups_for_targets([str(tmp_path)], config, dry_run=True)

    assert backed_up == 1
    assert errors == 0
    assert not Path(f"{file1}.bak").exists()

def test_manual_backup_json_format(tmp_path, capsys):
    file1 = tmp_path / "file1.txt"
    file1.write_text("Hello file 1")

    config = utils.DEFAULT_CONFIG.copy()

    backed_up, errors = create_backups_for_targets([str(tmp_path)], config, json_format=True)

    assert backed_up == 1
    assert errors == 0

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["title"] == "Backup Creation Report"
    assert len(data["backups"]) == 1
    assert data["backups"][0]["path"] == "file1.txt"
    assert data["backups"][0]["status"] == "CREATED"
    assert data["summary"]["created"] == 1
    assert data["summary"]["errors"] == 0

def test_manual_backup_dry_run_json(tmp_path, capsys):
    file1 = tmp_path / "file1.txt"
    file1.write_text("Hello file 1")

    config = utils.DEFAULT_CONFIG.copy()

    backed_up, errors = create_backups_for_targets([str(tmp_path)], config, dry_run=True, json_format=True)

    assert backed_up == 1
    assert errors == 0

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["backups"][0]["status"] == "PREVIEW"
    assert data["summary"]["preview"] == 1

def test_manual_backup_non_existent_target(tmp_path, caplog):
    non_existent = tmp_path / "does_not_exist"
    caplog.set_level(logging.WARNING)

    config = utils.DEFAULT_CONFIG.copy()
    backed_up, errors = create_backups_for_targets([str(non_existent)], config)

    assert backed_up == 0
    assert errors == 0
    assert f"Target folder not found: {non_existent}" in caplog.text

def test_manual_backup_os_error_handling(tmp_path):
    file1 = tmp_path / "file1.txt"
    file1.write_text("Hello file 1")

    config = utils.DEFAULT_CONFIG.copy()

    with patch("shutil.copy2", side_effect=OSError("Permission denied")):
        backed_up, errors = create_backups_for_targets([str(tmp_path)], config)
        assert backed_up == 0
        assert errors == 1

def test_manual_backup_missing_file_error(tmp_path):
    file1 = tmp_path / "file1.txt"
    file1.write_text("Hello file 1")

    config = utils.DEFAULT_CONFIG.copy()

    # Simulate target file deletion right before copy
    with patch("shutil.copy2", side_effect=FileNotFoundError("No such file or directory")):
        backed_up, errors = create_backups_for_targets([str(file1)], config)
        assert backed_up == 0
        assert errors == 1

def test_manual_backup_respects_filters(tmp_path):
    sub = tmp_path / "subdir"
    sub.mkdir()

    file1 = tmp_path / "file1.txt"
    file1.write_text("Hello file 1")

    file2 = sub / "file2.py"
    file2.write_text("print('python')")

    config = utils.DEFAULT_CONFIG.copy()
    config["search"] = config.get("search", {}).copy()
    config["search"]["allowed_extensions"] = [".py"]

    backed_up, errors = create_backups_for_targets([str(tmp_path)], config)

    # Only file2.py has a .py extension, file1.txt should be skipped
    assert backed_up == 1
    assert errors == 0
    assert Path(f"{file2}.bak").exists()
    assert not Path(f"{file1}.bak").exists()

def test_manual_backup_cli_integration(tmp_path):
    file1 = tmp_path / "file1.txt"
    file1.write_text("Hello file 1")

    with patch("sys.argv", ["sourcecombine.py", str(tmp_path), "--backup"]):
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 0

    assert Path(f"{file1}.bak").exists()
    assert Path(f"{file1}.bak").read_text() == "Hello file 1"

def test_manual_backup_defaults_to_dot():
    with patch("sourcecombine.Path") as mock_path:
        mock_instance = mock_path.return_value
        mock_instance.exists.return_value = False

        create_backups_for_targets([], utils.DEFAULT_CONFIG.copy())

        mock_path.assert_any_call(".")

def test_manual_backup_resolve_error(tmp_path):
    config = utils.DEFAULT_CONFIG.copy()
    config["output"] = config.get("output", {}).copy()
    config["output"]["file"] = "somefile.txt"

    with patch("pathlib.Path.resolve", side_effect=OSError("Resolve failed")), \
         patch("pathlib.Path.absolute", side_effect=OSError("Absolute failed")):
        backed_up, errors = create_backups_for_targets([str(tmp_path)], config)
        assert errors == 0

def test_manual_backup_collect_paths_error(tmp_path):
    config = utils.DEFAULT_CONFIG.copy()
    with patch("sourcecombine.collect_file_paths", side_effect=OSError("Access denied")):
        backed_up, errors = create_backups_for_targets([str(tmp_path)], config)
        assert backed_up == 0
        assert errors == 0

def test_manual_backup_file_missing_at_copy_time(tmp_path):
    file1 = tmp_path / "file1.txt"
    file1.write_text("Hello")

    config = utils.DEFAULT_CONFIG.copy()

    original_exists = Path.exists
    def custom_exists(self):
        if self.name == "file1.txt":
            return False
        return original_exists(self)

    with patch("pathlib.Path.exists", custom_exists):
        backed_up, errors = create_backups_for_targets([str(tmp_path)], config)
        assert backed_up == 0
        assert errors == 1

def test_manual_backup_with_ignore_file(tmp_path):
    ignore_file = tmp_path / ".sourcecombineignore"
    ignore_file.write_text("*.log\n")

    file1 = tmp_path / "file1.log"
    file1.write_text("Log")

    config = utils.DEFAULT_CONFIG.copy()
    config["search"] = config.get("search", {}).copy()
    config["search"]["ignore_files"] = [str(ignore_file)]

    backed_up, errors = create_backups_for_targets([str(tmp_path)], config)
    assert backed_up == 0
    assert errors == 0
