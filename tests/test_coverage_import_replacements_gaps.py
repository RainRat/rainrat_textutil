import copy
import json
import pytest
import sourcecombine
import utils


def test_import_replacements_oserror(tmp_path, monkeypatch):
    """Test import_replacements handling OSError when opening file."""
    test_file = tmp_path / "rules.json"
    test_file.write_text("{}", encoding="utf-8")

    def mock_open(*args, **kwargs):
        raise OSError("Permission denied")

    monkeypatch.setattr("builtins.open", mock_open)
    config = copy.deepcopy(utils.DEFAULT_CONFIG)

    with pytest.raises(SystemExit):
        sourcecombine.import_replacements(test_file, config)


def test_import_replacements_yaml_none_json_fail(tmp_path, monkeypatch):
    """Test import_replacements when utils.yaml is None and JSON fails."""
    bad_file = tmp_path / "invalid.json"
    bad_file.write_text("{ invalid json }", encoding="utf-8")

    monkeypatch.setattr(utils, "yaml", None)
    config = copy.deepcopy(utils.DEFAULT_CONFIG)

    with pytest.raises(SystemExit):
        sourcecombine.import_replacements(bad_file, config)


def test_import_replacements_rule_normalization_edge_cases(tmp_path):
    """Test _normalize_rule when rule is non-dict or lacks search/pattern keys."""
    rules_file = tmp_path / "rules.json"
    data = {
        "text_replacements": [
            "not_a_dict",
            {"other_key": "val"},
            {"pattern": "valid", "replacement": "ok"}
        ]
    }
    rules_file.write_text(json.dumps(data), encoding="utf-8")

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    sourcecombine.import_replacements(rules_file, config)

    assert len(config['processing']['regex_replacements']) == 1
    assert config['processing']['regex_replacements'][0] == {'pattern': 'valid', 'replacement': 'ok'}


def test_import_replacements_none_config_sections(tmp_path):
    """Test import_replacements when config processing or rules lists are None."""
    rules_file = tmp_path / "rules.json"
    data = {
        "text_replacements": [{"pattern": "foo", "replacement": "bar"}],
        "line_replacements": [{"pattern": "^#.*", "replacement": ""}]
    }
    rules_file.write_text(json.dumps(data), encoding="utf-8")

    config = {'processing': None}
    sourcecombine.import_replacements(rules_file, config)

    assert config['processing']['regex_replacements'] == [{'pattern': 'foo', 'replacement': 'bar'}]
    assert config['processing']['line_regex_replacements'] == [{'pattern': '^#.*', 'replacement': ''}]

    config2 = {
        'processing': {
            'regex_replacements': None,
            'line_regex_replacements': None
        }
    }
    sourcecombine.import_replacements(rules_file, config2)

    assert config2['processing']['regex_replacements'] == [{'pattern': 'foo', 'replacement': 'bar'}]
    assert config2['processing']['line_regex_replacements'] == [{'pattern': '^#.*', 'replacement': ''}]


def test_cli_list_replacements_with_import_replacements(tmp_path, monkeypatch, capsys):
    """Test CLI --list-replacements combined with --import-replacements."""
    rules_file = tmp_path / "rules.json"
    rules_file.write_text(json.dumps({
        "text_replacements": [{"pattern": "CLI_FOO", "replacement": "CLI_BAR"}]
    }), encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        [
            "sourcecombine.py",
            "--list-replacements",
            "--import-replacements",
            str(rules_file),
        ]
    )

    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.main()

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "CLI_FOO" in captured.out


def test_update_identity_from_dict_non_dict():
    """Test utils._update_identity_from_dict with non-dict input."""
    identity = {"project_name": "original"}
    utils._update_identity_from_dict(None, identity)
    assert identity == {"project_name": "original"}

    utils._update_identity_from_dict("not a dict", identity)
    assert identity == {"project_name": "original"}
