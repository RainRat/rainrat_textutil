import sys; import os; from pathlib import Path; sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

import json
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock
import sourcecombine

def test_list_backups_no_backups(tmp_path):
    # No backup files found
    res = sourcecombine.list_backups([tmp_path], json_format=False)
    assert res == []

def test_list_backups_scenarios(tmp_path):
    # Create matching, modified, and orphaned backup files
    sub_dir = tmp_path / "src"
    sub_dir.mkdir()

    # 1. Matching
    file_match = sub_dir / "match.py"
    file_match.write_text("print('hello')")
    file_match_bak = sub_dir / "match.py.bak"
    file_match_bak.write_text("print('hello')")

    # 2. Modified
    file_mod = sub_dir / "mod.py"
    file_mod.write_text("print('hello modified')")
    file_mod_bak = sub_dir / "mod.py.bak"
    file_mod_bak.write_text("print('hello')")

    # 3. Orphaned
    file_orphan_bak = sub_dir / "orphan.py.bak"
    file_orphan_bak.write_text("print('orphan')")

    res = sourcecombine.list_backups([tmp_path], json_format=False)

    # Assert return values
    assert len(res) == 3

    status_map = {item["original_path"]: item["status"] for item in res}
    assert status_map["src/match.py"] == "MATCHING"
    assert status_map["src/mod.py"] == "MODIFIED"
    assert status_map["src/orphan.py"] == "ORPHANED"

def test_list_backups_single_file_target(tmp_path):
    sub_dir = tmp_path / "src"
    sub_dir.mkdir()

    file_match = sub_dir / "match.py"
    file_match.write_text("print('hello')")
    file_match_bak = sub_dir / "match.py.bak"
    file_match_bak.write_text("print('hello')")

    # Single backup file as target
    res1 = sourcecombine.list_backups([file_match_bak], json_format=False)
    assert len(res1) == 1
    assert res1[0]["status"] == "MATCHING"

    # Single original file with backup as target
    res2 = sourcecombine.list_backups([file_match], json_format=False)
    assert len(res2) == 1
    assert res2[0]["status"] == "MATCHING"

def test_list_backups_json_format(tmp_path, capsys):
    sub_dir = tmp_path / "src"
    sub_dir.mkdir()

    file_match = sub_dir / "match.py"
    file_match.write_text("print('hello')")
    file_match_bak = sub_dir / "match.py.bak"
    file_match_bak.write_text("print('hello')")

    # Print to console as JSON
    res = sourcecombine.list_backups([tmp_path], json_format=True)
    captured = capsys.readouterr()
    data = json.loads(captured.out)

    assert "backups" in data
    assert len(data["backups"]) == 1
    assert data["backups"][0]["status"] == "MATCHING"
    assert data["backups"][0]["original_path"] == "src/match.py"

def test_list_backups_not_found_target(capsys):
    res = sourcecombine.list_backups(["non_existent_folder_abc_123"], json_format=False)
    assert res == []

def test_list_backups_error_status(tmp_path):
    sub_dir = tmp_path / "src"
    sub_dir.mkdir()

    file_match = sub_dir / "match.py"
    file_match.write_text("print('hello')")
    file_match_bak = sub_dir / "match.py.bak"
    file_match_bak.write_text("print('hello')")

    # Mock open to raise an exception on reading to simulate an error status
    with patch("builtins.open", side_effect=OSError("Permission denied")):
        res = sourcecombine.list_backups([tmp_path], json_format=False)
        assert len(res) == 1
        assert res[0]["status"] == "ERROR"

def test_list_backups_cli_integration(tmp_path):
    # Test CLI execution flow through main
    sub_dir = tmp_path / "src"
    sub_dir.mkdir()

    file_match = sub_dir / "match.py"
    file_match.write_text("print('hello')")
    file_match_bak = sub_dir / "match.py.bak"
    file_match_bak.write_text("print('hello')")

    # We patch sys.argv and mock sys.exit to verify main works with list_backups
    test_args = [
        "sourcecombine.py",
        "--list-backups",
        str(tmp_path)
    ]
    with patch("sys.argv", test_args), pytest.raises(SystemExit) as excinfo:
        sourcecombine.main()
    assert excinfo.value.code == 0
