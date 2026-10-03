import copy
import json
import pytest
import utils
from sourcecombine import import_replacements, main


def test_import_replacements_os_error(tmp_path, monkeypatch):
    """Test OSError handling when reading a replacements file."""
    rule_file = tmp_path / "rules.json"
    rule_file.write_text("{}", encoding="utf-8")

    def mock_open(*args, **kwargs):
        raise OSError("Disk read error")

    monkeypatch.setattr("builtins.open", mock_open)
    config = copy.deepcopy(utils.DEFAULT_CONFIG)

    with pytest.raises(SystemExit):
        import_replacements(rule_file, config)


def test_import_replacements_json_parse_error_no_yaml(tmp_path, monkeypatch):
    """Test JSON parsing error handling when utils.yaml is None."""
    rule_file = tmp_path / "bad.json"
    rule_file.write_text("{ invalid json", encoding="utf-8")

    monkeypatch.setattr(utils, "yaml", None)
    config = copy.deepcopy(utils.DEFAULT_CONFIG)

    with pytest.raises(SystemExit):
        import_replacements(rule_file, config)


def test_import_replacements_rule_normalization_edge_cases(tmp_path):
    """Test rule normalization edge cases such as non-dict items or missing search/pattern keys."""
    rule_file = tmp_path / "edge_rules.json"
    data = [
        123,
        "not a dict",
        None,
        {"pattern": None, "replacement": "test"},
        {"no_pattern_or_search_key": "val"},
        {"pattern": "valid_pattern", "replacement": "valid_replacement"},
    ]
    rule_file.write_text(json.dumps(data), encoding="utf-8")

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    import_replacements(rule_file, config)

    assert config['processing']['regex_replacements'] == [{'pattern': 'valid_pattern', 'replacement': 'valid_replacement'}]


def test_import_replacements_none_config_sections(tmp_path):
    """Test handling of config structures where processing sections are explicitly set to None."""
    rule_file = tmp_path / "rules.json"
    data = {
        "regex_replacements": [{"pattern": "foo", "replacement": "bar"}],
        "line_replacements": [{"pattern": "line", "replacement": "sub"}]
    }
    rule_file.write_text(json.dumps(data), encoding="utf-8")

    config = {'processing': None}
    import_replacements(rule_file, config)

    assert config['processing']['regex_replacements'] == [{'pattern': 'foo', 'replacement': 'bar'}]
    assert config['processing']['line_regex_replacements'] == [{'pattern': 'line', 'replacement': 'sub'}]

    config = {
        'processing': {
            'regex_replacements': None,
            'line_regex_replacements': None
        }
    }
    import_replacements(rule_file, config)

    assert config['processing']['regex_replacements'] == [{'pattern': 'foo', 'replacement': 'bar'}]
    assert config['processing']['line_regex_replacements'] == [{'pattern': 'line', 'replacement': 'sub'}]


def test_cli_list_replacements_with_import_replacements(tmp_path, monkeypatch):
    """Test CLI --list-replacements combined with --import-replacements."""
    rules_file = tmp_path / "rules.json"
    rules_file.write_text(json.dumps({
        "regex_replacements": [{"pattern": "test_pat", "replacement": "test_rep"}]
    }), encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        [
            "sourcecombine.py",
            "--list-replacements",
            "--import-replacements",
            str(rules_file),
            "--json"
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0


def test_update_identity_from_dict_non_dict_input():
    """Test utils._update_identity_from_dict when input is not a dictionary."""
    identity = {"project_name": "original"}
    utils._update_identity_from_dict("not_a_dict", identity)
    assert identity == {"project_name": "original"}

    utils._update_identity_from_dict(None, identity)
    assert identity == {"project_name": "original"}
