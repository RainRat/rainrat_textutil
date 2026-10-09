import json
import pytest
import utils
from sourcecombine import import_replacements, main


def test_update_identity_from_dict_non_dict():
    identity = {"project_name": "Initial"}
    utils._update_identity_from_dict("invalid_input", identity)
    assert identity["project_name"] == "Initial"


def test_import_replacements_read_oserror(tmp_path, monkeypatch):
    test_file = tmp_path / "unreadable.json"
    test_file.write_text('{"regex_replacements": []}', encoding="utf-8")

    def mock_open(*args, **kwargs):
        raise OSError("Permission denied")

    monkeypatch.setattr("builtins.open", mock_open)
    config = {}
    with pytest.raises(SystemExit):
        import_replacements(test_file, config)


def test_import_replacements_invalid_json_no_yaml(tmp_path, monkeypatch):
    test_file = tmp_path / "invalid.json"
    test_file.write_text("invalid json content", encoding="utf-8")

    monkeypatch.setattr(utils, "yaml", None)
    config = {}
    with pytest.raises(SystemExit):
        import_replacements(test_file, config)


def test_import_replacements_non_dict_rule_and_missing_pattern(tmp_path):
    test_file = tmp_path / "rules.json"
    data = [
        123,
        {"no_pattern_key": "val"},
        {"pattern": "valid", "replacement": "ok"}
    ]
    test_file.write_text(json.dumps(data), encoding="utf-8")

    config = {}
    import_replacements(test_file, config)
    assert config["processing"]["regex_replacements"] == [{"pattern": "valid", "replacement": "ok"}]


def test_import_replacements_none_config_sections(tmp_path):
    test_file = tmp_path / "rules.json"
    data = {"regex_replacements": [{"pattern": "a", "replacement": "b"}]}
    test_file.write_text(json.dumps(data), encoding="utf-8")

    config_none_proc = {"processing": None}
    import_replacements(test_file, config_none_proc)
    assert config_none_proc["processing"]["regex_replacements"] == [{"pattern": "a", "replacement": "b"}]

    config_none_rules = {"processing": {"regex_replacements": None, "line_regex_replacements": None}}
    import_replacements(test_file, config_none_rules)
    assert config_none_rules["processing"]["regex_replacements"] == [{"pattern": "a", "replacement": "b"}]


def test_cli_list_replacements_with_import_replacements(tmp_path, monkeypatch):
    rules_file = tmp_path / "rules.json"
    rules_file.write_text(json.dumps({
        "regex_replacements": [{"pattern": "FOO", "replacement": "BAR"}]
    }), encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        [
            "sourcecombine.py",
            "--list-replacements",
            "--import-replacements",
            str(rules_file),
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0
