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


def test_export_lang_map_none_config(tmp_path):
    target = tmp_path / "lang_map_none_cfg.json"
    sourcecombine.export_lang_map(target, config=None)
    assert target.is_file()
    data = json.loads(target.read_text(encoding="utf-8"))
    assert "total_mappings" in data
    assert "custom_languages" in data


def test_export_lang_map_default_file(tmp_path, monkeypatch, caplog):
    monkeypatch.chdir(tmp_path)
    config = copy_config()
    config['search']['custom_languages'] = {
        '.mjml': 'html',
        '.blade.php': 'php'
    }

    with caplog.at_level(logging.INFO):
        sourcecombine.export_lang_map("lang_map.json", config=config)

    exported_file = tmp_path / "lang_map.json"
    assert exported_file.is_file()
    data = json.loads(exported_file.read_text(encoding="utf-8"))
    assert data["total_mappings"] == 2
    assert data["custom_languages"] == {'.mjml': 'html', '.blade.php': 'php'}


def test_export_lang_map_custom_file(tmp_path, caplog):
    target = tmp_path / "custom_lang.json"
    config = copy_config()
    config['search']['custom_languages'] = {
        '.vue': 'html'
    }

    with caplog.at_level(logging.INFO):
        sourcecombine.export_lang_map(target, config=config)

    assert target.is_file()
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["total_mappings"] == 1
    assert data["custom_languages"][".vue"] == 'html'


def test_export_lang_map_directory_target(tmp_path):
    target_dir = tmp_path / "lang_dir"
    target_dir.mkdir()
    config = copy_config()
    config['search']['custom_languages'] = {'.svelte': 'html'}

    sourcecombine.export_lang_map(target_dir, config=config)

    expected_file = target_dir / "lang_map.json"
    assert expected_file.is_file()
    data = json.loads(expected_file.read_text(encoding="utf-8"))
    assert data["total_mappings"] == 1


def test_export_lang_map_stdout(capsys):
    config = copy_config()
    config['search']['custom_languages'] = {'.astro': 'html'}

    sourcecombine.export_lang_map("-", config=config)

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["exported_to"] == "-"
    assert data["total_mappings"] == 1
    assert data["custom_languages"] == {'.astro': 'html'}


def test_export_lang_map_write_error(tmp_path, monkeypatch):
    invalid_target = tmp_path / "nonexistent_dir" / "out.json"

    def mock_mkdir(*args, **kwargs):
        raise OSError("Permission denied")

    monkeypatch.setattr(Path, "mkdir", mock_mkdir)

    config = copy_config()

    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.export_lang_map(invalid_target, config=config)
    assert exc_info.value.code == 1


def test_cli_export_lang_map_default(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        ["sourcecombine", "--export-lang-map", "--map-lang", ".mjml", "html"]
    )

    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.main()

    assert exc_info.value.code == 0
    exported_file = tmp_path / "lang_map.json"
    assert exported_file.is_file()
    data = json.loads(exported_file.read_text(encoding="utf-8"))
    assert data["total_mappings"] == 1
    assert data["custom_languages"] == {'.mjml': 'html'}


def test_cli_export_lang_map_alias(tmp_path, monkeypatch):
    target = tmp_path / "alias_lang.json"
    monkeypatch.setattr(
        sys,
        "argv",
        ["sourcecombine", "--export-lang", str(target), "--map-lang", ".blade.php", "php"]
    )

    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.main()

    assert exc_info.value.code == 0
    assert target.is_file()
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["custom_languages"] == {'.blade.php': 'php'}


def test_cli_export_lang_map_and_files_from_conflict(monkeypatch, caplog):
    monkeypatch.setattr(
        sys,
        "argv",
        ["sourcecombine", "--export-lang-map", "--files-from", "list.txt"]
    )

    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.main()

    assert exc_info.value.code == 1
    assert "cannot use --export-lang-map and --files-from at the same time" in caplog.text
