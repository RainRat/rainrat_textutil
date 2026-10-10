import json
import pytest
import sys
import copy
from pathlib import Path
import sourcecombine
import utils


def test_import_config_none_or_empty(tmp_path):
    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    res = sourcecombine.import_config(None, config)
    assert res == config

    res_empty = sourcecombine.import_config("", config)
    assert res_empty == config


def test_import_config_default_initialization(tmp_path):
    import_file = tmp_path / "extra_config.json"
    import_file.write_text(json.dumps({"output": {"format": "json"}}), encoding="utf-8")

    res = sourcecombine.import_config(str(import_file), config=None)
    assert res["output"]["format"] == "json"


def test_import_config_json_file(tmp_path):
    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    import_file = tmp_path / "extra.json"
    import_file.write_text(json.dumps({"processing": {"max_lines": 50}}), encoding="utf-8")

    res = sourcecombine.import_config(str(import_file), config)
    assert res["processing"]["max_lines"] == 50


def test_import_config_yaml_file(tmp_path):
    if not utils.yaml:
        pytest.skip("PyYAML not installed")

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    import_file = tmp_path / "extra.yml"
    import_file.write_text("filters:\n  max_size: 1048576\n", encoding="utf-8")

    res = sourcecombine.import_config(str(import_file), config)
    assert res["filters"]["max_size"] == 1048576


def test_import_config_stdin(monkeypatch):
    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    monkeypatch.setattr(sys, "stdin", type("StdinMock", (), {"read": lambda self: json.dumps({"output": {"format": "xml"}})})())

    res = sourcecombine.import_config("-", config)
    assert res["output"]["format"] == "xml"


def test_import_config_file_not_found():
    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    with pytest.raises(SystemExit) as exc:
        sourcecombine.import_config("non_existent_file.json", config)
    assert exc.value.code == 1


def test_import_config_os_error(tmp_path, monkeypatch):
    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    import_file = tmp_path / "unreadable.json"
    import_file.write_text("{}", encoding="utf-8")

    def mock_open(*args, **kwargs):
        raise OSError("Permission denied")

    monkeypatch.setattr("builtins.open", mock_open)
    with pytest.raises(SystemExit) as exc:
        sourcecombine.import_config(str(import_file), config)
    assert exc.value.code == 1


def test_import_config_empty_file(tmp_path, caplog):
    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    import_file = tmp_path / "empty.json"
    import_file.write_text("   \n", encoding="utf-8")

    res = sourcecombine.import_config(str(import_file), config)
    assert res == config
    assert "empty" in caplog.text


def test_import_config_invalid_json_yaml(tmp_path):
    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    import_file = tmp_path / "invalid.json"
    import_file.write_text("{\n  invalid: [unclosed bracket\n", encoding="utf-8")

    with pytest.raises(SystemExit) as exc:
        sourcecombine.import_config(str(import_file), config)
    assert exc.value.code == 1


def test_import_config_not_a_dict(tmp_path):
    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    import_file = tmp_path / "list_config.json"
    import_file.write_text(json.dumps(["item1", "item2"]), encoding="utf-8")

    with pytest.raises(SystemExit) as exc:
        sourcecombine.import_config(str(import_file), config)
    assert exc.value.code == 1


def test_import_config_invalid_schema(tmp_path):
    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    import_file = tmp_path / "bad_schema.json"
    # max_depth must be an integer, passing a dict/string will fail validation
    import_file.write_text(json.dumps({"search": {"max_depth": "invalid_number"}}), encoding="utf-8")

    with pytest.raises(SystemExit) as exc:
        sourcecombine.import_config(str(import_file), config)
    assert exc.value.code == 1


def test_cli_import_config(tmp_path, monkeypatch, capsys):
    import_file = tmp_path / "cli_extra.json"
    import_file.write_text(json.dumps({"project": {"name": "ImportedTestProject"}}), encoding="utf-8")

    monkeypatch.setattr(sys, "argv", ["sourcecombine", "--import-config", str(import_file), "--show-config", "--json"])

    with pytest.raises(SystemExit) as exc:
        sourcecombine.main()
    assert exc.value.code == 0

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data.get("project", {}).get("name") == "ImportedTestProject"
