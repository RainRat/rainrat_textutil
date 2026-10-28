import json
import logging
import sys
from pathlib import Path
import pytest

import sourcecombine


def test_export_extensions_default_file(tmp_path, monkeypatch, caplog):
    monkeypatch.chdir(tmp_path)

    with caplog.at_level(logging.INFO):
        sourcecombine.export_extensions("extensions.json")

    exported_file = tmp_path / "extensions.json"
    assert exported_file.is_file()
    data = json.loads(exported_file.read_text(encoding="utf-8"))
    assert "total_extensions" in data
    assert "extensions" in data
    assert data["total_extensions"] == len(data["extensions"])
    assert ".py" in data["extensions"]
    assert data["extensions"][".py"] == "python"


def test_export_extensions_custom_file(tmp_path, caplog):
    target = tmp_path / "custom_ext.json"

    with caplog.at_level(logging.INFO):
        sourcecombine.export_extensions(target)

    assert target.is_file()
    data = json.loads(target.read_text(encoding="utf-8"))
    assert "total_extensions" in data
    assert ".rs" in data["extensions"]


def test_export_extensions_directory_target(tmp_path):
    target_dir = tmp_path / "ext_dir"
    target_dir.mkdir()

    sourcecombine.export_extensions(target_dir)

    expected_file = target_dir / "extensions.json"
    assert expected_file.is_file()
    data = json.loads(expected_file.read_text(encoding="utf-8"))
    assert "total_extensions" in data


def test_export_extensions_stdout(capsys):
    sourcecombine.export_extensions("-")

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["exported_to"] == "-"
    assert "total_extensions" in data
    assert ".js" in data["extensions"]


def test_export_extensions_write_error(tmp_path, monkeypatch):
    invalid_target = tmp_path / "nonexistent_dir" / "out.json"

    def mock_mkdir(*args, **kwargs):
        raise OSError("Permission denied")

    monkeypatch.setattr(Path, "mkdir", mock_mkdir)

    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.export_extensions(invalid_target)
    assert exc_info.value.code == 1


def test_cli_export_extensions_default(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        ["sourcecombine", "--export-extensions"]
    )

    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.main()

    assert exc_info.value.code == 0
    exported_file = tmp_path / "extensions.json"
    assert exported_file.is_file()
    data = json.loads(exported_file.read_text(encoding="utf-8"))
    assert "total_extensions" in data


def test_cli_export_extensions_alias(tmp_path, monkeypatch):
    target = tmp_path / "alias_ext.json"
    monkeypatch.setattr(
        sys,
        "argv",
        ["sourcecombine", "--export-ext", str(target)]
    )

    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.main()

    assert exc_info.value.code == 0
    assert target.is_file()
    data = json.loads(target.read_text(encoding="utf-8"))
    assert "extensions" in data


def test_cli_export_extensions_and_files_from_conflict(monkeypatch, caplog):
    monkeypatch.setattr(
        sys,
        "argv",
        ["sourcecombine", "--export-extensions", "--files-from", "list.txt"]
    )

    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.main()

    assert exc_info.value.code == 1
    assert "cannot use --export-extensions and --files-from at the same time" in caplog.text
