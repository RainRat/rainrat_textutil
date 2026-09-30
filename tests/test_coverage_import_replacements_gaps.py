import json
import pytest
import utils
from sourcecombine import import_replacements, main


def test_import_replacements_oserror(tmp_path, monkeypatch):
    test_file = tmp_path / "rules.json"
    test_file.write_text("{}", encoding="utf-8")

    def mock_open(*args, **kwargs):
        raise OSError("Permission denied")

    monkeypatch.setattr("builtins.open", mock_open)
    config = {"processing": {}}
    with pytest.raises(SystemExit):
        import_replacements(test_file, config)


def test_import_replacements_json_fail_no_yaml(tmp_path, monkeypatch):
    test_file = tmp_path / "bad.json"
    test_file.write_text("{invalid json", encoding="utf-8")

    monkeypatch.setattr(utils, "yaml", None)
    config = {"processing": {}}
    with pytest.raises(SystemExit):
        import_replacements(test_file, config)


def test_import_replacements_normalize_rule_gaps(tmp_path):
    test_file = tmp_path / "rules.json"
    data = [
        123,
        "string_rule",
        {"other_key": "no_pattern_or_search"},
        {"pattern": "valid_pat", "replacement": "valid_rep"}
    ]
    test_file.write_text(json.dumps(data), encoding="utf-8")

    config = {"processing": {}}
    import_replacements(test_file, config)
    assert config["processing"]["regex_replacements"] == [
        {"pattern": "valid_pat", "replacement": "valid_rep"}
    ]


def test_import_replacements_none_processing_dict(tmp_path):
    test_file = tmp_path / "rules.json"
    data = {
        "text_replacements": [{"pattern": "pat1", "replacement": "rep1"}],
        "line_replacements": [{"pattern": "pat2", "replacement": "rep2"}]
    }
    test_file.write_text(json.dumps(data), encoding="utf-8")

    config = {
        "processing": None
    }
    import_replacements(test_file, config)
    assert config["processing"]["regex_replacements"] == [
        {"pattern": "pat1", "replacement": "rep1"}
    ]
    assert config["processing"]["line_regex_replacements"] == [
        {"pattern": "pat2", "replacement": "rep2"}
    ]


def test_import_replacements_none_rule_lists(tmp_path):
    test_file = tmp_path / "rules.json"
    data = {
        "text_replacements": [{"pattern": "pat1", "replacement": "rep1"}],
        "line_replacements": [{"pattern": "pat2", "replacement": "rep2"}]
    }
    test_file.write_text(json.dumps(data), encoding="utf-8")

    config = {
        "processing": {
            "regex_replacements": None,
            "line_regex_replacements": None
        }
    }
    import_replacements(test_file, config)
    assert config["processing"]["regex_replacements"] == [
        {"pattern": "pat1", "replacement": "rep1"}
    ]
    assert config["processing"]["line_regex_replacements"] == [
        {"pattern": "pat2", "replacement": "rep2"}
    ]


def test_import_replacements_with_list_replacements_cli(tmp_path, monkeypatch, capsys):
    rules_file = tmp_path / "rules.json"
    rules_file.write_text(json.dumps({
        "regex_replacements": [{"pattern": "pat_cli", "replacement": "rep_cli"}]
    }), encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        [
            "sourcecombine.py",
            "--list-replacements",
            "--import-replacements",
            str(rules_file)
        ]
    )

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "pat_cli" in captured.out


def test_update_identity_from_dict_non_dict():
    identity = {}
    utils._update_identity_from_dict(None, identity)
    assert identity == {}

    utils._update_identity_from_dict("not a dict", identity)
    assert identity == {}
