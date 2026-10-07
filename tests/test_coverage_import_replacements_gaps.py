import copy
import json
import pytest
import utils
import sourcecombine


def test_import_replacements_os_error_handling(tmp_path):
    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    dir_path = tmp_path / "dir_as_file"
    dir_path.mkdir()
    with pytest.raises(SystemExit):
        sourcecombine.import_replacements(dir_path, config)


def test_import_replacements_no_yaml_json_error(tmp_path, monkeypatch):
    invalid_file = tmp_path / "invalid.json"
    invalid_file.write_text("invalid json content", encoding="utf-8")
    monkeypatch.setattr(utils, "yaml", None)
    monkeypatch.setattr(sourcecombine.utils, "yaml", None)
    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    with pytest.raises(SystemExit):
        sourcecombine.import_replacements(invalid_file, config)


def test_import_replacements_normalize_rule_edge_cases(tmp_path):
    rules_file = tmp_path / "rules_edge.json"
    data = [
        "not_a_dict",
        {"no_pattern_key": "val"},
        {"search": "valid_search", "replace": "valid_replace"}
    ]
    rules_file.write_text(json.dumps(data), encoding="utf-8")
    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    sourcecombine.import_replacements(rules_file, config)
    assert config["processing"]["regex_replacements"] == [
        {"pattern": "valid_search", "replacement": "valid_replace"}
    ]


def test_import_replacements_none_processing_sections(tmp_path):
    rules_file = tmp_path / "rules.json"
    rules_file.write_text(json.dumps([{"pattern": "p", "replacement": "r"}]), encoding="utf-8")

    config_none_proc = {"processing": None}
    sourcecombine.import_replacements(rules_file, config_none_proc)
    assert config_none_proc["processing"]["regex_replacements"] == [{"pattern": "p", "replacement": "r"}]

    config_none_rules = {
        "processing": {
            "regex_replacements": None,
            "line_regex_replacements": None,
        }
    }
    sourcecombine.import_replacements(rules_file, config_none_rules)
    assert config_none_rules["processing"]["regex_replacements"] == [{"pattern": "p", "replacement": "r"}]
    assert config_none_rules["processing"]["line_regex_replacements"] == []


def test_cli_import_replacements_with_list_replacements(tmp_path, monkeypatch, capsys):
    rules_file = tmp_path / "imported_rules.json"
    rules_file.write_text(
        json.dumps({"regex_replacements": [{"pattern": "FOO", "replacement": "BAR"}]}),
        encoding="utf-8"
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "sourcecombine.py",
            "--import-replacements",
            str(rules_file),
            "--list-replacements",
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.main()

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "FOO" in captured.out
    assert "BAR" in captured.out


def test_update_identity_from_dict_non_dict_input():
    identity = {"project_name": "original"}
    utils._update_identity_from_dict("not_a_dict", identity)
    assert identity == {"project_name": "original"}

    utils._update_identity_from_dict(None, identity)
    assert identity == {"project_name": "original"}
