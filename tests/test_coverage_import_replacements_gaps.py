import copy
import json
import pytest
import utils
from sourcecombine import import_replacements, main


def test_main_list_replacements_with_import_replacements(tmp_path, monkeypatch):
    rules_file = tmp_path / "rules.json"
    rules_file.write_text(
        json.dumps({"regex_replacements": [{"pattern": "foo", "replacement": "bar"}]}),
        encoding="utf-8",
    )

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


def test_import_replacements_open_oserror(tmp_path, monkeypatch):
    rules_file = tmp_path / "rules.json"
    rules_file.write_text("[]", encoding="utf-8")

    orig_open = open

    def mock_open(file, *args, **kwargs):
        if str(file) == str(rules_file):
            raise OSError("Permission denied")
        return orig_open(file, *args, **kwargs)

    monkeypatch.setattr("builtins.open", mock_open)

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    with pytest.raises(SystemExit):
        import_replacements(rules_file, config)


def test_import_replacements_no_yaml_json_parse_failure(tmp_path, monkeypatch):
    rules_file = tmp_path / "rules.json"
    rules_file.write_text("{ invalid json }", encoding="utf-8")

    monkeypatch.setattr(utils, "yaml", None)

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    with pytest.raises(SystemExit):
        import_replacements(rules_file, config)


def test_import_replacements_normalize_rule_edge_cases(tmp_path):
    rules_file = tmp_path / "rules.json"
    data = [
        123,
        "not_a_dict",
        {"invalid_key": "val"},
        {"pattern": "hello", "replacement": "world"},
    ]
    rules_file.write_text(json.dumps(data), encoding="utf-8")

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    import_replacements(rules_file, config)

    assert config['processing']['regex_replacements'] == [{'pattern': 'hello', 'replacement': 'world'}]


def test_import_replacements_none_config_sections(tmp_path):
    rules_file = tmp_path / "rules.json"
    data = {"regex_replacements": [{"pattern": "a", "replacement": "b"}]}
    rules_file.write_text(json.dumps(data), encoding="utf-8")

    config_a = {'processing': None}
    import_replacements(rules_file, config_a)
    assert config_a['processing']['regex_replacements'] == [{'pattern': 'a', 'replacement': 'b'}]

    config_b = {'processing': {'regex_replacements': None, 'line_regex_replacements': None}}
    import_replacements(rules_file, config_b)
    assert config_b['processing']['regex_replacements'] == [{'pattern': 'a', 'replacement': 'b'}]
    assert config_b['processing']['line_regex_replacements'] == []


def test_update_identity_from_dict_non_dict():
    identity = {}
    utils._update_identity_from_dict("not_a_dict", identity)
    utils._update_identity_from_dict(None, identity)
    utils._update_identity_from_dict(123, identity)
    assert identity == {}
