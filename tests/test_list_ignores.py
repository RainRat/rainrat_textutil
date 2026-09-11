import sys, os; from pathlib import Path; sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))
import json
import pytest
from unittest.mock import patch
import sourcecombine


def test_print_ignore_patterns_text(capsys, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ignore_file = tmp_path / ".sourcecombineignore"
    ignore_file.write_text("*.log\ntmp/*\n")

    sourcecombine.print_ignore_patterns()
    captured = capsys.readouterr()
    assert "ACTIVE IGNORE PATTERNS" in captured.out
    assert "Ignore File (.sourcecombineignore)" in captured.out
    assert "*.log" in captured.out
    assert "tmp/*" in captured.out
    assert "Excluded Filenames (Config)" in captured.out
    assert "Excluded Folders (Config)" in captured.out


def test_print_ignore_patterns_filter_matching(capsys, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ignore_file = tmp_path / ".sourcecombineignore"
    ignore_file.write_text("*.log\ntmp/*\n")

    sourcecombine.print_ignore_patterns(query="log")
    captured = capsys.readouterr()
    assert "FILTERED BY 'log'" in captured.out
    assert "*.log" in captured.out
    assert "tmp/*" not in captured.out


def test_print_ignore_patterns_filter_no_matches(capsys, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ignore_file = tmp_path / ".sourcecombineignore"
    ignore_file.write_text("*.log\n")

    sourcecombine.print_ignore_patterns(query="xyz_nonexistent_pattern")
    captured = capsys.readouterr()
    assert "No ignore patterns matched the filter query 'xyz_nonexistent_pattern'" in captured.out
    assert "Matching: 0 active ignore patterns supported." in captured.out


def test_print_ignore_patterns_json(capsys, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ignore_file = tmp_path / ".sourcecombineignore"
    ignore_file.write_text("*.log\n")

    sourcecombine.print_ignore_patterns(json_format=True)
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "ignore_patterns" in data
    assert "Ignore File (.sourcecombineignore)" in data["ignore_patterns"]
    assert "*.log" in data["ignore_patterns"]["Ignore File (.sourcecombineignore)"]


def test_cli_list_ignores_main(capsys, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ignore_file = tmp_path / ".sourcecombineignore"
    ignore_file.write_text("build_output/*\n")

    with patch("sys.argv", ["sourcecombine", "--list-ignores"]):
        with pytest.raises(SystemExit) as exc:
            sourcecombine.main()
        assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "ACTIVE IGNORE PATTERNS" in captured.out
    assert "build_output/*" in captured.out


def test_cli_list_ig_alias_main(capsys, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ignore_file = tmp_path / ".sourcecombineignore"
    ignore_file.write_text("build_output/*\n")

    with patch("sys.argv", ["sourcecombine", "--list-ig"]):
        with pytest.raises(SystemExit) as exc:
            sourcecombine.main()
        assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "ACTIVE IGNORE PATTERNS" in captured.out
    assert "build_output/*" in captured.out


def test_cli_list_ignores_json_main(capsys, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ignore_file = tmp_path / ".sourcecombineignore"
    ignore_file.write_text("build_output/*\n")

    with patch("sys.argv", ["sourcecombine", "--list-ignores", "--json"]):
        with pytest.raises(SystemExit) as exc:
            sourcecombine.main()
        assert exc.value.code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "ignore_patterns" in data
    assert "Ignore File (.sourcecombineignore)" in data["ignore_patterns"]
