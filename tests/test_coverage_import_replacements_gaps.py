import copy
import json
import pytest
import utils
from sourcecombine import import_replacements, main


def test_cli_list_replacements_with_import_replacements(tmp_path, monkeypatch, capsys):
    """Test CLI --list-replacements combined with --import-replacements."""
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
    captured = capsys.readouterr()
    assert "FOO" in captured.out


def test_import_replacements_os_error(tmp_path, monkeypatch):
    """Test import_replacements handling OSError when reading rule file."""
    bad_file = tmp_path / "unreadable.json"
    bad_file.write_text("{}", encoding="utf-8")

    def mock_open(*args, **kwargs):
        raise OSError("Permission denied")

    monkeypatch.setattr("builtins.open", mock_open)

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    with pytest.raises(SystemExit) as exc_info:
        import_replacements(bad_file, config)

    assert exc_info.value.code == 1


def test_import_replacements_no_yaml_parse_error(tmp_path, monkeypatch):
    """Test import_replacements when utils.yaml is None and JSON parsing fails."""
    bad_file = tmp_path / "invalid.json"
    bad_file.write_text("invalid json content", encoding="utf-8")

    monkeypatch.setattr(utils, "yaml", None)

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    with pytest.raises(SystemExit) as exc_info:
        import_replacements(bad_file, config)

    assert exc_info.value.code == 1


def test_import_replacements_normalize_rule_edge_cases(tmp_path):
    """Test import_replacements rule normalization with non-dict elements and missing pattern keys."""
    rules_file = tmp_path / "edge_rules.json"
    data = [
        "not a dict rule",
        {"no_pattern_or_search": "value"},
        {"pattern": "VALID", "replacement": "OK"}
    ]
    rules_file.write_text(json.dumps(data), encoding="utf-8")

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    import_replacements(rules_file, config)

    assert len(config['processing']['regex_replacements']) == 1
    assert config['processing']['regex_replacements'][0] == {'pattern': 'VALID', 'replacement': 'OK'}


def test_import_replacements_none_config_sections(tmp_path):
    """Test import_replacements when processing or replacement lists in config are None."""
    rules_file = tmp_path / "rules.json"
    data = {
        "text_replacements": [{"pattern": "A", "replacement": "B"}],
        "line_replacements": [{"pattern": "C", "replacement": "D"}]
    }
    rules_file.write_text(json.dumps(data), encoding="utf-8")

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    config['processing'] = None

    import_replacements(rules_file, config)
    assert config['processing']['regex_replacements'] == [{'pattern': 'A', 'replacement': 'B'}]
    assert config['processing']['line_regex_replacements'] == [{'pattern': 'C', 'replacement': 'D'}]

    config2 = copy.deepcopy(utils.DEFAULT_CONFIG)
    config2['processing']['regex_replacements'] = None
    config2['processing']['line_regex_replacements'] = None

    import_replacements(rules_file, config2)
    assert config2['processing']['regex_replacements'] == [{'pattern': 'A', 'replacement': 'B'}]
    assert config2['processing']['line_regex_replacements'] == [{'pattern': 'C', 'replacement': 'D'}]


def test_update_identity_from_dict_non_dict():
    """Test utils._update_identity_from_dict with non-dict input."""
    identity = {}
    utils._update_identity_from_dict(None, identity)
    assert identity == {}

    utils._update_identity_from_dict("not a dict", identity)
    assert identity == {}
