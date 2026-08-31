import json
import pytest
from sourcecombine import main, print_formats


def test_print_formats_unfiltered(capsys):
    print_formats()
    captured = capsys.readouterr().out
    assert "=== SUPPORTED OUTPUT FORMATS ===" in captured
    assert "markdown" in captured


def test_cli_list_fmt_alias(capsys, monkeypatch):
    monkeypatch.setattr("sys.argv", ["sourcecombine.py", "--list-fmt"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0
    captured = capsys.readouterr().out
    assert "=== SUPPORTED OUTPUT FORMATS ===" in captured
    assert "markdown" in captured
    assert "md" in captured
    assert "json" in captured
    assert "Total: 7" in captured


def test_print_formats_filtered_matching(capsys):
    print_formats(query="markdown")
    captured = capsys.readouterr().out
    assert "FILTERED BY 'markdown'" in captured
    assert "markdown" in captured
    assert "Matching: 1" in captured


def test_print_formats_filtered_alias(capsys):
    print_formats(query="md")
    captured = capsys.readouterr().out
    assert "FILTERED BY 'md'" in captured
    assert "markdown" in captured
    assert "Matching: 1" in captured


def test_print_formats_filtered_no_match(capsys):
    print_formats(query="nonexistentformat999")
    captured = capsys.readouterr().out
    assert "FILTERED BY 'nonexistentformat999'" in captured
    assert "No output formats matched the filter query 'nonexistentformat999'." in captured
    assert "Matching: 0 output formats supported." in captured


def test_print_formats_json(capsys):
    print_formats(json_format=True)
    captured = capsys.readouterr().out
    data = json.loads(captured)
    assert "formats" in data
    assert "markdown" in data["formats"]
    assert "md" in data["formats"]["markdown"]["aliases"]
    assert data["total"] == 7


def test_print_formats_json_query(capsys):
    print_formats(query="csv", json_format=True)
    captured = capsys.readouterr().out
    data = json.loads(captured)
    assert "formats" in data
    assert "csv" in data["formats"]
    assert data["total"] == 1


def test_cli_list_formats(capsys, monkeypatch):
    monkeypatch.setattr("sys.argv", ["sourcecombine.py", "--list-formats"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0
    captured = capsys.readouterr().out
    assert "=== SUPPORTED OUTPUT FORMATS ===" in captured
    assert "markdown" in captured


def test_cli_list_formats_query(capsys, monkeypatch):
    monkeypatch.setattr("sys.argv", ["sourcecombine.py", "--list-formats", "json"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0
    captured = capsys.readouterr().out
    assert "FILTERED BY 'json'" in captured
    assert "json" in captured


def test_cli_list_formats_json(capsys, monkeypatch):
    monkeypatch.setattr("sys.argv", ["sourcecombine.py", "--list-formats", "--json"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0
    captured = capsys.readouterr().out
    data = json.loads(captured)
    assert "formats" in data
    assert "text" in data["formats"]
    assert data["total"] == 7
