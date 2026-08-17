import json
from unittest.mock import patch
import pytest
from sourcecombine import restore_backups, delete_backups


def test_restore_backups_json_format_dry_run(tmp_path, capsys):
    bak_file = tmp_path / "test.txt.bak"
    bak_file.write_text("backup content", encoding="utf-8")

    restored, errors = restore_backups([str(tmp_path)], dry_run=True, json_format=True)
    assert restored == 1
    assert errors == 0

    captured = capsys.readouterr()
    data = json.loads(captured.out)

    assert data["title"] == "Restore Backups Report"
    assert data["dry_run"] is True
    assert data["summary"]["restored"] == 1
    assert data["summary"]["errors"] == 0
    assert len(data["files"]) == 1
    assert data["files"][0]["status"] == "would_restore"
    assert data["files"][0]["target_path"] == "test.txt"


def test_restore_backups_json_format_execution(tmp_path, capsys):
    orig_file = tmp_path / "test.txt"
    bak_file = tmp_path / "test.txt.bak"
    orig_file.write_text("modified content", encoding="utf-8")
    bak_file.write_text("original content", encoding="utf-8")

    restored, errors = restore_backups([str(tmp_path)], dry_run=False, json_format=True)
    assert restored == 1
    assert errors == 0
    assert orig_file.read_text(encoding="utf-8") == "original content"
    assert not bak_file.exists()

    captured = capsys.readouterr()
    data = json.loads(captured.out)

    assert data["summary"]["restored"] == 1
    assert data["files"][0]["status"] == "restored"


def test_restore_backups_json_format_error(tmp_path, capsys):
    bak_file = tmp_path / "test.txt.bak"
    bak_file.write_text("backup content", encoding="utf-8")

    with patch("shutil.move", side_effect=OSError("Permission denied")):
        restored, errors = restore_backups([str(tmp_path)], dry_run=False, json_format=True)

    assert restored == 0
    assert errors == 1

    captured = capsys.readouterr()
    data = json.loads(captured.out)

    assert data["summary"]["errors"] == 1
    assert data["files"][0]["status"] == "error"
    assert "Permission denied" in data["files"][0]["error"]


def test_delete_backups_json_format_dry_run(tmp_path, capsys):
    bak_file = tmp_path / "test.txt.bak"
    bak_file.write_text("backup content", encoding="utf-8")

    deleted, errors = delete_backups([str(tmp_path)], dry_run=True, json_format=True)
    assert deleted == 1
    assert errors == 0
    assert bak_file.exists()

    captured = capsys.readouterr()
    data = json.loads(captured.out)

    assert data["title"] == "Delete Backups Report"
    assert data["dry_run"] is True
    assert data["summary"]["deleted"] == 1
    assert data["files"][0]["status"] == "would_delete"


def test_delete_backups_json_format_execution(tmp_path, capsys):
    bak_file = tmp_path / "test.txt.bak"
    bak_file.write_text("backup content", encoding="utf-8")

    deleted, errors = delete_backups([str(tmp_path)], dry_run=False, json_format=True)
    assert deleted == 1
    assert errors == 0
    assert not bak_file.exists()

    captured = capsys.readouterr()
    data = json.loads(captured.out)

    assert data["summary"]["deleted"] == 1
    assert data["files"][0]["status"] == "deleted"


def test_delete_backups_json_format_error(tmp_path, capsys):
    bak_file = tmp_path / "test.txt.bak"
    bak_file.write_text("backup content", encoding="utf-8")

    with patch("os.remove", side_effect=OSError("Access denied")):
        deleted, errors = delete_backups([str(tmp_path)], dry_run=False, json_format=True)

    assert deleted == 0
    assert errors == 1

    captured = capsys.readouterr()
    data = json.loads(captured.out)

    assert data["summary"]["errors"] == 1
    assert data["files"][0]["status"] == "error"
    assert "Access denied" in data["files"][0]["error"]
