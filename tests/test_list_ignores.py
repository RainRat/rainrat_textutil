import json
import pytest
from pathlib import Path
from sourcecombine import main, print_ignore_patterns


def test_print_ignore_patterns_no_files(capsys):
    print_ignore_patterns()
    captured = capsys.readouterr().out
    assert "=== ACTIVE IGNORE PATTERNS ===" in captured
    assert "No active ignore patterns found." in captured
    assert "Total: 0" in captured


def test_print_ignore_patterns_unfiltered(capsys, tmp_path):
    ignore_file = tmp_path / ".sourcecombineignore"
    ignore_file.write_text("*.log\nnode_modules/\n# comment\n", encoding="utf-8")

    config = {"search": {"ignore_files": [str(ignore_file)]}}
    print_ignore_patterns(config=config)
    captured = capsys.readouterr().out

    assert "=== ACTIVE IGNORE PATTERNS ===" in captured
    assert f"File: {ignore_file}" in captured
    assert "*.log" in captured
    assert "node_modules/" in captured
    assert "Total: 2" in captured


def test_print_ignore_patterns_query_matching(capsys, tmp_path):
    ignore_file = tmp_path / ".sourcecombineignore"
    ignore_file.write_text("*.log\nnode_modules/\n*.tmp\n", encoding="utf-8")

    config = {"search": {"ignore_files": [str(ignore_file)]}}
    print_ignore_patterns(query="log", config=config)
    captured = capsys.readouterr().out

    assert "FILTERED BY 'log'" in captured
    assert "*.log" in captured
    assert "node_modules/" not in captured
    assert "Matching: 1" in captured


def test_print_ignore_patterns_query_no_match(capsys, tmp_path):
    ignore_file = tmp_path / ".sourcecombineignore"
    ignore_file.write_text("*.log\nnode_modules/\n", encoding="utf-8")

    config = {"search": {"ignore_files": [str(ignore_file)]}}
    print_ignore_patterns(query="nonexistentpattern999", config=config)
    captured = capsys.readouterr().out

    assert "FILTERED BY 'nonexistentpattern999'" in captured
    assert "No ignore patterns matched the filter query 'nonexistentpattern999'." in captured
    assert "Matching: 0" in captured


def test_print_ignore_patterns_json(capsys, tmp_path):
    ignore_file = tmp_path / ".sourcecombineignore"
    ignore_file.write_text("*.log\nnode_modules/\n", encoding="utf-8")

    config = {"search": {"ignore_files": [str(ignore_file)]}}
    print_ignore_patterns(json_format=True, config=config)
    captured = capsys.readouterr().out

    data = json.loads(captured)
    assert "ignore_files" in data
    assert len(data["ignore_files"]) == 1
    assert data["ignore_files"][0]["file"] == str(ignore_file)
    assert data["ignore_files"][0]["patterns"] == ["*.log", "node_modules/"]
    assert data["total_patterns"] == 2


def test_print_ignore_patterns_json_query(capsys, tmp_path):
    ignore_file = tmp_path / ".sourcecombineignore"
    ignore_file.write_text("*.log\nnode_modules/\n", encoding="utf-8")

    config = {"search": {"ignore_files": [str(ignore_file)]}}
    print_ignore_patterns(query="node", json_format=True, config=config)
    captured = capsys.readouterr().out

    data = json.loads(captured)
    assert "ignore_files" in data
    assert len(data["ignore_files"]) == 1
    assert data["ignore_files"][0]["patterns"] == ["node_modules/"]
    assert data["total_patterns"] == 1


def test_cli_list_ignores(capsys, monkeypatch, tmp_path):
    ignore_file = tmp_path / "custom.ignore"
    ignore_file.write_text("*.bak\nbuild/\n", encoding="utf-8")

    monkeypatch.setattr("sys.argv", ["sourcecombine.py", "--ignore-file", str(ignore_file), "--list-ignores"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0
    captured = capsys.readouterr().out
    assert "=== ACTIVE IGNORE PATTERNS ===" in captured
    assert "*.bak" in captured
    assert "build/" in captured


def test_cli_list_ig_alias(capsys, monkeypatch, tmp_path):
    ignore_file = tmp_path / "custom.ignore"
    ignore_file.write_text("*.bak\nbuild/\n", encoding="utf-8")

    monkeypatch.setattr("sys.argv", ["sourcecombine.py", "--ignore-file", str(ignore_file), "--list-ig", "bak"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0
    captured = capsys.readouterr().out
    assert "FILTERED BY 'bak'" in captured
    assert "*.bak" in captured
    assert "build/" not in captured


def test_cli_list_ignores_json(capsys, monkeypatch, tmp_path):
    ignore_file = tmp_path / "custom.ignore"
    ignore_file.write_text("*.bak\nbuild/\n", encoding="utf-8")

    monkeypatch.setattr("sys.argv", ["sourcecombine.py", "--ignore-file", str(ignore_file), "--list-ignores", "--json"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0
    captured = capsys.readouterr().out
    data = json.loads(captured)
    assert data["total_patterns"] == 2
