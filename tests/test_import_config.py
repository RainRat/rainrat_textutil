import json
import pytest
from sourcecombine import import_config, main


def test_import_config_none():
    assert import_config(None, {"key": "value"}) == {"key": "value"}
    assert import_config("file.yml", None) is None


def test_import_config_yaml_file(tmp_path):
    cfg_file = tmp_path / "imported.yml"
    cfg_file.write_text("output:\n  file: custom_output.txt\n", encoding="utf-8")

    config = {
        "output": {"file": "default.txt", "format": "text"},
        "search": {"recursive": True}
    }
    updated = import_config(cfg_file, config)
    assert updated["output"]["file"] == "custom_output.txt"
    assert updated["output"]["format"] == "text"


def test_import_config_json_file(tmp_path):
    cfg_file = tmp_path / "imported.json"
    cfg_file.write_text(json.dumps({"filters": {"skip_binary": True}}), encoding="utf-8")

    config = {
        "filters": {"skip_binary": False, "unique": True}
    }
    updated = import_config(cfg_file, config)
    assert updated["filters"]["skip_binary"] is True
    assert updated["filters"]["unique"] is True


def test_import_config_stdin(monkeypatch):
    monkeypatch.setattr("sys.stdin.read", lambda: json.dumps({"search": {"max_depth": 3}}))
    config = {"search": {"max_depth": 0, "recursive": True}}
    updated = import_config("-", config)
    assert updated["search"]["max_depth"] == 3
    assert updated["search"]["recursive"] is True


def test_import_config_empty_file(tmp_path, caplog):
    cfg_file = tmp_path / "empty.json"
    cfg_file.write_text("", encoding="utf-8")
    config = {"output": {"file": "out.txt"}}
    updated = import_config(cfg_file, config)
    assert updated["output"]["file"] == "out.txt"
    assert "empty; no settings imported." in caplog.text


def test_import_config_file_not_found():
    with pytest.raises(SystemExit):
        import_config("nonexistent_file_12345.yml", {})


def test_import_config_invalid_json(tmp_path):
    cfg_file = tmp_path / "invalid.json"
    cfg_file.write_text("{invalid json", encoding="utf-8")
    with pytest.raises(SystemExit):
        import_config(cfg_file, {})


def test_import_config_invalid_format(tmp_path):
    cfg_file = tmp_path / "list.json"
    cfg_file.write_text(json.dumps(["not", "a", "dict"]), encoding="utf-8")
    with pytest.raises(SystemExit):
        import_config(cfg_file, {})


def test_import_config_validation_error(tmp_path):
    cfg_file = tmp_path / "invalid_type.json"
    cfg_file.write_text(json.dumps({"search": {"max_depth": "invalid_integer"}}), encoding="utf-8")
    with pytest.raises(SystemExit):
        import_config(cfg_file, {})


def test_cli_import_config_integration(tmp_path, monkeypatch, capsys):
    cfg_file = tmp_path / "cli_cfg.json"
    cfg_file.write_text(json.dumps({"output": {"file": "cli_output.txt"}}), encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        ["sourcecombine.py", "--import-config", str(cfg_file), "--show-config"]
    )
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 0

    captured = capsys.readouterr()
    assert "cli_output.txt" in captured.out
