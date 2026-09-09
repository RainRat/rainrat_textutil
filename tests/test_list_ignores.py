import json
from sourcecombine import print_ignore_patterns


def test_print_ignore_patterns_basic(tmp_path, capsys):
    ignore_file = tmp_path / ".sourcecombineignore"
    ignore_file.write_text("*.log\nnode_modules/\n# comment\n", encoding="utf-8")

    print_ignore_patterns(ignore_files_override=[str(ignore_file)])
    captured = capsys.readouterr().out

    assert "ACTIVE IGNORE PATTERNS" in captured
    assert "*.log" in captured
    assert "node_modules/" in captured
    assert "2 active ignore patterns loaded." in captured


def test_print_ignore_patterns_query_filter(tmp_path, capsys):
    ignore_file = tmp_path / ".sourcecombineignore"
    ignore_file.write_text("*.log\n*.tmp\nnode_modules/\n", encoding="utf-8")

    print_ignore_patterns(query="log", ignore_files_override=[str(ignore_file)])
    captured = capsys.readouterr().out

    assert "*.log" in captured
    assert "*.tmp" not in captured
    assert "Matching: 1" in captured


def test_print_ignore_patterns_json_format(tmp_path, capsys):
    ignore_file = tmp_path / ".sourcecombineignore"
    ignore_file.write_text("*.log\nbuild/\n", encoding="utf-8")

    print_ignore_patterns(json_format=True, ignore_files_override=[str(ignore_file)])
    captured = capsys.readouterr().out

    data = json.loads(captured)
    assert data["total"] == 2
    assert str(ignore_file) in data["ignore_sources"]
    assert data["ignore_sources"][str(ignore_file)] == ["*.log", "build/"]


def test_print_ignore_patterns_json_query_filter(tmp_path, capsys):
    ignore_file = tmp_path / ".sourcecombineignore"
    ignore_file.write_text("*.log\nbuild/\n", encoding="utf-8")

    print_ignore_patterns(query="build", json_format=True, ignore_files_override=[str(ignore_file)])
    captured = capsys.readouterr().out

    data = json.loads(captured)
    assert data["total"] == 1
    assert data["ignore_sources"][str(ignore_file)] == ["build/"]


def test_print_ignore_patterns_no_files(capsys, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    print_ignore_patterns()
    captured = capsys.readouterr().out

    assert "No active ignore files found." in captured
    assert "Total: 0 active ignore patterns loaded." in captured


def test_print_ignore_patterns_no_query_matches(tmp_path, capsys):
    ignore_file = tmp_path / ".sourcecombineignore"
    ignore_file.write_text("*.log\nbuild/\n", encoding="utf-8")

    print_ignore_patterns(query="nonexistent", ignore_files_override=[str(ignore_file)])
    captured = capsys.readouterr().out

    assert "No ignore patterns matched the filter query 'nonexistent'." in captured
    assert "Matching: 0" in captured
