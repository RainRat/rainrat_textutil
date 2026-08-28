import json
import pytest
from sourcecombine import main, print_extensions


def test_print_extensions_unfiltered(capsys):
    print_extensions()
    captured = capsys.readouterr().out
    assert "=== SUPPORTED EXTENSIONS & FILENAMES ===" in captured
    assert ".py" in captured
    assert "python" in captured
    assert "Total:" in captured


def test_print_extensions_filtered_matching(capsys):
    print_extensions(query="python")
    captured = capsys.readouterr().out
    assert "FILTERED BY 'python'" in captured
    assert ".py" in captured
    assert "Matching:" in captured


def test_print_extensions_filtered_no_match(capsys):
    print_extensions(query="nonexistentext999")
    captured = capsys.readouterr().out
    assert "FILTERED BY 'nonexistentext999'" in captured
    assert "No extensions or filenames matched the filter query 'nonexistentext999'." in captured
    assert "Matching: 0 extensions and filenames supported." in captured


def test_print_extensions_json(capsys):
    print_extensions(json_format=True)
    captured = capsys.readouterr().out
    data = json.loads(captured)
    assert "extensions" in data
    assert ".py" in data["extensions"]
    assert data["extensions"][".py"] == "python"
    assert data["total"] > 0


def test_print_extensions_json_query(capsys):
    print_extensions(query="py", json_format=True)
    captured = capsys.readouterr().out
    data = json.loads(captured)
    assert "extensions" in data
    assert ".py" in data["extensions"]
    assert data["extensions"][".py"] == "python"
    assert data["total"] > 0


def test_cli_list_extensions(capsys, monkeypatch):
    monkeypatch.setattr("sys.argv", ["sourcecombine.py", "--list-extensions"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0
    captured = capsys.readouterr().out
    assert "=== SUPPORTED EXTENSIONS & FILENAMES ===" in captured
    assert ".py" in captured


def test_cli_list_ext_alias(capsys, monkeypatch):
    monkeypatch.setattr("sys.argv", ["sourcecombine.py", "--list-ext", "python"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0
    captured = capsys.readouterr().out
    assert "FILTERED BY 'python'" in captured
    assert ".py" in captured


def test_cli_list_extensions_json(capsys, monkeypatch):
    monkeypatch.setattr("sys.argv", ["sourcecombine.py", "--list-extensions", "py", "--json"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0
    captured = capsys.readouterr().out
    data = json.loads(captured)
    assert "extensions" in data
    assert ".py" in data["extensions"]
    assert data["extensions"][".py"] == "python"
    assert data["total"] == len(data["extensions"])

