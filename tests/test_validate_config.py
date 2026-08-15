import json
import os
from pathlib import Path
import pytest
from unittest.mock import patch

from sourcecombine import main


def test_validate_config_valid_yaml(tmp_path, capsys):
    config_file = tmp_path / "valid_config.yml"
    config_file.write_text("search:\n  recursive: true\nfilters:\n  unique: true\n", encoding="utf-8")

    with patch("sys.argv", ["sourcecombine", "--validate-config", str(config_file)]):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    captured = capsys.readouterr()
    assert "CONFIGURATION VALIDATION" in captured.out
    assert "Status:   VALID" in captured.out
    assert "search" in captured.out


def test_validate_config_valid_json(tmp_path, capsys):
    config_file = tmp_path / "valid_config.json"
    config_file.write_text(json.dumps({"search": {"recursive": True}, "filters": {"unique": True}}), encoding="utf-8")

    with patch("sys.argv", ["sourcecombine", "--validate-config", str(config_file)]):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    captured = capsys.readouterr()
    assert "CONFIGURATION VALIDATION" in captured.out
    assert "Status:   VALID" in captured.out


def test_validate_config_valid_json_output(tmp_path, capsys):
    config_file = tmp_path / "valid_config.yml"
    config_file.write_text("search:\n  recursive: true\n", encoding="utf-8")

    with patch("sys.argv", ["sourcecombine", "--validate-config", str(config_file), "--json"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["status"] == "valid"
    assert data["file"] == str(config_file)
    assert "search" in data["sections"]


def test_validate_config_invalid_yaml(tmp_path, capsys):
    config_file = tmp_path / "invalid_config.yml"
    config_file.write_text("search: [invalid yaml structure: {", encoding="utf-8")

    with patch("sys.argv", ["sourcecombine", "--validate-config", str(config_file)]):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

    captured = capsys.readouterr()
    assert "CONFIGURATION VALIDATION" in captured.out
    assert "Status: INVALID" in captured.out


def test_validate_config_invalid_yaml_json_output(tmp_path, capsys):
    config_file = tmp_path / "invalid_config.yml"
    config_file.write_text("search: [invalid yaml structure: {", encoding="utf-8")

    with patch("sys.argv", ["sourcecombine", "--validate-config", str(config_file), "--json"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["status"] == "invalid"
    assert "error" in data


def test_validate_config_nonexistent_file(tmp_path, capsys):
    config_file = tmp_path / "does_not_exist.yml"

    with patch("sys.argv", ["sourcecombine", "--validate-config", str(config_file)]):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1


def test_validate_config_nonexistent_file_json_output(tmp_path, capsys):
    config_file = tmp_path / "does_not_exist.yml"

    with patch("sys.argv", ["sourcecombine", "--validate-config", str(config_file), "--json"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["status"] == "error"
    assert "does not exist" in data["message"]


def test_validate_config_autodiscover(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    config_file = tmp_path / "sourcecombine.yml"
    config_file.write_text("search:\n  recursive: true\n", encoding="utf-8")

    with patch("sys.argv", ["sourcecombine", "--validate-config"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    captured = capsys.readouterr()
    assert "CONFIGURATION VALIDATION" in captured.out
    assert "sourcecombine.yml" in captured.out


def test_validate_config_with_explicit_config_flag(tmp_path, capsys):
    config_file = tmp_path / "custom.json"
    config_file.write_text(json.dumps({"search": {"recursive": True}}), encoding="utf-8")

    with patch("sys.argv", ["sourcecombine", "-k", str(config_file), "--validate-config"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    captured = capsys.readouterr()
    assert "CONFIGURATION VALIDATION" in captured.out
    assert str(config_file) in captured.out


def test_validate_config_no_file_found(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    with patch("sys.argv", ["sourcecombine", "--validate-config"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1


def test_validate_config_no_file_found_json_output(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    with patch("sys.argv", ["sourcecombine", "--validate-config", "--json"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["status"] == "error"
    assert "No configuration file specified" in data["message"]
