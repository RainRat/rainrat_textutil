import copy
import json
import pytest
import utils
from sourcecombine import import_replacements, export_replacements


def test_import_replacements_exported_json(tmp_path):
    """Test round-trip export and import of replacements."""
    export_file = tmp_path / "rules.json"

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    config['processing']['regex_replacements'] = [{'pattern': 'FOO', 'replacement': 'BAR'}]
    config['processing']['line_regex_replacements'] = [{'pattern': '^#.*', 'replacement': ''}]

    export_replacements(export_file, config=config)
    assert export_file.exists()

    new_config = copy.deepcopy(utils.DEFAULT_CONFIG)
    import_replacements(export_file, new_config)

    assert new_config['processing']['regex_replacements'] == [{'pattern': 'FOO', 'replacement': 'BAR'}]
    assert new_config['processing']['line_regex_replacements'] == [{'pattern': '^#.*', 'replacement': ''}]


def test_import_replacements_search_replace_keys(tmp_path):
    """Test importing rules with search/replace keys instead of pattern/replacement."""
    rules_file = tmp_path / "alt_rules.json"
    data = {
        "text_replacements": [{"search": "cat", "replace": "dog"}],
        "line_replacements": [{"search": "DEBUG:.*", "replace": None}]
    }
    rules_file.write_text(json.dumps(data), encoding="utf-8")

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    import_replacements(rules_file, config)

    assert config['processing']['regex_replacements'] == [{'pattern': 'cat', 'replacement': 'dog'}]
    assert config['processing']['line_regex_replacements'] == [{'pattern': 'DEBUG:.*', 'replacement': ''}]


def test_import_replacements_json_array(tmp_path):
    """Test importing rules from a JSON array."""
    rules_file = tmp_path / "list_rules.json"
    data = [
        {"pattern": "alpha", "replacement": "beta"},
        {"search": "gamma", "replace": "delta"}
    ]
    rules_file.write_text(json.dumps(data), encoding="utf-8")

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    import_replacements(rules_file, config)

    assert len(config['processing']['regex_replacements']) == 2
    assert config['processing']['regex_replacements'][0] == {'pattern': 'alpha', 'replacement': 'beta'}
    assert config['processing']['regex_replacements'][1] == {'pattern': 'gamma', 'replacement': 'delta'}


def test_import_replacements_yaml_format(tmp_path):
    """Test importing rules from a YAML file."""
    if not utils.yaml:
        pytest.skip("PyYAML not installed")

    yaml_file = tmp_path / "rules.yml"
    yaml_content = """
regex_replacements:
  - pattern: "greeting"
    replacement: "hi"
line_regex_replacements:
  - pattern: "^//.*"
    replacement: ""
"""
    yaml_file.write_text(yaml_content, encoding="utf-8")

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    import_replacements(yaml_file, config)

    assert config['processing']['regex_replacements'] == [{'pattern': 'greeting', 'replacement': 'hi'}]
    assert config['processing']['line_regex_replacements'] == [{'pattern': '^//.*', 'replacement': ''}]


def test_import_replacements_stdin(monkeypatch):
    """Test importing rules from standard input ('-')."""
    data = {
        "regex_rules": [{"pattern": "one", "replacement": "1"}],
        "line_rules": [{"pattern": "two", "replacement": "2"}]
    }
    json_str = json.dumps(data)
    monkeypatch.setattr("sys.stdin", pytest.importorskip("io").StringIO(json_str))

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    import_replacements("-", config)

    assert config['processing']['regex_replacements'] == [{'pattern': 'one', 'replacement': '1'}]
    assert config['processing']['line_regex_replacements'] == [{'pattern': 'two', 'replacement': '2'}]


def test_import_replacements_text_processing(tmp_path):
    """Test that imported rules actually perform replacement during process_content."""
    rules_file = tmp_path / "rules.json"
    data = {
        "regex_replacements": [{"pattern": "foo", "replacement": "bar"}]
    }
    rules_file.write_text(json.dumps(data), encoding="utf-8")

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    import_replacements(rules_file, config)

    processed = utils.process_content("hello foo world", config['processing'])
    assert processed == "hello bar world"


def test_import_replacements_missing_file(tmp_path):
    """Test error handling when the replacements file is missing."""
    missing_file = tmp_path / "nonexistent.json"
    config = copy.deepcopy(utils.DEFAULT_CONFIG)

    with pytest.raises(SystemExit):
        import_replacements(missing_file, config)


def test_import_replacements_invalid_syntax(tmp_path):
    """Test error handling when replacements file has invalid syntax."""
    bad_file = tmp_path / "bad_syntax.json"
    bad_file.write_text("{ this is not valid json or yaml", encoding="utf-8")

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    with pytest.raises(SystemExit):
        import_replacements(bad_file, config)


def test_import_replacements_invalid_regex(tmp_path):
    """Test error handling when an imported replacement pattern is an invalid regex."""
    bad_file = tmp_path / "bad_regex.json"
    data = {
        "regex_replacements": [{"pattern": "[unclosed", "replacement": "x"}]
    }
    bad_file.write_text(json.dumps(data), encoding="utf-8")

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    with pytest.raises(SystemExit):
        import_replacements(bad_file, config)


def test_import_replacements_empty_file_and_none(tmp_path):
    """Test handling of None, empty paths, empty files, and invalid formats."""
    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    assert import_replacements(None, config) is config
    assert import_replacements("", config) is config
    assert import_replacements("path.json", None) is None

    empty_file = tmp_path / "empty.json"
    empty_file.write_text("", encoding="utf-8")
    assert import_replacements(empty_file, config) is config

    invalid_fmt = tmp_path / "number.json"
    invalid_fmt.write_text("12345", encoding="utf-8")
    with pytest.raises(SystemExit):
        import_replacements(invalid_fmt, config)
