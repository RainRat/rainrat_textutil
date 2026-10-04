import io
import json
import os
import sys
import pytest
from pathlib import Path

import sourcecombine
import utils


def test_import_ignore_patterns_none_and_empty():
    assert sourcecombine.import_ignore_patterns(None, {}) == {}
    assert sourcecombine.import_ignore_patterns("file.txt", None) is None

    config = {"filters": {"exclusions": {"filenames": []}}}

    # Test empty file
    tmp_empty = Path("test_empty_ignore.txt")
    tmp_empty.write_text("", encoding="utf-8")
    try:
        res = sourcecombine.import_ignore_patterns(str(tmp_empty), config)
        assert res["filters"]["exclusions"]["filenames"] == []
    finally:
        if tmp_empty.exists():
            tmp_empty.unlink()


def test_import_ignore_patterns_missing_file():
    config = {"filters": {"exclusions": {"filenames": []}}}
    with pytest.raises(SystemExit):
        sourcecombine.import_ignore_patterns("non_existent_ignore_file.txt", config)


def test_import_ignore_patterns_plain_text(tmp_path):
    ignore_file = tmp_path / ".customignore"
    ignore_file.write_text("# Comment line\n*.log\n\n  *.tmp  \n# Another comment\nnode_modules/\n", encoding="utf-8")

    config = {"filters": {"exclusions": {"filenames": ["*.bak"]}}}
    res = sourcecombine.import_ignore_patterns(str(ignore_file), config)

    imported = res["filters"]["exclusions"]["filenames"]
    assert "*.bak" in imported
    assert "*.log" in imported
    assert "*.tmp" in imported
    assert "node_modules/" in imported


def test_import_ignore_patterns_json_array(tmp_path):
    ignore_file = tmp_path / "ignore.json"
    ignore_file.write_text(json.dumps(["*.out", "dist/"]), encoding="utf-8")

    config = {"filters": {"exclusions": {"filenames": []}}}
    res = sourcecombine.import_ignore_patterns(str(ignore_file), config)

    imported = res["filters"]["exclusions"]["filenames"]
    assert "*.out" in imported
    assert "dist/" in imported


def test_import_ignore_patterns_json_dict_with_patterns_and_categories(tmp_path):
    ignore_file = tmp_path / "exported_ignore.json"
    data = {
        "patterns": ["*.pyc"],
        "categories": {
            "Custom": ["*.cache", ".env"]
        }
    }
    ignore_file.write_text(json.dumps(data), encoding="utf-8")

    config = {"filters": {"exclusions": {"filenames": []}}}
    res = sourcecombine.import_ignore_patterns(str(ignore_file), config)

    imported = res["filters"]["exclusions"]["filenames"]
    assert "*.pyc" in imported
    assert "*.cache" in imported
    assert ".env" in imported


def test_import_ignore_patterns_stdin(monkeypatch):
    content = "*.iso\n*.dmg\n"
    monkeypatch.setattr(sys, "stdin", io.StringIO(content))

    config = {"filters": {"exclusions": {"filenames": []}}}
    res = sourcecombine.import_ignore_patterns("-", config)

    imported = res["filters"]["exclusions"]["filenames"]
    assert "*.iso" in imported
    assert "*.dmg" in imported


def test_cli_import_ignore_with_list_ignores(tmp_path, monkeypatch, capsys):
    ignore_file = tmp_path / "imported.txt"
    ignore_file.write_text("*.custom_ext\n", encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        ["sourcecombine", "--import-ignore", str(ignore_file), "--list-ignores"]
    )

    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.main()

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "*.custom_ext" in captured.out


def test_cli_import_ignore_alias_and_export_ignore(tmp_path, monkeypatch):
    import_file = tmp_path / "imported_rules.json"
    import_file.write_text(json.dumps(["*.imported_rule"]), encoding="utf-8")

    export_file = tmp_path / "exported_rules.json"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "sourcecombine",
            "--import-ig", str(import_file),
            "--export-ignore", str(export_file),
            "--json"
        ]
    )

    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.main()

    assert exc_info.value.code == 0
    assert export_file.exists()

    data = json.loads(export_file.read_text(encoding="utf-8"))
    assert "*.imported_rule" in data["patterns"]
