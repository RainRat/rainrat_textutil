import json
import pytest
from pathlib import Path
import sourcecombine


def test_print_ignore_patterns_empty(capsys):
    """Test print_ignore_patterns when no ignore file exists."""
    sourcecombine.print_ignore_patterns(config={"search": {"ignore_files": []}})
    captured = capsys.readouterr()
    assert "No ignore files found or specified." in captured.out
    assert "Total: 0 patterns across 0 ignore file(s)" in captured.out


def test_print_ignore_patterns_terminal(tmp_path, capsys):
    """Test plain text terminal output for print_ignore_patterns with ignore files."""
    ignore_file = tmp_path / ".sourcecombineignore"
    ignore_file.write_text("# Comment\n*.tmp\n/build/\nnode_modules\n", encoding="utf-8")

    config = {"search": {"ignore_files": [str(ignore_file)]}}

    sourcecombine.print_ignore_patterns(config=config)
    captured = capsys.readouterr()

    assert "ACTIVE IGNORE PATTERNS" in captured.out
    assert str(ignore_file) in captured.out
    assert "*.tmp" in captured.out
    assert "/build/" in captured.out
    assert "node_modules" in captured.out
    assert "Total: 3 patterns across 1 ignore file(s)" in captured.out


def test_print_ignore_patterns_filter_query(tmp_path, capsys):
    """Test QUERY filtering for print_ignore_patterns."""
    ignore_file = tmp_path / ".sourcecombineignore"
    ignore_file.write_text("*.tmp\n*.log\n/dist/\n", encoding="utf-8")

    config = {"search": {"ignore_files": [str(ignore_file)]}}

    # Filter matching 'tmp'
    sourcecombine.print_ignore_patterns(query="tmp", config=config)
    captured = capsys.readouterr()

    assert "FILTERED BY 'tmp'" in captured.out
    assert "*.tmp" in captured.out
    assert "*.log" not in captured.out
    assert "Matching: 1 patterns across 1 ignore file(s)" in captured.out

    # Filter with no matches
    sourcecombine.print_ignore_patterns(query="nonexistent", config=config)
    captured_no_match = capsys.readouterr()

    assert "No ignore patterns matched the filter query 'nonexistent'." in captured_no_match.out
    assert "Matching: 0 patterns across 0 ignore file(s)" in captured_no_match.out


def test_print_ignore_patterns_json(tmp_path, capsys):
    """Test machine-readable JSON output for print_ignore_patterns."""
    ignore_file = tmp_path / "custom.ignore"
    ignore_file.write_text("*.bak\nvenv/\n", encoding="utf-8")

    config = {"search": {"ignore_files": [str(ignore_file)]}}

    sourcecombine.print_ignore_patterns(json_format=True, config=config)
    captured = capsys.readouterr()

    data = json.loads(captured.out)
    assert data["total_patterns"] == 2
    assert data["total_files"] == 1
    assert str(ignore_file) in data["ignore_files"]
    assert data["ignore_files"][str(ignore_file)] == ["*.bak", "venv/"]


def test_cli_list_ignores(tmp_path, monkeypatch, capsys):
    """Test CLI execution with --list-ignores and --list-ig alias."""
    ignore_file = tmp_path / ".sourcecombineignore"
    ignore_file.write_text("*.cache\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)

    # Test full flag
    monkeypatch.setattr("sys.argv", ["sourcecombine.py", "--list-ignores", "--ignore-file", str(ignore_file)])
    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.main()
    assert exc_info.value.code == 0

    captured = capsys.readouterr()
    assert "ACTIVE IGNORE PATTERNS" in captured.out
    assert "*.cache" in captured.out

    # Test alias with json
    monkeypatch.setattr("sys.argv", ["sourcecombine.py", "--list-ig", "cache", "--ignore-file", str(ignore_file), "--json"])
    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.main()
    assert exc_info.value.code == 0

    captured_json = capsys.readouterr()
    data = json.loads(captured_json.out)
    assert data["total_patterns"] == 1
    assert data["total_files"] == 1
