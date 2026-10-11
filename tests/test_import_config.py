import copy
import io
import json
import sys
import pytest
import sourcecombine
import utils


@pytest.fixture(autouse=True)
def restore_default_config():
    """Ensure utils.DEFAULT_CONFIG is restored after each test."""
    original = copy.deepcopy(utils.DEFAULT_CONFIG)
    yield
    utils.DEFAULT_CONFIG.clear()
    utils.DEFAULT_CONFIG.update(original)


def test_import_config_none_handling():
    assert sourcecombine.import_config(None, {"search": {}}) == {"search": {}}
    assert sourcecombine.import_config("test.yml", None) is None


def test_import_config_nonexistent_file(tmp_path, caplog):
    non_existent = tmp_path / "does_not_exist.yml"
    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    with pytest.raises(SystemExit) as exc:
        sourcecombine.import_config(non_existent, config)
    assert exc.value.code == 1
    assert "Configuration import file not found" in caplog.text


def test_import_config_file_read_error(tmp_path, monkeypatch, caplog):
    file_path = tmp_path / "unreadable.yml"
    file_path.write_text("search:\n  recursive: false\n")

    def mock_open(*args, **kwargs):
        raise OSError("Permission denied")

    monkeypatch.setattr("builtins.open", mock_open)
    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    with pytest.raises(SystemExit) as exc:
        sourcecombine.import_config(file_path, config)
    assert exc.value.code == 1
    assert "Could not read configuration import file" in caplog.text


def test_import_config_empty_file(tmp_path, caplog):
    empty_file = tmp_path / "empty.yml"
    empty_file.write_text("   \n")
    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    result = sourcecombine.import_config(empty_file, config)
    assert result == config
    assert "is empty; no settings imported" in caplog.text


def test_import_config_invalid_json_or_yaml(tmp_path, caplog):
    invalid_file = tmp_path / "invalid.yaml"
    invalid_file.write_text("::: [invalid yaml :::")
    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    with pytest.raises(SystemExit) as exc:
        sourcecombine.import_config(invalid_file, config)
    assert exc.value.code == 1
    assert "Could not parse configuration import file" in caplog.text


def test_import_config_non_dict_payload(tmp_path, caplog):
    list_file = tmp_path / "list.json"
    list_file.write_text('["item1", "item2"]')
    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    with pytest.raises(SystemExit) as exc:
        sourcecombine.import_config(list_file, config)
    assert exc.value.code == 1
    assert "must be a JSON/YAML dictionary object" in caplog.text


def test_import_config_invalid_merged_config(tmp_path, caplog):
    invalid_cfg = tmp_path / "bad_config.json"
    invalid_cfg.write_text(json.dumps({"filters": {"max_total_tokens": -5}}))
    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    with pytest.raises(SystemExit) as exc:
        sourcecombine.import_config(invalid_cfg, config)
    assert exc.value.code == 1
    assert "Invalid merged configuration from" in caplog.text


def test_import_config_valid_json_and_yaml_merging(tmp_path):
    json_cfg = tmp_path / "custom.json"
    json_cfg.write_text(json.dumps({
        "search": {"recursive": False, "max_depth": 3},
        "filters": {"exclusions": {"folders": ["custom_dir"]}}
    }))

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    merged = sourcecombine.import_config(json_cfg, config)
    assert merged["search"]["recursive"] is False
    assert merged["search"]["max_depth"] == 3
    assert "custom_dir" in merged["filters"]["exclusions"]["folders"]


def test_import_config_stdin(monkeypatch):
    json_data = json.dumps({"project": {"name": "StdinProject", "version": "1.2.3"}})
    monkeypatch.setattr(sys, "stdin", io.StringIO(json_data))

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    merged = sourcecombine.import_config("-", config)
    assert merged["project"]["name"] == "StdinProject"
    assert merged["project"]["version"] == "1.2.3"


def test_cli_import_config_integration(tmp_path, monkeypatch):
    import_file = tmp_path / "imported_settings.json"
    import_file.write_text(json.dumps({
        "project": {"name": "CLIImportedProject"}
    }))

    test_args = ["sourcecombine.py", "--import-config", str(import_file), "--show-config"]
    monkeypatch.setattr(sys, "argv", test_args)

    with pytest.raises(SystemExit) as exc:
        sourcecombine.main()
    assert exc.value.code == 0
