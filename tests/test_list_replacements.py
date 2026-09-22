import json
import pytest
from sourcecombine import main, print_replacements


def test_print_replacements_empty(capsys):
    print_replacements(json_format=False)
    captured = capsys.readouterr().out
    assert "ACTIVE SEARCH-AND-REPLACE RULES" in captured
    assert "No active search-and-replace rules configured" in captured


def test_print_replacements_text_and_line(capsys):
    config = {
        "processing": {
            "regex_replacements": [{"pattern": "foo", "replacement": "bar"}],
            "line_regex_replacements": [{"pattern": "import x", "replacement": ""}],
        }
    }
    print_replacements(config=config, json_format=False)
    captured = capsys.readouterr().out
    assert "[Text Replacements (--replace)]" in captured
    assert "Pattern: 'foo' -> Replacement: 'bar'" in captured
    assert "[Line Replacements (--replace-line)]" in captured
    assert "Pattern: 'import x' -> Replacement: ''" in captured


def test_print_replacements_json(capsys):
    config = {
        "processing": {
            "regex_replacements": [{"pattern": "alpha", "replacement": "beta"}],
            "line_regex_replacements": [],
        }
    }
    print_replacements(config=config, json_format=True)
    captured = capsys.readouterr().out
    data = json.loads(captured)
    assert data["total"] == 1
    assert data["regex_replacements"] == [{"pattern": "alpha", "replacement": "beta"}]
    assert data["line_regex_replacements"] == []


def test_print_replacements_query_filter(capsys):
    config = {
        "processing": {
            "regex_replacements": [
                {"pattern": "target_one", "replacement": "1"},
                {"pattern": "other", "replacement": "2"},
            ],
            "line_regex_replacements": [
                {"pattern": "target_line", "replacement": "3"},
            ],
        }
    }
    print_replacements(query="target", config=config, json_format=False)
    captured = capsys.readouterr().out
    assert "FILTERED BY 'target'" in captured
    assert "target_one" in captured
    assert "target_line" in captured
    assert "other" not in captured


def test_print_replacements_query_json(capsys):
    config = {
        "processing": {
            "regex_replacements": [
                {"pattern": "match_me", "replacement": "yes"},
                {"pattern": "ignore_me", "replacement": "no"},
            ],
            "line_regex_replacements": [],
        }
    }
    print_replacements(query="match", config=config, json_format=True)
    captured = capsys.readouterr().out
    data = json.loads(captured)
    assert data["total"] == 1
    assert len(data["regex_replacements"]) == 1
    assert data["regex_replacements"][0]["pattern"] == "match_me"


def test_cli_list_replacements(monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.argv",
        [
            "sourcecombine.py",
            "--replace",
            "hello",
            "world",
            "--replace-line",
            "import old",
            "import new",
            "--list-replacements",
        ],
    )
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 0
    captured = capsys.readouterr().out
    assert "Pattern: 'hello' -> Replacement: 'world'" in captured
    assert "Pattern: 'import old' -> Replacement: 'import new'" in captured


def test_cli_list_rep_alias_json(monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.argv",
        [
            "sourcecombine.py",
            "--replace",
            "foo",
            "bar",
            "--list-rep",
            "--json",
        ],
    )
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 0
    captured = capsys.readouterr().out
    data = json.loads(captured)
    assert data["total"] == 1
    assert data["regex_replacements"][0] == {"pattern": "foo", "replacement": "bar"}


def test_cli_list_rules_alias_query(monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.argv",
        [
            "sourcecombine.py",
            "--replace",
            "apple",
            "fruit",
            "--replace",
            "dog",
            "animal",
            "--list-rules",
            "dog",
        ],
    )
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 0
    captured = capsys.readouterr().out
    assert "dog" in captured
    assert "apple" not in captured


def test_print_replacements_no_match(capsys):
    config = {
        "processing": {
            "regex_replacements": [{"pattern": "apple", "replacement": "fruit"}],
            "line_regex_replacements": [],
        }
    }
    print_replacements(query="nonexistent", config=config, json_format=False)
    captured = capsys.readouterr().out
    assert "No search-and-replace rules matched the filter query 'nonexistent'" in captured


def test_cli_list_replacements_config_target(tmp_path, monkeypatch, capsys):
    cfg_file = tmp_path / "custom.yml"
    cfg_file.write_text("processing:\n  regex_replacements:\n    - pattern: 'abc'\n      replacement: 'xyz'\n")
    monkeypatch.setattr(
        "sys.argv",
        [
            "sourcecombine.py",
            str(cfg_file),
            "--list-replacements",
        ],
    )
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 0
    captured = capsys.readouterr().out
    assert "Pattern: 'abc' -> Replacement: 'xyz'" in captured


def test_cli_list_replacements_auto_detect_default_config(tmp_path, monkeypatch, capsys):
    cfg_file = tmp_path / "sourcecombine.yml"
    cfg_file.write_text("processing:\n  regex_replacements:\n    - pattern: 'auto'\n      replacement: 'detected'\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "sys.argv",
        [
            "sourcecombine.py",
            "--list-replacements",
        ],
    )
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 0
    captured = capsys.readouterr().out
    assert "Pattern: 'auto' -> Replacement: 'detected'" in captured


def test_cli_list_replacements_invalid_config_error(tmp_path, monkeypatch, capsys):
    cfg_file = tmp_path / "invalid.yml"
    cfg_file.write_text("filters: invalid_structure_not_dict\n")
    monkeypatch.setattr(
        "sys.argv",
        [
            "sourcecombine.py",
            "-c",
            str(cfg_file),
            "--list-replacements",
        ],
    )
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 1


def test_cli_list_replacements_none_regex_rules(tmp_path, monkeypatch, capsys):
    cfg_file = tmp_path / "none_rules.yml"
    cfg_file.write_text("processing:\n  regex_replacements: null\n  line_regex_replacements: null\n")
    monkeypatch.setattr(
        "sys.argv",
        [
            "sourcecombine.py",
            "-c",
            str(cfg_file),
            "--replace",
            "one",
            "two",
            "--replace-line",
            "three",
            "four",
            "--list-replacements",
        ],
    )
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 0
    captured = capsys.readouterr().out
    assert "Pattern: 'one' -> Replacement: 'two'" in captured
    assert "Pattern: 'three' -> Replacement: 'four'" in captured
