import copy
import json
import logging
import sys
from pathlib import Path
import pytest

import sourcecombine
import utils


def copy_config():
    cfg = copy.deepcopy(utils.DEFAULT_CONFIG)
    utils.validate_config(cfg)
    return cfg


def test_export_file_list_none_config(tmp_path):
    target = tmp_path / "file_list_none_cfg.txt"
    files = ["src/main.py", "src/utils.py"]
    sourcecombine.export_file_list(target, files=files, config=None)
    assert target.is_file()
    lines = target.read_text(encoding="utf-8").splitlines()
    assert lines == ["src/main.py", "src/utils.py"]


def test_export_file_list_default_file(tmp_path, monkeypatch, caplog):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "app.py").write_text("print('hello')", encoding="utf-8")
    config = copy_config()

    with caplog.at_level(logging.INFO):
        sourcecombine.export_file_list("file_list.txt", config=config)

    exported_file = tmp_path / "file_list.txt"
    assert exported_file.is_file()
    content = exported_file.read_text(encoding="utf-8")
    assert "app.py" in content


def test_export_file_list_custom_file(tmp_path, caplog):
    target = tmp_path / "custom_files.txt"
    files = ["a.py", "b.py"]

    with caplog.at_level(logging.INFO):
        sourcecombine.export_file_list(target, files=files)

    assert target.is_file()
    lines = target.read_text(encoding="utf-8").splitlines()
    assert lines == ["a.py", "b.py"]


def test_export_file_list_directory_target(tmp_path):
    target_dir = tmp_path / "export_dir"
    target_dir.mkdir()
    files = ["lib/core.py"]

    sourcecombine.export_file_list(target_dir, files=files)

    expected_file = target_dir / "file_list.txt"
    assert expected_file.is_file()
    assert expected_file.read_text(encoding="utf-8").strip() == "lib/core.py"


def test_export_file_list_json_format(tmp_path):
    target = tmp_path / "files.json"
    files = [{"path": "module1.py"}, ("module2.py", "root"), "module3.py"]

    sourcecombine.export_file_list(target, files=files, json_format=True)

    assert target.is_file()
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["total_files"] == 3
    assert data["files"] == ["module1.py", "module2.py", "module3.py"]


def test_export_file_list_stdout(capsys):
    files = ["index.js", "style.css"]

    sourcecombine.export_file_list("-", files=files)
    captured = capsys.readouterr()
    assert captured.out == "index.js\nstyle.css\n"

    sourcecombine.export_file_list("-", files=files, json_format=True)
    captured_json = capsys.readouterr()
    data = json.loads(captured_json.out)
    assert data["exported_to"] == "-"
    assert data["total_files"] == 2
    assert data["files"] == ["index.js", "style.css"]


def test_export_file_list_write_error(tmp_path, monkeypatch):
    invalid_target = tmp_path / "nonexistent_dir" / "out.txt"

    def mock_mkdir(*args, **kwargs):
        raise OSError("Permission denied")

    monkeypatch.setattr(Path, "mkdir", mock_mkdir)

    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.export_file_list(invalid_target, files=["test.py"])
    assert exc_info.value.code == 1


def test_cli_export_file_list_default(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "test1.py").write_text("x = 1", encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        ["sourcecombine", "--export-file-list"]
    )

    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.main()

    assert exc_info.value.code == 0
    exported_file = tmp_path / "file_list.txt"
    assert exported_file.is_file()
    assert "test1.py" in exported_file.read_text(encoding="utf-8")


def test_cli_export_file_list_aliases(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "demo.py").write_text("y = 2", encoding="utf-8")

    target1 = tmp_path / "files_alias.txt"
    monkeypatch.setattr(
        sys,
        "argv",
        ["sourcecombine", "--export-files", str(target1)]
    )

    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.main()

    assert exc_info.value.code == 0
    assert target1.is_file()

    target2 = tmp_path / "file_map_alias.json"
    monkeypatch.setattr(
        sys,
        "argv",
        ["sourcecombine", "--export-file-map", str(target2), "--json"]
    )

    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.main()

    assert exc_info.value.code == 0
    assert target2.is_file()
    data = json.loads(target2.read_text(encoding="utf-8"))
    assert "demo.py" in data["files"]


def test_cli_export_file_list_and_files_from_conflict(monkeypatch, caplog):
    monkeypatch.setattr(
        sys,
        "argv",
        ["sourcecombine", "--export-file-list", "--files-from", "list.txt"]
    )

    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.main()

    assert exc_info.value.code == 1
    assert "cannot use --export-file-list and --files-from at the same time" in caplog.text
