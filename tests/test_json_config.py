import json
import pytest
from pathlib import Path
from utils import load_config, save_config, DEFAULT_CONFIG
import utils
import sourcecombine


def test_load_valid_json_config(tmp_path):
    config_data = {
        "search": {
            "max_depth": 3,
            "use_git": True
        },
        "filters": {
            "unique": True
        }
    }
    config_file = tmp_path / "sourcecombine.json"
    config_file.write_text(json.dumps(config_data), encoding="utf-8")

    loaded = load_config(config_file)
    assert loaded["search"]["max_depth"] == 3
    assert loaded["search"]["use_git"] is True
    assert loaded["filters"]["unique"] is True


def test_load_invalid_json_config(tmp_path):
    config_file = tmp_path / "sourcecombine.json"
    config_file.write_text("{invalid json: }", encoding="utf-8")

    with pytest.raises(utils.InvalidConfigError):
        load_config(config_file)


def test_load_config_non_existent_file(tmp_path):
    config_file = tmp_path / "non_existent.json"
    with pytest.raises(utils.ConfigNotFoundError):
        load_config(config_file)


def test_load_config_by_first_character_brace(tmp_path):
    config_data = {
        "search": {
            "max_depth": 5
        }
    }
    config_file = tmp_path / "sourcecombine.conf"
    config_file.write_text(json.dumps(config_data), encoding="utf-8")

    loaded = load_config(config_file)
    assert loaded["search"]["max_depth"] == 5


def test_save_json_config(tmp_path):
    config_data = {
        "search": {
            "max_depth": 2
        }
    }
    config_file = tmp_path / "exported.json"
    save_config(config_file, config_data)

    assert config_file.exists()
    loaded = json.loads(config_file.read_text(encoding="utf-8"))
    assert loaded["search"]["max_depth"] == 2


def test_fallback_to_json_when_yaml_is_none(tmp_path, monkeypatch):
    monkeypatch.setattr(utils, "yaml", None)

    config_data = {
        "search": {
            "max_depth": 4
        }
    }
    config_file = tmp_path / "sourcecombine.yaml"
    config_file.write_text(json.dumps(config_data), encoding="utf-8")

    loaded = load_config(config_file)
    assert loaded["search"]["max_depth"] == 4


def test_save_config_falls_back_to_json_when_yaml_is_none(tmp_path, monkeypatch):
    monkeypatch.setattr(utils, "yaml", None)

    config_data = {
        "search": {
            "max_depth": 7
        }
    }
    config_file = tmp_path / "exported.yaml"
    save_config(config_file, config_data)

    assert config_file.exists()
    loaded = json.loads(config_file.read_text(encoding="utf-8"))
    assert loaded["search"]["max_depth"] == 7


def test_cli_auto_discovers_json_config(tmp_path, monkeypatch):
    config_data = {
        "search": {
            "root_folders": [str(tmp_path)]
        },
        "filters": {
            "unique": True
        }
    }
    config_file = tmp_path / "sourcecombine.json"
    config_file.write_text(json.dumps(config_data), encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["sourcecombine.py", "--show-config", "--json"])

    import io
    import sys
    stdout_capture = io.StringIO()
    monkeypatch.setattr(sys, "stdout", stdout_capture)

    with pytest.raises(SystemExit) as exc:
        sourcecombine.main()

    assert exc.value.code == 0
    config_out = json.loads(stdout_capture.getvalue())
    assert config_out["filters"]["unique"] is True


def test_cli_targets_first_as_json_config(tmp_path, monkeypatch):
    config_data = {
        "search": {
            "root_folders": [str(tmp_path)]
        },
        "filters": {
            "unique": True
        }
    }
    config_file = tmp_path / "my_config.json"
    config_file.write_text(json.dumps(config_data), encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["sourcecombine.py", str(config_file), "--show-config", "--json"])

    import io
    import sys
    stdout_capture = io.StringIO()
    monkeypatch.setattr(sys, "stdout", stdout_capture)

    with pytest.raises(SystemExit) as exc:
        sourcecombine.main()

    assert exc.value.code == 0
    config_out = json.loads(stdout_capture.getvalue())
    assert config_out["filters"]["unique"] is True


def test_cli_export_config_as_json(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    exported_file = tmp_path / "exported_config.json"
    monkeypatch.setattr("sys.argv", ["sourcecombine.py", "--export-config", str(exported_file)])

    with pytest.raises(SystemExit) as exc:
        sourcecombine.main()

    assert exc.value.code == 0
    assert exported_file.exists()
    loaded = json.loads(exported_file.read_text(encoding="utf-8"))
    assert "search" in loaded
