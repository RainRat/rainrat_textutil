import json
import sys
from unittest.mock import patch, MagicMock
import pytest
from sourcecombine import main, restore_backups, delete_backups


@pytest.fixture(autouse=True)
def ensure_pyperclip_spec():
    """Ensure pyperclip has a __spec__ if stubbed."""
    import pyperclip
    if not hasattr(pyperclip, '__spec__'):
        pyperclip.__spec__ = MagicMock(name='pyperclip_spec')
    yield


def test_restore_backups_json_dry_run(tmp_path, capsys):
    f1 = tmp_path / "test.txt"
    f1.write_text("modified content")
    b1 = tmp_path / "test.txt.bak"
    b1.write_text("original content")

    restored_count, error_count = restore_backups([str(tmp_path)], dry_run=True, json_format=True)
    assert restored_count == 1
    assert error_count == 0

    captured = capsys.readouterr()
    data = json.loads(captured.out)

    assert data["title"] == "Restore Backups Report"
    assert data["dry_run"] is True
    assert data["summary"]["restored_count"] == 1
    assert data["summary"]["error_count"] == 0
    assert len(data["restored"]) == 1
    assert data["restored"][0]["status"] == "WOULD_RESTORE"
    assert data["restored"][0]["path"] == "test.txt"
    assert b1.exists()


def test_restore_backups_json_actual(tmp_path, capsys):
    f1 = tmp_path / "test.txt"
    f1.write_text("modified content")
    b1 = tmp_path / "test.txt.bak"
    b1.write_text("original content")

    restored_count, error_count = restore_backups([str(tmp_path)], dry_run=False, json_format=True)
    assert restored_count == 1
    assert error_count == 0

    captured = capsys.readouterr()
    data = json.loads(captured.out)

    assert data["title"] == "Restore Backups Report"
    assert data["dry_run"] is False
    assert data["summary"]["restored_count"] == 1
    assert len(data["restored"]) == 1
    assert data["restored"][0]["status"] == "RESTORED"
    assert f1.read_text() == "original content"
    assert not b1.exists()


def test_delete_backups_json_dry_run(tmp_path, capsys):
    b1 = tmp_path / "test.txt.bak"
    b1.write_text("backup content")

    deleted_count, error_count = delete_backups([str(tmp_path)], dry_run=True, json_format=True)
    assert deleted_count == 1
    assert error_count == 0

    captured = capsys.readouterr()
    data = json.loads(captured.out)

    assert data["title"] == "Delete Backups Report"
    assert data["dry_run"] is True
    assert data["summary"]["deleted_count"] == 1
    assert len(data["deleted"]) == 1
    assert data["deleted"][0]["status"] == "WOULD_DELETE"
    assert b1.exists()


def test_delete_backups_json_actual(tmp_path, capsys):
    b1 = tmp_path / "test.txt.bak"
    b1.write_text("backup content")

    deleted_count, error_count = delete_backups([str(tmp_path)], dry_run=False, json_format=True)
    assert deleted_count == 1
    assert error_count == 0

    captured = capsys.readouterr()
    data = json.loads(captured.out)

    assert data["title"] == "Delete Backups Report"
    assert data["dry_run"] is False
    assert data["summary"]["deleted_count"] == 1
    assert len(data["deleted"]) == 1
    assert data["deleted"][0]["status"] == "DELETED"
    assert not b1.exists()


def test_restore_and_delete_json_empty_and_missing(tmp_path, capsys):
    # Non-existent target
    missing = tmp_path / "non_existent"
    restore_backups([str(missing)], json_format=True)
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["summary"]["restored_count"] == 0

    delete_backups([str(missing)], json_format=True)
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["summary"]["deleted_count"] == 0

    # Empty target folder
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    restore_backups([str(empty_dir)], json_format=True)
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["summary"]["restored_count"] == 0


def test_cli_restore_and_clean_json(tmp_path, capsys):
    f1 = tmp_path / "demo.txt"
    f1.write_text("new")
    b1 = tmp_path / "demo.txt.bak"
    b1.write_text("old")

    # CLI restore json
    with patch.object(sys, 'argv', ["sourcecombine.py", "--restore", "--json", str(tmp_path)]):
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["summary"]["restored_count"] == 1
    assert f1.read_text() == "old"

    # Create backup again and test CLI clean json
    b2 = tmp_path / "demo.txt.bak"
    b2.write_text("backup")
    with patch.object(sys, 'argv', ["sourcecombine.py", "--clean", "--json", str(tmp_path)]):
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["summary"]["deleted_count"] == 1
    assert not b2.exists()


def test_restore_delete_oserror_json(tmp_path, capsys):
    b1 = tmp_path / "file.txt.bak"
    b1.write_text("backup")

    with patch("shutil.move", side_effect=OSError("Permission denied")):
        restored_count, error_count = restore_backups([str(tmp_path)], json_format=True)
        assert restored_count == 0
        assert error_count == 1
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["summary"]["error_count"] == 1
        assert data["restored"][0]["status"] == "ERROR"
        assert "Permission denied" in data["restored"][0]["error"]

    with patch("os.remove", side_effect=OSError("Access denied")):
        deleted_count, error_count = delete_backups([str(tmp_path)], json_format=True)
        assert deleted_count == 0
        assert error_count == 1
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["summary"]["error_count"] == 1
        assert data["deleted"][0]["status"] == "ERROR"
        assert "Access denied" in data["deleted"][0]["error"]
