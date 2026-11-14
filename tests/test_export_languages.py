import json
from pathlib import Path
from unittest.mock import patch
import pytest

import sourcecombine


def test_export_languages_stdout(capsys):
    sourcecombine.export_languages("-")
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["exported_to"] == "-"
    assert data["total_languages"] > 0
    assert "python" in data["languages"]
    assert ".py" in data["languages"]["python"]


def test_export_languages_default_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    sourcecombine.export_languages(None)
    target_file = tmp_path / "languages.json"
    assert target_file.is_file()
    with open(target_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["exported_to"] == str(target_file.resolve())
    assert data["total_languages"] > 0
    assert "python" in data["languages"]


def test_export_languages_custom_file(tmp_path):
    target_file = tmp_path / "custom_langs.json"
    sourcecombine.export_languages(target_file)
    assert target_file.is_file()
    with open(target_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["exported_to"] == str(target_file.resolve())
    assert data["total_languages"] > 0
    assert "rust" in data["languages"]
    assert ".rs" in data["languages"]["rust"]


def test_export_languages_directory(tmp_path):
    target_dir = tmp_path / "langs_dir"
    target_dir.mkdir()
    sourcecombine.export_languages(target_dir)
    expected_file = target_dir / "languages.json"
    assert expected_file.is_file()
    with open(expected_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["exported_to"] == str(expected_file.resolve())
    assert "javascript" in data["languages"]


def test_export_languages_with_query():
    # Filter by language tag
    import io
    with patch("sys.stdout", new_callable=io.StringIO) as fake_stdout:
        sourcecombine.export_languages("-", query="python")
        data = json.loads(fake_stdout.getvalue())
        assert "python" in data["languages"]
        assert "rust" not in data["languages"]

    # Filter by extension
    with patch("sys.stdout", new_callable=io.StringIO) as fake_stdout:
        sourcecombine.export_languages("-", query=".rs")
        data = json.loads(fake_stdout.getvalue())
        assert "rust" in data["languages"]
        assert "python" not in data["languages"]


def test_export_languages_oserror_handling(tmp_path):
    invalid_path = tmp_path / "non_existent" / "languages.json"
    with patch("builtins.open", side_effect=OSError("Permission denied")):
        with pytest.raises(SystemExit) as exc_info:
            sourcecombine.export_languages(str(invalid_path))
        assert exc_info.value.code == 1


def test_main_cli_export_languages_default(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    test_args = ["sourcecombine.py", "--export-languages"]
    with patch("sys.argv", test_args):
        with pytest.raises(SystemExit) as exc_info:
            sourcecombine.main()
        assert exc_info.value.code == 0
    target_file = tmp_path / "languages.json"
    assert target_file.is_file()


def test_main_cli_export_languages_alias_and_custom_path(tmp_path):
    target_file = tmp_path / "exported.json"
    test_args = ["sourcecombine.py", "--export-langs", str(target_file)]
    with patch("sys.argv", test_args):
        with pytest.raises(SystemExit) as exc_info:
            sourcecombine.main()
        assert exc_info.value.code == 0
    assert target_file.is_file()


def test_main_cli_export_languages_conflict_with_files_from():
    test_args = ["sourcecombine.py", "--export-languages", "--files-from", "file_list.txt"]
    with patch("sys.argv", test_args):
        with pytest.raises(SystemExit) as exc_info:
            sourcecombine.main()
        assert exc_info.value.code == 1
