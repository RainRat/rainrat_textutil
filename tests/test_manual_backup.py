import sys; import os; from pathlib import Path; sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

import os
import sys
import logging
import json
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock

from sourcecombine import create_backups_for_targets, main
import utils

def test_create_backups_for_targets_standard(tmp_path):
    """Test standard manual backup creation of matched files."""
    sub = tmp_path / "subdir"
    sub.mkdir()

    file1 = tmp_path / "file1.txt"
    file2 = sub / "file2.py"
    file3 = tmp_path / "file3.log" # Let's exclude this via config later

    file1.write_text("content 1", encoding="utf-8")
    file2.write_text("content 2", encoding="utf-8")
    file3.write_text("content 3", encoding="utf-8")

    config = {
        "search": {
            "root_folders": [str(tmp_path)],
            "recursive": True,
        },
        "filters": {
            "exclusions": {
                "filenames": ["*.log"]
            }
        }
    }

    backed_up, errors = create_backups_for_targets([str(tmp_path)], config)

    assert backed_up == 2
    assert errors == 0

    bak1 = tmp_path / "file1.txt.bak"
    bak2 = sub / "file2.py.bak"
    bak3 = tmp_path / "file3.log.bak"

    assert bak1.exists()
    assert bak1.read_text(encoding="utf-8") == "content 1"
    assert bak2.exists()
    assert bak2.read_text(encoding="utf-8") == "content 2"
    assert not bak3.exists()


def test_create_backups_for_targets_dry_run(tmp_path):
    """Test manual backup with dry_run enabled."""
    file1 = tmp_path / "file1.txt"
    file1.write_text("content 1", encoding="utf-8")

    config = {
        "search": {
            "root_folders": [str(tmp_path)],
            "recursive": True,
        },
        "filters": {}
    }

    backed_up, errors = create_backups_for_targets([str(tmp_path)], config, dry_run=True)

    assert backed_up == 1
    assert errors == 0

    bak1 = tmp_path / "file1.txt.bak"
    assert not bak1.exists()


def test_create_backups_for_targets_json(tmp_path, capsys):
    """Test manual backup outputting JSON report."""
    file1 = tmp_path / "file1.txt"
    file1.write_text("content 1", encoding="utf-8")

    config = {
        "search": {
            "root_folders": [str(tmp_path)],
            "recursive": True,
        },
        "filters": {}
    }

    backed_up, errors = create_backups_for_targets([str(tmp_path)], config, json_format=True)

    assert backed_up == 1
    assert errors == 0

    captured = capsys.readouterr()
    report = json.loads(captured.out)

    assert "backups" in report
    assert len(report["backups"]) == 1
    assert report["backups"][0]["file"] == "file1.txt"
    assert report["backups"][0]["status"] == "backed_up"
    assert report["summary"]["backed_up"] == 1
    assert report["summary"]["error"] == 0


def test_create_backups_for_targets_error(tmp_path):
    """Test error handling when backup fails (e.g. permission or write error)."""
    file1 = tmp_path / "file1.txt"
    file1.write_text("content 1", encoding="utf-8")

    config = {
        "search": {
            "root_folders": [str(tmp_path)],
            "recursive": True,
        },
        "filters": {}
    }

    with patch("shutil.copy2", side_effect=OSError("Permission denied")):
        backed_up, errors = create_backups_for_targets([str(tmp_path)], config)
        assert backed_up == 0
        assert errors == 1


def test_create_backups_cli_integration(tmp_path):
    """Test integrated --backup command execution via main."""
    file1 = tmp_path / "file1.txt"
    file1.write_text("content 1", encoding="utf-8")

    with patch("sys.argv", ["sourcecombine.py", str(tmp_path), "--backup"]):
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 0

    bak1 = tmp_path / "file1.txt.bak"
    assert bak1.exists()
    assert bak1.read_text(encoding="utf-8") == "content 1"


def test_create_backups_cli_integration_json(tmp_path, capsys):
    """Test integrated --backup command execution with --json."""
    file1 = tmp_path / "file1.txt"
    file1.write_text("content 1", encoding="utf-8")

    with patch("sys.argv", ["sourcecombine.py", str(tmp_path), "--backup", "--json"]):
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 0

    captured = capsys.readouterr()
    report = json.loads(captured.out)
    assert report["summary"]["backed_up"] == 1
