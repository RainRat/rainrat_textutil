import io
import json
import sys
from pathlib import Path
import pytest

from sourcecombine import import_replacements, export_replacements, InvalidConfigError, main


def test_import_replacements_none_config():
    """Test that import_replacements raises InvalidConfigError when config is None."""
    with pytest.raises(InvalidConfigError, match="A target configuration dictionary must be provided"):
        import_replacements("rules.json", config=None)


def test_import_replacements_no_source_path():
    """Test that import_replacements raises InvalidConfigError when source_path is empty."""
    config = {"processing": {}}
    with pytest.raises(InvalidConfigError, match="No source file specified"):
        import_replacements("", config=config)


def test_import_replacements_file_not_found(tmp_path):
    """Test that import_replacements raises InvalidConfigError when file does not exist."""
    config = {"processing": {}}
    non_existent = tmp_path / "missing.json"
    with pytest.raises(InvalidConfigError, match="Replacements rule file not found"):
        import_replacements(str(non_existent), config=config)


def test_import_replacements_empty_file(tmp_path, caplog):
    """Test that import_replacements logs warning and returns config unchanged for an empty file."""
    config = {"processing": {}}
    empty_file = tmp_path / "empty.json"
    empty_file.write_text("", encoding="utf-8")

    result = import_replacements(str(empty_file), config=config)
    assert result == {"processing": {}}
    assert "Replacements file" in caplog.text and "is empty" in caplog.text


def test_import_replacements_invalid_json(tmp_path):
    """Test that import_replacements raises InvalidConfigError for malformed JSON/YAML."""
    config = {"processing": {}}
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("{bad json syntax", encoding="utf-8")

    with pytest.raises(InvalidConfigError, match="Could not parse replacements rule file"):
        import_replacements(str(bad_file), config=config)


def test_import_replacements_invalid_top_level_structure(tmp_path):
    """Test that import_replacements raises InvalidConfigError when top-level is not a dict or list."""
    config = {"processing": {}}
    bad_file = tmp_path / "number.json"
    bad_file.write_text("12345", encoding="utf-8")

    with pytest.raises(InvalidConfigError, match="Invalid format in replacements rule file"):
        import_replacements(str(bad_file), config=config)


def test_import_replacements_dict_format(tmp_path):
    """Test importing rules from a JSON dict structure."""
    config = {"processing": {}}
    rule_file = tmp_path / "rules.json"
    rule_data = {
        "regex_replacements": [
            {"pattern": "foo", "replacement": "bar"},
            {"find": "hello", "replace": "world"}
        ],
        "line_regex_replacements": [
            {"pattern": "^#.*", "replacement": ""}
        ]
    }
    rule_file.write_text(json.dumps(rule_data), encoding="utf-8")

    res = import_replacements(str(rule_file), config=config)
    proc = res["processing"]
    assert len(proc["regex_replacements"]) == 2
    assert proc["regex_replacements"][0] == {"pattern": "foo", "replacement": "bar"}
    assert proc["regex_replacements"][1] == {"pattern": "hello", "replacement": "world"}
    assert len(proc["line_regex_replacements"]) == 1
    assert proc["line_regex_replacements"][0] == {"pattern": "^#.*", "replacement": ""}


def test_import_replacements_list_format(tmp_path):
    """Test importing rules from a JSON list array structure."""
    config = {"processing": {}}
    rule_file = tmp_path / "rules_list.json"
    rule_data = [
        {"pattern": "alpha", "replacement": "beta"},
        {"pattern": "^DEBUG.*", "replacement": "", "line": True}
    ]
    rule_file.write_text(json.dumps(rule_data), encoding="utf-8")

    res = import_replacements(str(rule_file), config=config)
    proc = res["processing"]
    assert len(proc["regex_replacements"]) == 1
    assert proc["regex_replacements"][0] == {"pattern": "alpha", "replacement": "beta"}
    assert len(proc["line_regex_replacements"]) == 1
    assert proc["line_regex_replacements"][0] == {"pattern": "^DEBUG.*", "replacement": ""}


