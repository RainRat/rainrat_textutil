import json
import os
import sys
from pathlib import Path
import pytest

from sourcecombine import main, print_excluded_files


def test_print_excluded_files_plain_text(capsys):
    excluded = [
        {"path": "file1.log", "reason": "excluded", "relative_path": "file1.log"},
        {"path": "image.png", "reason": "binary", "relative_path": "image.png"},
    ]
    print_excluded_files(excluded, query=None, json_format=False)
    captured = capsys.readouterr().out
    assert "EXCLUDED FILES" in captured
    assert "file1.log" in captured
    assert "excluded" in captured
    assert "image.png" in captured
    assert "binary" in captured
    assert "Total: 2 excluded files." in captured


def test_print_excluded_files_filtered_query(capsys):
    excluded = [
        {"path": "file1.log", "reason": "excluded", "relative_path": "file1.log"},
        {"path": "image.png", "reason": "binary", "relative_path": "image.png"},
    ]
    print_excluded_files(excluded, query="png", json_format=False)
    captured = capsys.readouterr().out
    assert "EXCLUDED FILES (FILTERED BY 'png')" in captured
    assert "image.png" in captured
    assert "file1.log" not in captured
    assert "Matching: 1 excluded files." in captured


def test_print_excluded_files_no_matches(capsys):
    excluded = [
        {"path": "file1.log", "reason": "excluded", "relative_path": "file1.log"},
    ]
    print_excluded_files(excluded, query="nonexistent", json_format=False)
    captured = capsys.readouterr().out
    assert "No excluded files matched the filter query 'nonexistent'." in captured
    assert "Matching: 0 excluded files." in captured


def test_print_excluded_files_empty_list(capsys):
    print_excluded_files([], query=None, json_format=False)
    captured = capsys.readouterr().out
    assert "No files were excluded." in captured
    assert "Total: 0 excluded files." in captured


def test_print_excluded_files_json(capsys):
    excluded = [
        {"path": "file1.log", "reason": "excluded", "relative_path": "file1.log"},
        {"path": "image.png", "reason": "binary", "relative_path": "image.png"},
    ]
    print_excluded_files(excluded, query="binary", json_format=True)
    captured = capsys.readouterr().out
    data = json.loads(captured)
    assert data["total"] == 1
    assert len(data["excluded_files"]) == 1
    assert data["excluded_files"][0]["path"] == "image.png"
    assert data["excluded_files"][0]["reason"] == "binary"


def test_cli_list_excluded(tmp_path, monkeypatch, capsys):
    (tmp_path / "valid.py").write_text("print('hello')", encoding="utf-8")
    (tmp_path / "ignore.log").write_text("log data", encoding="utf-8")
    (tmp_path / "skip.tmp").write_text("temp data", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["sourcecombine.py", ".", "-x", "*.log", "-x", "*.tmp", "--list-excluded"])

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0
    captured = capsys.readouterr().out
    assert "EXCLUDED FILES" in captured
    assert "ignore.log" in captured
    assert "skip.tmp" in captured
    assert "excluded" in captured


def test_cli_list_excluded_alias_and_json(tmp_path, monkeypatch, capsys):
    (tmp_path / "valid.py").write_text("print('hello')", encoding="utf-8")
    (tmp_path / "ignore.log").write_text("log data", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["sourcecombine.py", ".", "-x", "*.log", "--list-exc", "--json"])

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0
    captured = capsys.readouterr().out
    data = json.loads(captured)
    assert data["total"] == 1
    assert data["excluded_files"][0]["path"] == "ignore.log"
    assert data["excluded_files"][0]["reason"] == "excluded"
