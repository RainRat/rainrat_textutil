import json
import pytest
from unittest.mock import patch, mock_open
import sourcecombine
import utils


def test_import_replacements_os_error(tmp_path):
    target_file = tmp_path / "rules.json"
    target_file.touch()

    config = sourcecombine.DEFAULT_CONFIG.copy()

    with patch("builtins.open", side_effect=OSError("Disk error")):
        with pytest.raises(SystemExit) as exc_info:
            sourcecombine.import_replacements(target_file, config)
        assert exc_info.value.code == 1


def test_import_replacements_yaml_none_json_error(tmp_path):
    target_file = tmp_path / "rules.json"
    target_file.write_text("invalid json {", encoding="utf-8")

    config = sourcecombine.DEFAULT_CONFIG.copy()

    with patch.object(utils, "yaml", None):
        with pytest.raises(SystemExit) as exc_info:
            sourcecombine.import_replacements(target_file, config)
        assert exc_info.value.code == 1


def test_import_replacements_normalization_and_none_sections(tmp_path):
    rules_data = [
        123,
        {"pattern": None, "replacement": "test"},
        {"pattern": "foo", "replacement": None},
        {"search": "bar", "replace": "baz"},
    ]
    target_file = tmp_path / "rules.json"
    target_file.write_text(json.dumps(rules_data), encoding="utf-8")

    config = {
        "processing": {
            "regex_replacements": None,
            "line_regex_replacements": None,
        }
    }

    res = sourcecombine.import_replacements(target_file, config)
    regex_rules = res["processing"]["regex_replacements"]
    assert len(regex_rules) == 2
    assert regex_rules[0] == {"pattern": "foo", "replacement": ""}
    assert regex_rules[1] == {"pattern": "bar", "replacement": "baz"}


def test_import_replacements_config_none_processing(tmp_path):
    rules_data = [{"pattern": "hello", "replacement": "world"}]
    target_file = tmp_path / "rules.json"
    target_file.write_text(json.dumps(rules_data), encoding="utf-8")

    config = {"processing": None}

    res = sourcecombine.import_replacements(target_file, config)
    assert res["processing"]["regex_replacements"] == [
        {"pattern": "hello", "replacement": "world"}
    ]


def test_cli_list_replacements_with_import(tmp_path, monkeypatch, capsys):
    rules_data = {"text_replacements": [{"pattern": "cat", "replacement": "dog"}]}
    rules_file = tmp_path / "import_rules.json"
    rules_file.write_text(json.dumps(rules_data), encoding="utf-8")

    test_args = [
        "sourcecombine.py",
        "--list-replacements",
        "--import-replacements",
        str(rules_file),
    ]
    monkeypatch.setattr("sys.argv", test_args)

    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.main()
    assert exc_info.value.code == 0

    captured = capsys.readouterr()
    assert "cat" in captured.out
    assert "dog" in captured.out


def test_update_identity_from_dict_non_dict():
    identity = {}
    utils._update_identity_from_dict("not a dict", identity)
    assert identity == {}
    utils._update_identity_from_dict(12345, identity)
    assert identity == {}
    utils._update_identity_from_dict(None, identity)
    assert identity == {}
