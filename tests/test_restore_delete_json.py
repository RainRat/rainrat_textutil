import json
from pathlib import Path
import pytest
from unittest.mock import patch
import sourcecombine


def test_restore_backups_json_format_real(tmp_path, capsys):
    """Test restore_backups with json_format=True when performing actual restore."""
    orig_file = tmp_path / "app.py"
    bak_file = tmp_path / "app.py.bak"

    orig_file.write_text("modified content", encoding="utf-8")
    bak_file.write_text("original content", encoding="utf-8")

    restored_count, error_count = sourcecombine.restore_backups([str(tmp_path)], dry_run=False, json_format=True)

    assert restored_count == 1
    assert error_count == 0
    assert orig_file.read_text(encoding="utf-8") == "original content"
    assert not bak_file.exists()

    captured = capsys.readouterr()
    data = json.loads(captured.out)

    assert data["title"] == "Backup Restore Report"
    assert data["dry_run"] is False
    assert len(data["restored_files"]) == 1
    assert data["restored_files"][0]["path"] == "app.py"
    assert data["restored_files"][0]["status"] == "RESTORED"
    assert data["summary"] == {"restored": 1, "errors": 0, "total": 1}


def test_restore_backups_json_format_dry_run(tmp_path, capsys):
    """Test restore_backups with json_format=True in dry_run mode."""
    orig_file = tmp_path / "app.py"
    bak_file = tmp_path / "app.py.bak"

    orig_file.write_text("modified content", encoding="utf-8")
    bak_file.write_text("original content", encoding="utf-8")

    restored_count, error_count = sourcecombine.restore_backups([str(tmp_path)], dry_run=True, json_format=True)

    assert restored_count == 1
    assert error_count == 0
    assert orig_file.read_text(encoding="utf-8") == "modified content"
    assert bak_file.exists()

    captured = capsys.readouterr()
    data = json.loads(captured.out)

    assert data["title"] == "Backup Restore Report"
    assert data["dry_run"] is True
    assert len(data["restored_files"]) == 1
    assert data["restored_files"][0]["path"] == "app.py"
    assert data["restored_files"][0]["status"] == "WOULD_RESTORE"
    assert data["summary"] == {"restored": 1, "errors": 0, "total": 1}


def test_restore_backups_json_format_empty(tmp_path, capsys):
    """Test restore_backups with json_format=True when no backups exist."""
    restored_count, error_count = sourcecombine.restore_backups([str(tmp_path)], dry_run=False, json_format=True)

    assert restored_count == 0
    assert error_count == 0

    captured = capsys.readouterr()
    data = json.loads(captured.out)

    assert data["title"] == "Backup Restore Report"
    assert data["restored_files"] == []
    assert data["summary"] == {"restored": 0, "errors": 0, "total": 0}


def test_delete_backups_json_format_real(tmp_path, capsys):
    """Test delete_backups with json_format=True when performing actual deletion."""
    bak_file = tmp_path / "app.py.bak"
    bak_file.write_text("backup content", encoding="utf-8")

    deleted_count, error_count = sourcecombine.delete_backups([str(tmp_path)], dry_run=False, json_format=True)

    assert deleted_count == 1
    assert error_count == 0
    assert not bak_file.exists()

    captured = capsys.readouterr()
    data = json.loads(captured.out)

    assert data["title"] == "Backup Delete Report"
    assert data["dry_run"] is False
    assert len(data["deleted_files"]) == 1
    assert data["deleted_files"][0]["path"] == "app.py.bak"
    assert data["deleted_files"][0]["status"] == "DELETED"
    assert data["summary"] == {"deleted": 1, "errors": 0, "total": 1}


def test_delete_backups_json_format_dry_run(tmp_path, capsys):
    """Test delete_backups with json_format=True in dry_run mode."""
    bak_file = tmp_path / "app.py.bak"
    bak_file.write_text("backup content", encoding="utf-8")

    deleted_count, error_count = sourcecombine.delete_backups([str(tmp_path)], dry_run=True, json_format=True)

    assert deleted_count == 1
    assert error_count == 0
    assert bak_file.exists()

    captured = capsys.readouterr()
    data = json.loads(captured.out)

    assert data["title"] == "Backup Delete Report"
    assert data["dry_run"] is True
    assert len(data["deleted_files"]) == 1
    assert data["deleted_files"][0]["path"] == "app.py.bak"
    assert data["deleted_files"][0]["status"] == "WOULD_DELETE"
    assert data["summary"] == {"deleted": 1, "errors": 0, "total": 1}


def test_delete_backups_json_format_empty(tmp_path, capsys):
    """Test delete_backups with json_format=True when no backups exist."""
    deleted_count, error_count = sourcecombine.delete_backups([str(tmp_path)], dry_run=False, json_format=True)

    assert deleted_count == 0
    assert error_count == 0

    captured = capsys.readouterr()
    data = json.loads(captured.out)

    assert data["title"] == "Backup Delete Report"
    assert data["deleted_files"] == []
    assert data["summary"] == {"deleted": 0, "errors": 0, "total": 0}


def test_cli_restore_json(tmp_path, monkeypatch, capsys):
    """Test CLI invocation of sourcecombine --restore --json."""
    monkeypatch.chdir(tmp_path)
    orig_file = tmp_path / "test.txt"
    bak_file = tmp_path / "test.txt.bak"

    orig_file.write_text("new content", encoding="utf-8")
    bak_file.write_text("old content", encoding="utf-8")

    test_args = ["sourcecombine.py", ".", "--restore", "--json"]
    with patch("sys.argv", test_args):
        with pytest.raises(SystemExit) as exc:
            sourcecombine.main()
        assert exc.value.code == 0

    captured = capsys.readouterr()
    data = json.loads(captured.out)

    assert data["title"] == "Backup Restore Report"
    assert len(data["restored_files"]) == 1
    assert orig_file.read_text(encoding="utf-8") == "old content"


def test_cli_clean_json(tmp_path, monkeypatch, capsys):
    """Test CLI invocation of sourcecombine --clean --json."""
    monkeypatch.chdir(tmp_path)
    bak_file = tmp_path / "test.txt.bak"
    bak_file.write_text("old content", encoding="utf-8")

    test_args = ["sourcecombine.py", ".", "--clean", "--json"]
    with patch("sys.argv", test_args):
        with pytest.raises(SystemExit) as exc:
            sourcecombine.main()
        assert exc.value.code == 0

    captured = capsys.readouterr()
    data = json.loads(captured.out)

    assert data["title"] == "Backup Delete Report"
    assert len(data["deleted_files"]) == 1
    assert not bak_file.exists()
