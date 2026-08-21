import io
import json
import pytest
from unittest.mock import patch

import utils
import sourcecombine


def test_load_yaml_config_stdin_yaml(monkeypatch):
    yaml_content = "search:\n  max_depth: 3\n"
    monkeypatch.setattr("sys.stdin", io.StringIO(yaml_content))
    config = utils.load_yaml_config("-")
    assert config["search"]["max_depth"] == 3


def test_load_yaml_config_stdin_json(monkeypatch):
    json_content = json.dumps({"search": {"max_depth": 5}})
    monkeypatch.setattr("sys.stdin", io.StringIO(json_content))
    config = utils.load_yaml_config("-")
    assert config["search"]["max_depth"] == 5


def test_load_yaml_config_stdin_empty(monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("   \n"))
    with pytest.raises(utils.InvalidConfigError, match="empty"):
        utils.load_yaml_config("-")


def test_load_yaml_config_stdin_invalid_yaml(monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("invalid: [yaml: foo: :"))
    with pytest.raises(utils.InvalidConfigError):
        utils.load_yaml_config("-")


def test_load_yaml_config_stdin_non_dict(monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("- item1\n- item2\n"))
    with pytest.raises(utils.InvalidConfigError, match="dictionary"):
        utils.load_yaml_config("-")


def test_save_yaml_config_stdout(monkeypatch, capsys):
    config = {"logging": {"level": "DEBUG"}}
    utils.save_yaml_config("-", config)
    captured = capsys.readouterr().out
    assert "# SourceCombine Configuration" in captured
    assert "level: DEBUG" in captured


def test_save_yaml_config_stdout_no_yaml(monkeypatch, capsys):
    monkeypatch.setattr(utils, "yaml", None)
    config = {"logging": {"level": "INFO"}}
    utils.save_yaml_config("-", config)
    captured = capsys.readouterr().out
    assert '"level": "INFO"' in captured


def test_cli_init_stdout(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["sourcecombine.py", "--init", "-"])
    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.main()
    assert exc_info.value.code == 0
    captured = capsys.readouterr().out
    assert "# Default SourceCombine Configuration" in captured or "logging" in captured


def test_cli_init_stdout_json(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["sourcecombine.py", "--init", "-", "--json"])
    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.main()
    assert exc_info.value.code == 0
    captured = capsys.readouterr().out
    data = json.loads(captured)
    assert "search" in data


def test_cli_export_config_stdout(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["sourcecombine.py", "--export-config", "-"])
    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.main()
    assert exc_info.value.code == 0
    captured = capsys.readouterr().out
    assert "logging" in captured


def test_cli_validate_config_stdin_valid(monkeypatch, capsys):
    yaml_content = "search:\n  max_depth: 2\n"
    monkeypatch.setattr("sys.stdin", io.StringIO(yaml_content))
    monkeypatch.setattr("sys.argv", ["sourcecombine.py", "--validate-config", "-"])
    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.main()
    assert exc_info.value.code == 0


def test_cli_validate_config_stdin_json_valid(monkeypatch, capsys):
    json_content = json.dumps({"search": {"max_depth": 2}})
    monkeypatch.setattr("sys.stdin", io.StringIO(json_content))
    monkeypatch.setattr("sys.argv", ["sourcecombine.py", "--validate-config", "-", "--json"])
    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.main()
    assert exc_info.value.code == 0
    captured = capsys.readouterr().out
    data = json.loads(captured)
    assert data["valid"] is True
    assert data["path"] == "<stdin>"


def test_cli_validate_config_stdin_invalid(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO("invalid: [yaml: foo: :"))
    monkeypatch.setattr("sys.argv", ["sourcecombine.py", "--validate-config", "-", "--json"])
    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.main()
    assert exc_info.value.code == 1
    captured = capsys.readouterr().out
    data = json.loads(captured)
    assert data["valid"] is False
    assert data["path"] == "<stdin>"


def test_cli_config_stdin_combine(monkeypatch, tmp_path, capsys):
    test_file = tmp_path / "sample.py"
    test_file.write_text("print('hello')\n")
    out_file = tmp_path / "output.txt"

    yaml_config = f"search:\n  root_folders:\n    - '{tmp_path}'\noutput:\n  file: '{out_file}'\n"
    monkeypatch.setattr("sys.stdin", io.StringIO(yaml_config))
    monkeypatch.setattr("sys.argv", ["sourcecombine.py", "--config", "-"])

    sourcecombine.main()
    assert out_file.exists()
    assert "print('hello')" in out_file.read_text()
