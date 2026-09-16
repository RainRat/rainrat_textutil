import sys, os; from pathlib import Path; sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))
import copy
import json
import pytest
from unittest.mock import patch
import sourcecombine


def test_print_replacements_empty(capsys, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    sourcecombine.print_replacements()
    captured = capsys.readouterr()
    assert "ACTIVE REPLACEMENT RULES" in captured.out
    assert "No replacement rules are currently configured." in captured.out
    assert "Total: 0 active replacement rules configured." in captured.out


def test_print_replacements_with_rules(capsys, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config = copy.deepcopy(sourcecombine.utils.DEFAULT_CONFIG)
    config['processing']['regex_replacements'] = [
        {'pattern': 'foo', 'replacement': 'bar'}
    ]
    config['processing']['line_regex_replacements'] = [
        {'pattern': '^#.*$', 'replacement': ''}
    ]

    sourcecombine.print_replacements(config=config)
    captured = capsys.readouterr()
    assert "ACTIVE REPLACEMENT RULES" in captured.out
    assert "Text Replacement Rules (Config / CLI):" in captured.out
    assert "'foo' -> 'bar'" in captured.out
    assert "Line Replacement Rules (Config / CLI):" in captured.out
    assert "'^#.*$' -> ''" in captured.out
    assert "Total: 2 active replacement rules configured." in captured.out


def test_print_replacements_query_filter(capsys, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config = copy.deepcopy(sourcecombine.utils.DEFAULT_CONFIG)
    config['processing']['regex_replacements'] = [
        {'pattern': 'foo', 'replacement': 'bar'},
        {'pattern': 'hello', 'replacement': 'world'}
    ]
    config['processing']['line_regex_replacements'] = [
        {'pattern': '^#.*$', 'replacement': ''}
    ]

    sourcecombine.print_replacements(query="foo", config=config)
    captured = capsys.readouterr()
    assert "FILTERED BY 'foo'" in captured.out
    assert "'foo' -> 'bar'" in captured.out
    assert "'hello' -> 'world'" not in captured.out
    assert "'^#.*$'" not in captured.out
    assert "Matching: 1" in captured.out


def test_print_replacements_query_no_match(capsys, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config = copy.deepcopy(sourcecombine.utils.DEFAULT_CONFIG)
    config['processing']['regex_replacements'] = [
        {'pattern': 'foo', 'replacement': 'bar'}
    ]

    sourcecombine.print_replacements(query="nonexistent_pattern", config=config)
    captured = capsys.readouterr()
    assert "No replacement rules matched the filter query 'nonexistent_pattern'" in captured.out
    assert "Matching: 0" in captured.out


def test_print_replacements_json(capsys, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config = copy.deepcopy(sourcecombine.utils.DEFAULT_CONFIG)
    config['processing']['regex_replacements'] = [
        {'pattern': 'foo', 'replacement': 'bar'}
    ]
    config['processing']['line_regex_replacements'] = [
        {'pattern': '^//.*$', 'replacement': ''}
    ]

    sourcecombine.print_replacements(json_format=True, config=config)
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "regex_replacements" in data
    assert "line_regex_replacements" in data
    assert len(data["regex_replacements"]) == 1
    assert data["regex_replacements"][0]["pattern"] == "foo"
    assert len(data["line_regex_replacements"]) == 1
    assert data["line_regex_replacements"][0]["pattern"] == "^//.*$"
    assert data["total"] == 2


def test_cli_list_replacements_main(capsys, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with patch("sys.argv", ["sourcecombine", "--list-replacements"]):
        with pytest.raises(SystemExit) as exc:
            sourcecombine.main()
        assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "ACTIVE REPLACEMENT RULES" in captured.out


def test_cli_list_rep_alias_main(capsys, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with patch("sys.argv", ["sourcecombine", "--list-rep"]):
        with pytest.raises(SystemExit) as exc:
            sourcecombine.main()
        assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "ACTIVE REPLACEMENT RULES" in captured.out


def test_cli_list_rules_alias_main(capsys, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with patch("sys.argv", ["sourcecombine", "--list-rules"]):
        with pytest.raises(SystemExit) as exc:
            sourcecombine.main()
        assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "ACTIVE REPLACEMENT RULES" in captured.out


def test_cli_list_replacements_with_replace_flags(capsys, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with patch("sys.argv", ["sourcecombine", "--list-replacements", "--replace", "TODO", "FIXED", "--replace-line", "^#.*$", ""]):
        with pytest.raises(SystemExit) as exc:
            sourcecombine.main()
        assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "ACTIVE REPLACEMENT RULES" in captured.out
    assert "'TODO' -> 'FIXED'" in captured.out
    assert "'^#.*$' -> ''" in captured.out


def test_cli_list_replacements_json(capsys, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with patch("sys.argv", ["sourcecombine", "--list-replacements", "--replace", "alpha", "beta", "--json"]):
        with pytest.raises(SystemExit) as exc:
            sourcecombine.main()
        assert exc.value.code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["total"] == 1
    assert data["regex_replacements"][0]["pattern"] == "alpha"
    assert data["regex_replacements"][0]["replacement"] == "beta"