def test_import_replacements_yaml_format(tmp_path):
    """Test importing rules from a YAML file."""
    config = {"processing": {}}
    yaml_file = tmp_path / "rules.yml"
    yaml_file.write_text(
        "regex_replacements:\n"
        "  - pattern: 'v1'\n"
        "    replacement: 'v2'\n"
        "line_regex_replacements:\n"
        "  - pattern: '^//.*'\n"
        "    replacement: ''\n",
        encoding="utf-8"
    )

    res = import_replacements(str(yaml_file), config=config)
    proc = res["processing"]
    assert proc["regex_replacements"] == [{"pattern": "v1", "replacement": "v2"}]
    assert proc["line_regex_replacements"] == [{"pattern": "^//.*", "replacement": ""}]


def test_import_replacements_stdin(monkeypatch):
    """Test importing rules from standard input (-)."""
    config = {"processing": {}}
    rule_data = {
        "regex_replacements": [
            {"pattern": "stdin_find", "replacement": "stdin_replace"}
        ]
    }
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(rule_data)))

    res = import_replacements("-", config=config)
    proc = res["processing"]
    assert proc["regex_replacements"] == [{"pattern": "stdin_find", "replacement": "stdin_replace"}]


def test_export_import_roundtrip(tmp_path):
    """Test exporting active replacements and re-importing them into a clean configuration."""
    initial_config = {
        "processing": {
            "regex_replacements": [{"pattern": "cat", "replacement": "dog"}],
            "line_regex_replacements": [{"pattern": "^NOTE:", "replacement": "INFO:"}]
        }
    }
    export_file = tmp_path / "exported.json"
    export_replacements(str(export_file), config=initial_config)

    new_config = {"processing": {}}
    import_replacements(str(export_file), config=new_config)

    assert new_config["processing"]["regex_replacements"] == [{"pattern": "cat", "replacement": "dog"}]
    assert new_config["processing"]["line_regex_replacements"] == [{"pattern": "^NOTE:", "replacement": "INFO:"}]


def test_cli_import_replacements(tmp_path, monkeypatch):
    """Test CLI execution with --import-replacements."""
    test_dir = tmp_path / "src"
    test_dir.mkdir()
    sample_file = test_dir / "sample.txt"
    sample_file.write_text("Hello OLD_WORD World!", encoding="utf-8")

    rules_file = tmp_path / "rules.json"
    rules_file.write_text(json.dumps({
        "regex_replacements": [{"pattern": "OLD_WORD", "replacement": "NEW_WORD"}]
    }), encoding="utf-8")

    out_file = tmp_path / "output.txt"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "sourcecombine.py",
            str(test_dir),
            "--import-replacements",
            str(rules_file),
            "--output",
            str(out_file),
        ],
    )

    main()

    assert out_file.exists()
    assert "Hello NEW_WORD World!" in out_file.read_text(encoding="utf-8")


def test_cli_import_rep_alias(tmp_path, monkeypatch):
    """Test CLI execution with --import-rep alias."""
    test_dir = tmp_path / "src"
    test_dir.mkdir()
    sample_file = test_dir / "sample.txt"
    sample_file.write_text("FOO_BAR", encoding="utf-8")

    rules_file = tmp_path / "rules.json"
    rules_file.write_text(json.dumps({
        "regex_replacements": [{"pattern": "FOO_BAR", "replacement": "BAZ"}]
    }), encoding="utf-8")

    out_file = tmp_path / "output.txt"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "sourcecombine.py",
            str(test_dir),
            "--import-rep",
            str(rules_file),
            "--output",
            str(out_file),
        ],
    )

    main()

    assert out_file.exists()
    assert "BAZ" in out_file.read_text(encoding="utf-8")


def test_cli_import_replacements_conflict_files_from(tmp_path, monkeypatch, caplog):
    """Test CLI error when using --import-replacements and --files-from together."""
    rules_file = tmp_path / "rules.json"
    rules_file.write_text("{}", encoding="utf-8")
    files_from = tmp_path / "files.txt"
    files_from.write_text("", encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "sourcecombine.py",
            "--files-from",
            str(files_from),
            "--import-replacements",
            str(rules_file),
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 1
    assert "You cannot use --import-replacements and --files-from at the same time." in caplog.text
