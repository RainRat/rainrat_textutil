import json
import pytest
from unittest.mock import patch
from pathlib import Path
from sourcecombine import main

def test_validate_config_valid_yaml(tmp_path, monkeypatch, caplog):
    config_file = tmp_path / "sourcecombine.yml"
    config_file.write_text("search:\n  recursive: true\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["sourcecombine", "--validate-config"])

    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0
    assert "is valid" in caplog.text

def test_validate_config_valid_json(tmp_path, monkeypatch, caplog):
    config_file = tmp_path / "custom_config.json"
    config_file.write_text(json.dumps({"search": {"recursive": False}}), encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["sourcecombine", "--validate-config", str(config_file)])

    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0
    assert "is valid" in caplog.text

def test_validate_config_json_output_success(tmp_path, monkeypatch, capsys):
    config_file = tmp_path / "sourcecombine.json"
    config_file.write_text(json.dumps({"search": {"recursive": True}}), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["sourcecombine", "--validate-config", "--json"])

    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["valid"] is True
    assert data["path"] == str(config_file.resolve())

def test_validate_config_missing_file(tmp_path, monkeypatch, caplog):
    non_existent = tmp_path / "missing.yml"
    monkeypatch.setattr("sys.argv", ["sourcecombine", "--validate-config", str(non_existent)])

    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1
    assert "Could not find configuration file" in caplog.text

def test_validate_config_missing_file_json(tmp_path, monkeypatch, capsys):
    non_existent = tmp_path / "missing.yml"
    monkeypatch.setattr("sys.argv", ["sourcecombine", "--validate-config", str(non_existent), "--json"])

    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["valid"] is False
    assert "Could not find configuration file" in data["error"]

def test_validate_config_no_file_found(tmp_path, monkeypatch, caplog):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["sourcecombine", "--validate-config"])

    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1
    assert "No configuration file specified or found" in caplog.text

def test_validate_config_no_file_found_json(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["sourcecombine", "--validate-config", "--json"])

    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["valid"] is False
    assert "No configuration file specified or found" in data["error"]

def test_validate_config_invalid_schema(tmp_path, monkeypatch, caplog):
    config_file = tmp_path / "invalid.yml"
    # search section as integer instead of dict causes InvalidConfigError
    config_file.write_text("search: 123\n", encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["sourcecombine", "--validate-config", str(config_file)])

    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1
    assert "is invalid" in caplog.text

def test_validate_config_invalid_schema_json(tmp_path, monkeypatch, capsys):
    config_file = tmp_path / "invalid.yml"
    config_file.write_text("search: 123\n", encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["sourcecombine", "--validate-config", str(config_file), "--json"])

    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["valid"] is False
    assert "error" in data

def test_validate_config_from_positional_target(tmp_path, monkeypatch, caplog):
    config_file = tmp_path / "target_config.yml"
    config_file.write_text("search:\n  recursive: true\n", encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["sourcecombine", str(config_file), "--validate-config"])

    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0
    assert "is valid" in caplog.text
