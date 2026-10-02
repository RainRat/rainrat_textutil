import copy
import json
import pytest
import utils
from sourcecombine import import_replacements, main


def test_import_replacements_oserror_read(tmp_path, monkeypatch):
    """Test error handling when reading replacements file raises OSError."""
    rules_file = tmp_path / "unreadable.json"
    rules_file.write_text("{}", encoding="utf-8")

    def mock_open(*args, **kwargs):
        raise OSError("Permission denied")

    monkeypatch.setattr("builtins.open", mock_open)
    config = copy.deepcopy(utils.DEFAULT_CONFIG)

    with pytest.raises(SystemExit):
        import_replacements(rules_file, config)


def test_import_replacements_yaml_none(tmp_path, monkeypatch):
    """Test JSON parse error fallback when utils.yaml is None."""
    bad_file = tmp_path / "invalid.json"
    bad_file.write_text("{ invalid json", encoding="utf-8")

    monkeypatch.setattr(utils, "yaml", None)
    config = copy.deepcopy(utils.DEFAULT_CONFIG)

    with pytest.raises(SystemExit):
        import_replacements(bad_file, config)


def test_import_replacements_normalize_rule_edge_cases(tmp_path):
    """Test _normalize_rule with non-dict items and pattern: None."""
    rules_file = tmp_path / "edge_rules.json"
    data = [
        "not_a_dict",
        123,
        {"pattern": None, "replacement": "test"},
        {"pattern": "valid", "replacement": "ok"}
    ]
    rules_file.write_text(json.dumps(data), encoding="utf-8")

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    import_replacements(rules_file, config)

    assert config['processing']['regex_replacements'] == [{'pattern': 'valid', 'replacement': 'ok'}]


def test_import_replacements_none_config_sections(tmp_path):
    """Test import_replacements when config['processing'] or replacement lists are explicitly None."""
    rules_file = tmp_path / "rules.json"
    rules_file.write_text(json.dumps([{"pattern": "a", "replacement": "b"}]), encoding="utf-8")

    config = {'processing': None}
    import_replacements(rules_file, config)
    assert config['processing']['regex_replacements'] == [{'pattern': 'a', 'replacement': 'b'}]

    config = {'processing': {'regex_replacements': None, 'line_regex_replacements': None}}
    import_replacements(rules_file, config)
    assert config['processing']['regex_replacements'] == [{'pattern': 'a', 'replacement': 'b'}]


def test_cli_list_replacements_with_import(tmp_path, monkeypatch, capsys):
    """Test CLI option --list-replacements combined with --import-replacements."""
    rules_file = tmp_path / "rules.json"
    rules_file.write_text(json.dumps({
        "regex_replacements": [{"pattern": "FOO", "replacement": "BAR"}]
    }), encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        [
            "sourcecombine.py",
            str(tmp_path),
            "--import-replacements",
            str(rules_file),
            "--list-replacements"
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0
    captured = capsys.readouterr().out
    assert "FOO" in captured
    assert "BAR" in captured


def test_update_identity_from_dict_non_dict():
    """Test utils._update_identity_from_dict when non-dict data is passed."""
    identity = {}
    utils._update_identity_from_dict("not a dict", identity)
    assert identity == {}
