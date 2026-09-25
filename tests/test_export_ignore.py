import json
import logging
import os
import sys
from pathlib import Path
import pytest

import sourcecombine
import utils


def test_export_ignore_patterns_default_file(tmp_path, monkeypatch, caplog):
    monkeypatch.chdir(tmp_path)
    config = copy_config()
    config['filters']['exclusions'] = {
        'filenames': ['*.tmp', '*.log'],
        'folders': ['build', 'dist'],
        'extensions': ['.bak']
    }

    with caplog.at_level(logging.INFO):
        sourcecombine.export_ignore_patterns(".sourcecombineignore", config=config)

    exported_file = tmp_path / ".sourcecombineignore"
    assert exported_file.is_file()
    content = exported_file.read_text(encoding="utf-8")
    assert "# SourceCombine Exported Ignore Patterns" in content
    assert "*.tmp" in content
    assert "*.log" in content
    assert "build" in content
    assert ".bak" in content


def test_export_ignore_patterns_custom_file(tmp_path, caplog):
    target = tmp_path / "custom.ignore"
    config = copy_config()
    config['filters']['exclusions'] = {
        'filenames': ['secret.txt'],
        'folders': ['private'],
    }

    with caplog.at_level(logging.INFO):
        sourcecombine.export_ignore_patterns(target, config=config)

    assert target.is_file()
    content = target.read_text(encoding="utf-8")
    assert "secret.txt" in content
    assert "private" in content


def test_export_ignore_patterns_directory_target(tmp_path):
    target_dir = tmp_path / "subdir"
    target_dir.mkdir()
    config = copy_config()
    config['filters']['exclusions'] = {'filenames': ['temp.dat']}

    sourcecombine.export_ignore_patterns(target_dir, config=config)

    expected_file = target_dir / ".sourcecombineignore"
    assert expected_file.is_file()
    assert "temp.dat" in expected_file.read_text(encoding="utf-8")


def test_export_ignore_patterns_stdout(capsys):
    config = copy_config()
    config['filters']['exclusions'] = {'filenames': ['stdout_match.txt']}

    sourcecombine.export_ignore_patterns("-", config=config)

    captured = capsys.readouterr()
    assert "# SourceCombine Exported Ignore Patterns" in captured.out
    assert "stdout_match.txt" in captured.out


def test_export_ignore_patterns_json_file(tmp_path):
    target = tmp_path / "ignore.json"
    config = copy_config()
    config['filters']['exclusions'] = {
        'filenames': ['*.cache'],
        'folders': ['.git']
    }

    sourcecombine.export_ignore_patterns(target, config=config, json_format=True)

    assert target.is_file()
    data = json.loads(target.read_text(encoding="utf-8"))
    assert "total_patterns" in data
    assert "*.cache" in data["patterns"]
    assert ".git" in data["patterns"]


def test_export_ignore_patterns_json_stdout(capsys):
    config = copy_config()
    config['filters']['exclusions'] = {
        'filenames': ['*.cache'],
    }

    sourcecombine.export_ignore_patterns("-", config=config, json_format=True)

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["exported_to"] == "-"
    assert "*.cache" in data["patterns"]


def test_export_ignore_patterns_write_error(tmp_path, monkeypatch):
    invalid_target = tmp_path / "nonexistent_dir_file" / "out.ignore"

    def mock_mkdir(*args, **kwargs):
        raise OSError("Permission denied")

    monkeypatch.setattr(Path, "mkdir", mock_mkdir)

    config = copy_config()

    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.export_ignore_patterns(invalid_target, config=config)
    assert exc_info.value.code == 1


def test_cli_export_ignore_default(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["sourcecombine", "--export-ignore"])

    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.main()

    assert exc_info.value.code == 0
    exported_file = tmp_path / ".sourcecombineignore"
    assert exported_file.is_file()


def test_cli_export_ignore_alias_custom_target(tmp_path, monkeypatch):
    target = tmp_path / "cli_exported.ignore"
    monkeypatch.setattr(sys, "argv", ["sourcecombine", "--export-ig", str(target)])

    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.main()

    assert exc_info.value.code == 0
    assert target.is_file()


def test_cli_export_ignore_stdout_json(capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["sourcecombine", "--export-ignore", "-", "--json"])

    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.main()

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["exported_to"] == "-"
    assert "patterns" in data


def test_cli_export_ignore_and_files_from_conflict(monkeypatch, caplog):
    monkeypatch.setattr(sys, "argv", ["sourcecombine", "--export-ignore", "--files-from", "list.txt"])

    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.main()

    assert exc_info.value.code == 1
    assert "cannot use --export-ignore and --files-from at the same time" in caplog.text


def test_export_ignore_patterns_default_config_fallback(capsys):
    sourcecombine.export_ignore_patterns("-", config=None)
    captured = capsys.readouterr()
    assert "# SourceCombine Exported Ignore Patterns" in captured.out


def test_export_ignore_patterns_autodetect_default_ignore_file(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    ignore_file = tmp_path / ".sourcecombineignore"
    ignore_file.write_text("*.tmp_auto\n", encoding="utf-8")

    config = copy_config()
    config['search']['ignore_files'] = []

    sourcecombine.export_ignore_patterns("-", config=config)
    captured = capsys.readouterr()
    assert "*.tmp_auto" in captured.out


def test_export_ignore_patterns_with_loaded_ignore_files(tmp_path, capsys):
    custom_ignore = tmp_path / "custom_rules.txt"
    custom_ignore.write_text("*.custom_ignore\nbuild_out/\n", encoding="utf-8")

    config = copy_config()
    config['search']['ignore_files'] = [str(custom_ignore)]

    sourcecombine.export_ignore_patterns("-", config=config)
    captured = capsys.readouterr()
    assert "*.custom_ignore" in captured.out
    assert "build_out/" in captured.out


def test_export_ignore_patterns_json_write_error(tmp_path, monkeypatch, caplog):
    target = tmp_path / "subdir" / "out.json"

    def mock_mkdir(*args, **kwargs):
        raise OSError("Directory creation failed")

    monkeypatch.setattr(Path, "mkdir", mock_mkdir)

    config = copy_config()

    with caplog.at_level(logging.ERROR):
        with pytest.raises(SystemExit) as exc_info:
            sourcecombine.export_ignore_patterns(target, config=config, json_format=True)

    assert exc_info.value.code == 1
    assert "Could not export ignore patterns to" in caplog.text


def copy_config():
    import copy
    cfg = copy.deepcopy(utils.DEFAULT_CONFIG)
    utils.validate_config(cfg)
    return cfg
