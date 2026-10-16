import io
import json
import pytest
import sys
import utils
import sourcecombine


def copy_default_config():
    cfg = sourcecombine.copy.deepcopy(utils.DEFAULT_CONFIG)
    utils.validate_config(cfg)
    return cfg


def test_import_config_none_args():
    cfg = copy_default_config()
    assert sourcecombine.import_config(None, cfg) is cfg
    assert sourcecombine.import_config("some_path.json", None) is None


def test_import_config_json_file(tmp_path):
    cfg_file = tmp_path / "imported_config.json"
    import_data = {
        "search": {
            "recursive": False,
            "max_depth": 3,
            "allowed_languages": ["python", "javascript"]
        },
        "filters": {
            "unique": True,
            "min_tokens": 10
        },
        "project": {
            "name": "ImportedTestProject"
        }
    }
    cfg_file.write_text(json.dumps(import_data), encoding="utf-8")

    cfg = copy_default_config()
    result = sourcecombine.import_config(cfg_file, cfg)

    assert result["search"]["recursive"] is False
    assert result["search"]["max_depth"] == 3
    assert result["search"]["allowed_languages"] == ["python", "javascript"]
    assert result["filters"]["unique"] is True
    assert result["filters"]["min_tokens"] == 10
    assert result["project"]["name"] == "ImportedTestProject"


def test_import_config_yaml_file(tmp_path):
    cfg_file = tmp_path / "imported_config.yml"
    yaml_content = """
search:
  recursive: false
  max_depth: 2
filters:
  skip_binary: true
processing:
  compact_whitespace: true
"""
    cfg_file.write_text(yaml_content, encoding="utf-8")

    cfg = copy_default_config()
    result = sourcecombine.import_config(cfg_file, cfg)

    assert result["search"]["recursive"] is False
    assert result["search"]["max_depth"] == 2
    assert result["filters"]["skip_binary"] is True
    assert result["processing"]["compact_whitespace"] is True


def test_import_config_stdin(monkeypatch):
    import_data = {
        "output": {
            "format": "markdown",
            "table_of_contents": True
        }
    }
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(import_data)))

    cfg = copy_default_config()
    result = sourcecombine.import_config("-", cfg)

    assert result["output"]["format"] == "markdown"
    assert result["output"]["table_of_contents"] is True


def test_import_config_empty_file(tmp_path, caplog):
    empty_file = tmp_path / "empty.json"
    empty_file.write_text("   \n", encoding="utf-8")

    cfg = copy_default_config()
    with caplog.at_level("WARNING"):
        result = sourcecombine.import_config(empty_file, cfg)

    assert result is cfg
    assert "is empty" in caplog.text


def test_import_config_nonexistent_file(tmp_path):
    non_file = tmp_path / "does_not_exist.json"
    cfg = copy_default_config()

    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.import_config(non_file, cfg)
    assert exc_info.value.code == 1


def test_import_config_os_error(tmp_path, monkeypatch):
    test_file = tmp_path / "unreadable.json"
    test_file.write_text("{}", encoding="utf-8")

    def mock_open(*args, **kwargs):
        raise OSError("Permission denied")

    monkeypatch.setattr("builtins.open", mock_open)

    cfg = copy_default_config()
    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.import_config(test_file, cfg)
    assert exc_info.value.code == 1


def test_import_config_invalid_format(tmp_path):
    invalid_file = tmp_path / "invalid.json"
    invalid_file.write_text("[1, 2, 3]", encoding="utf-8")

    cfg = copy_default_config()
    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.import_config(invalid_file, cfg)
    assert exc_info.value.code == 1


def test_import_config_invalid_syntax(tmp_path):
    syntax_err_file = tmp_path / "syntax.json"
    syntax_err_file.write_text("{invalid json", encoding="utf-8")

    cfg = copy_default_config()
    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.import_config(syntax_err_file, cfg)
    assert exc_info.value.code == 1


def test_import_config_no_yaml(tmp_path, monkeypatch):
    syntax_err_file = tmp_path / "syntax.json"
    syntax_err_file.write_text("{invalid json", encoding="utf-8")

    monkeypatch.setattr(utils, "yaml", None)

    cfg = copy_default_config()
    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.import_config(syntax_err_file, cfg)
    assert exc_info.value.code == 1


def test_import_config_validation_failure(tmp_path):
    bad_val_file = tmp_path / "bad_val.json"
    bad_val_data = {
        "search": {
            "max_depth": -5
        }
    }
    bad_val_file.write_text(json.dumps(bad_val_data), encoding="utf-8")

    cfg = copy_default_config()
    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.import_config(bad_val_file, cfg)
    assert exc_info.value.code == 1


def test_import_config_cli_flags(tmp_path, monkeypatch):
    import_file = tmp_path / "cli_import.json"
    import_file.write_text(json.dumps({
        "filters": {
            "min_tokens": 42
        }
    }), encoding="utf-8")

    test_file = tmp_path / "sample.py"
    test_file.write_text("print('hello')", encoding="utf-8")

    monkeypatch.setattr("sys.argv", [
        "sourcecombine.py",
        str(tmp_path),
        "--import-config", str(import_file),
        "--show-config",
        "--json"
    ])

    captured_out = io.StringIO()
    monkeypatch.setattr("sys.stdout", captured_out)

    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.main()

    assert exc_info.value.code == 0
    out_json = json.loads(captured_out.getvalue())
    assert out_json["filters"]["min_tokens"] == 42


def test_import_cfg_alias(tmp_path, monkeypatch):
    import_file = tmp_path / "alias_import.json"
    import_file.write_text(json.dumps({
        "filters": {
            "min_lines": 15
        }
    }), encoding="utf-8")

    monkeypatch.setattr("sys.argv", [
        "sourcecombine.py",
        str(tmp_path),
        "--import-cfg", str(import_file),
        "--show-config",
        "--json"
    ])

    captured_out = io.StringIO()
    monkeypatch.setattr("sys.stdout", captured_out)

    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.main()

    assert exc_info.value.code == 0
    out_json = json.loads(captured_out.getvalue())
    assert out_json["filters"]["min_lines"] == 15


def test_deep_merge_dict_non_dict_inputs():
    assert sourcecombine._deep_merge_dict("not_a_dict", {"a": 1}) == "not_a_dict"
    assert sourcecombine._deep_merge_dict({"a": 1}, "not_a_dict") == {"a": 1}


def test_main_invalid_config_error_handling(tmp_path, monkeypatch):
    invalid_config = tmp_path / "invalid_config.json"
    invalid_config.write_text(json.dumps({"search": {"max_depth": -10}}), encoding="utf-8")

    monkeypatch.setattr("sys.argv", [
        "sourcecombine.py",
        str(tmp_path),
        "--config", str(invalid_config)
    ])

    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.main()

    assert exc_info.value.code == 1


def test_cli_list_replacements_with_import_config(tmp_path, monkeypatch):
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(json.dumps({
        "processing": {
            "regex_replacements": [{"pattern": "FOO", "replacement": "BAR"}]
        }
    }), encoding="utf-8")

    monkeypatch.setattr("sys.argv", [
        "sourcecombine.py",
        "--list-replacements",
        "--import-config", str(cfg_file)
    ])

    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.main()

    assert exc_info.value.code == 0
