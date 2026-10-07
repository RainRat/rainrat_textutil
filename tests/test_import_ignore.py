import json
import logging
import sys
import pytest

import sourcecombine
import utils


def copy_config():
    import copy
    cfg = copy.deepcopy(utils.DEFAULT_CONFIG)
    utils.validate_config(cfg)
    return cfg


def test_import_ignore_patterns_text_file(tmp_path):
    ignore_file = tmp_path / "custom.ignore"
    ignore_file.write_text("# Comment line\n*.tmp\n\nnode_modules/\n", encoding="utf-8")

    config = copy_config()
    sourcecombine.import_ignore_patterns(ignore_file, config)

    filenames = config['filters']['exclusions']['filenames']
    assert "*.tmp" in filenames
    assert "node_modules/" in filenames
    assert "# Comment line" not in filenames


def test_import_ignore_patterns_json_list(tmp_path):
    ignore_file = tmp_path / "patterns.json"
    data = ["*.log", "build/"]
    ignore_file.write_text(json.dumps(data), encoding="utf-8")

    config = copy_config()
    sourcecombine.import_ignore_patterns(ignore_file, config)

    filenames = config['filters']['exclusions']['filenames']
    assert "*.log" in filenames
    assert "build/" in filenames


def test_import_ignore_patterns_json_dict_patterns(tmp_path):
    ignore_file = tmp_path / "patterns.json"
    data = {"patterns": ["*.bak", "dist/"]}
    ignore_file.write_text(json.dumps(data), encoding="utf-8")

    config = copy_config()
    sourcecombine.import_ignore_patterns(ignore_file, config)

    filenames = config['filters']['exclusions']['filenames']
    assert "*.bak" in filenames
    assert "dist/" in filenames


def test_import_ignore_patterns_json_dict_exclusions_nested(tmp_path):
    ignore_file = tmp_path / "patterns.json"
    data = {"exclusions": {"filenames": ["*.cache"]}}
    ignore_file.write_text(json.dumps(data), encoding="utf-8")

    config = copy_config()
    sourcecombine.import_ignore_patterns(ignore_file, config)

    filenames = config['filters']['exclusions']['filenames']
    assert "*.cache" in filenames


def test_import_ignore_patterns_yaml_dict(tmp_path):
    if not utils.yaml:
        pytest.skip("PyYAML not installed")

    ignore_file = tmp_path / "patterns.yml"
    yaml_content = "patterns:\n  - '*.out'\n  - target/\n"
    ignore_file.write_text(yaml_content, encoding="utf-8")

    config = copy_config()
    sourcecombine.import_ignore_patterns(ignore_file, config)

    filenames = config['filters']['exclusions']['filenames']
    assert "*.out" in filenames
    assert "target/" in filenames


def test_import_ignore_patterns_stdin(monkeypatch):
    stdin_content = "*.pyc\n__pycache__/\n"
    monkeypatch.setattr(sys, "stdin", sys.stdin)
    monkeypatch.setattr("sys.stdin.read", lambda: stdin_content)

    config = copy_config()
    sourcecombine.import_ignore_patterns("-", config)

    filenames = config['filters']['exclusions']['filenames']
    assert "*.pyc" in filenames
    assert "__pycache__/" in filenames


def test_import_ignore_patterns_missing_file(tmp_path, caplog):
    non_existent = tmp_path / "missing.ignore"
    config = copy_config()

    with caplog.at_level(logging.ERROR):
        with pytest.raises(SystemExit) as exc_info:
            sourcecombine.import_ignore_patterns(non_existent, config)

    assert exc_info.value.code == 1
    assert "Ignore file not found" in caplog.text


def test_import_ignore_patterns_empty_file(tmp_path, caplog):
    empty_file = tmp_path / "empty.ignore"
    empty_file.write_text("   \n", encoding="utf-8")

    config = copy_config()
    with caplog.at_level(logging.WARNING):
        result = sourcecombine.import_ignore_patterns(empty_file, config)

    assert result == config
    assert "is empty" in caplog.text


def test_import_ignore_patterns_none_inputs():
    assert sourcecombine.import_ignore_patterns(None, {}) == {}
    assert sourcecombine.import_ignore_patterns("file.txt", None) is None


def test_cli_import_ignore_and_list_ignores(tmp_path, monkeypatch, capsys):
    ignore_file = tmp_path / "cli.ignore"
    ignore_file.write_text("*.cli_ignore\n", encoding="utf-8")

    monkeypatch.setattr(sys, "argv", ["sourcecombine", "--import-ignore", str(ignore_file), "--list-ignores"])

    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.main()

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "*.cli_ignore" in captured.out


def test_cli_import_ig_alias(tmp_path, monkeypatch, capsys):
    ignore_file = tmp_path / "cli_alias.ignore"
    ignore_file.write_text("*.alias_ignore\n", encoding="utf-8")

    monkeypatch.setattr(sys, "argv", ["sourcecombine", "--import-ig", str(ignore_file), "--list-ignores"])

    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.main()

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "*.alias_ignore" in captured.out
