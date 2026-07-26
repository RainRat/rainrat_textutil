import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
import utils
from sourcecombine import main

def test_load_json_config_directly(tmp_path):
    config_file = tmp_path / "test_config.json"
    data = {
        "logging": {"level": "DEBUG"},
        "search": {"max_depth": 5}
    }
    config_file.write_text(json.dumps(data), encoding="utf-8")

    loaded = utils.load_yaml_config(config_file)
    assert loaded["logging"]["level"] == "DEBUG"
    assert loaded["search"]["max_depth"] == 5

def test_save_json_config_directly(tmp_path):
    config_file = tmp_path / "test_config_out.json"
    data = {
        "logging": {"level": "WARNING"},
        "search": {"max_depth": 2}
    }
    utils.save_yaml_config(config_file, data)

    assert config_file.is_file()
    loaded_data = json.loads(config_file.read_text(encoding="utf-8"))
    assert loaded_data["logging"]["level"] == "WARNING"
    assert loaded_data["search"]["max_depth"] == 2

def test_save_json_config_os_error(tmp_path):
    invalid_path = tmp_path / "a_directory.json"
    invalid_path.mkdir()
    with pytest.raises(utils.InvalidConfigError):
        utils.save_yaml_config(invalid_path, {"test": "data"})

def test_load_invalid_json_config(tmp_path):
    config_file = tmp_path / "invalid.json"
    config_file.write_text("{malformed json", encoding="utf-8")

    with pytest.raises(utils.InvalidConfigError):
        utils.load_yaml_config(config_file)

def test_load_empty_json_config(tmp_path):
    config_file = tmp_path / "empty.json"
    config_file.write_text("null", encoding="utf-8")

    with pytest.raises(utils.InvalidConfigError):
        utils.load_yaml_config(config_file)

def test_load_non_existent_json_config():
    with pytest.raises(utils.ConfigNotFoundError):
        utils.load_yaml_config("non_existent_config.json")

def test_export_config_as_json_via_cli(tmp_path, monkeypatch):
    out_json = tmp_path / "exported.json"
    monkeypatch.chdir(tmp_path)

    args = ["sourcecombine.py", "--export-config", str(out_json)]
    with patch.object(sys, "argv", args):
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0

    assert out_json.is_file()
    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert "logging" in data
    assert "search" in data

def test_json_config_auto_discovery(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    config_file = tmp_path / "sourcecombine.json"
    config_data = {
        "logging": {"level": "DEBUG"},
        "search": {"max_depth": 11}
    }
    config_file.write_text(json.dumps(config_data), encoding="utf-8")

    dummy_file = tmp_path / "dummy.txt"
    dummy_file.write_text("some content", encoding="utf-8")

    args = ["sourcecombine.py", "--show-config", "--json"]
    with patch.object(sys, "argv", args):
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["logging"]["level"] == "DEBUG"
    assert data["search"]["max_depth"] == 11

def test_json_config_not_auto_discovered_in_verify_mode(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_file = tmp_path / "sourcecombine.json"
    config_data = {
        "logging": {"level": "DEBUG"},
        "search": {"max_depth": 11}
    }
    config_file.write_text(json.dumps(config_data), encoding="utf-8")

    args = ["sourcecombine.py", "--verify", "sourcecombine.json"]
    with patch.object(sys, "argv", args):
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1

def test_json_config_not_auto_discovered_in_extract_mode(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_file = tmp_path / "sourcecombine.json"
    config_data = {
        "logging": {"level": "DEBUG"},
        "search": {"max_depth": 11}
    }
    config_file.write_text(json.dumps(config_data), encoding="utf-8")

    args = ["sourcecombine.py", "--extract", "sourcecombine.json"]
    with patch.object(sys, "argv", args):
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1

def test_fallback_to_json_when_pyyaml_is_unavailable(tmp_path, monkeypatch):
    monkeypatch.setattr(utils, "yaml", None)
    config_file = tmp_path / "fallback.json"
    config_data = {
        "logging": {"level": "WARNING"},
        "search": {"max_depth": 8}
    }
    config_file.write_text(json.dumps(config_data), encoding="utf-8")

    loaded = utils.load_yaml_config(config_file)
    assert loaded["logging"]["level"] == "WARNING"
    assert loaded["search"]["max_depth"] == 8

    out_file = tmp_path / "fallback_saved.json"
    utils.save_yaml_config(out_file, config_data)
    assert out_file.is_file()

    loaded_saved = json.loads(out_file.read_text(encoding="utf-8"))
    assert loaded_saved["search"]["max_depth"] == 8

def test_project_info_json_config_auto_discovery(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    config_file = tmp_path / "sourcecombine.json"
    config_data = {
        "logging": {"level": "DEBUG"},
        "search": {"max_depth": 11}
    }
    config_file.write_text(json.dumps(config_data), encoding="utf-8")

    args = ["sourcecombine.py", "--project-info", "--json"]
    with patch.object(sys, "argv", args):
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "project_name" in data
