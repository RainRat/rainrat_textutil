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


def test_export_replacements_none_config(tmp_path):
    target = tmp_path / "replacements_none_cfg.json"
    sourcecombine.export_replacements(target, config=None)
    assert target.is_file()
    data = json.loads(target.read_text(encoding="utf-8"))
    assert "total_rules" in data
    assert "regex_replacements" in data
    assert "line_regex_replacements" in data


def test_export_replacements_default_file(tmp_path, monkeypatch, caplog):
    monkeypatch.chdir(tmp_path)
    config = copy_config()
    config['processing']['regex_replacements'] = [
        {'pattern': r'foo', 'replacement': 'bar'}
    ]
    config['processing']['line_regex_replacements'] = [
        {'pattern': r'^DEBUG.*', 'replacement': ''}
    ]

    with caplog.at_level(logging.INFO):
        sourcecombine.export_replacements("replacements.json", config=config)

    exported_file = tmp_path / "replacements.json"
    assert exported_file.is_file()
    data = json.loads(exported_file.read_text(encoding="utf-8"))
    assert data["total_rules"] == 2
    assert data["regex_replacements"] == [{'pattern': r'foo', 'replacement': 'bar'}]
    assert data["line_regex_replacements"] == [{'pattern': r'^DEBUG.*', 'replacement': ''}]


def test_export_replacements_custom_file(tmp_path, caplog):
    target = tmp_path / "custom_rules.json"
    config = copy_config()
    config['processing']['regex_replacements'] = [
        {'pattern': 'secret', 'replacement': 'REDACTED'}
    ]

    with caplog.at_level(logging.INFO):
        sourcecombine.export_replacements(target, config=config)

    assert target.is_file()
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["total_rules"] == 1
    assert data["regex_replacements"][0]["pattern"] == 'secret'


def test_export_replacements_directory_target(tmp_path):
    target_dir = tmp_path / "rules_dir"
    target_dir.mkdir()
    config = copy_config()
    config['processing']['regex_replacements'] = [{'pattern': 'a', 'replacement': 'b'}]

    sourcecombine.export_replacements(target_dir, config=config)

    expected_file = target_dir / "replacements.json"
    assert expected_file.is_file()
    data = json.loads(expected_file.read_text(encoding="utf-8"))
    assert data["total_rules"] == 1


def test_export_replacements_stdout(capsys):
    config = copy_config()
    config['processing']['regex_replacements'] = [{'pattern': 'x', 'replacement': 'y'}]

    sourcecombine.export_replacements("-", config=config)

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["exported_to"] == "-"
    assert data["total_rules"] == 1
    assert data["regex_replacements"] == [{'pattern': 'x', 'replacement': 'y'}]


def test_export_replacements_write_error(tmp_path, monkeypatch):
    invalid_target = tmp_path / "nonexistent_dir" / "out.json"

    def mock_mkdir(*args, **kwargs):
        raise OSError("Permission denied")

    monkeypatch.setattr(Path, "mkdir", mock_mkdir)

    config = copy_config()

    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.export_replacements(invalid_target, config=config)
    assert exc_info.value.code == 1


def test_cli_export_replacements_default(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        ["sourcecombine", "--export-replacements", "--replace", "old", "new"]
    )

    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.main()

    assert exc_info.value.code == 0
    exported_file = tmp_path / "replacements.json"
    assert exported_file.is_file()
    data = json.loads(exported_file.read_text(encoding="utf-8"))
    assert data["total_rules"] == 1
    assert data["regex_replacements"] == [{'pattern': 'old', 'replacement': 'new'}]


def test_cli_export_replacements_aliases(tmp_path, monkeypatch):
    target1 = tmp_path / "alias1.json"
    monkeypatch.setattr(
        sys,
        "argv",
        ["sourcecombine", "--export-rep", str(target1), "--replace-line", "LOG.*", ""]
    )

    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.main()

    assert exc_info.value.code == 0
    assert target1.is_file()
    data1 = json.loads(target1.read_text(encoding="utf-8"))
    assert data1["line_regex_replacements"] == [{'pattern': 'LOG.*', 'replacement': ''}]

    target2 = tmp_path / "alias2.json"
    monkeypatch.setattr(
        sys,
        "argv",
        ["sourcecombine", "--export-rules", str(target2)]
    )

    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.main()

    assert exc_info.value.code == 0
    assert target2.is_file()


def test_cli_export_replacements_and_files_from_conflict(monkeypatch, caplog):
    monkeypatch.setattr(
        sys,
        "argv",
        ["sourcecombine", "--export-replacements", "--files-from", "list.txt"]
    )

    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.main()

    assert exc_info.value.code == 1
    assert "cannot use --export-replacements and --files-from at the same time" in caplog.text
