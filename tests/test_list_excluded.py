import json
import os
import sys
import pytest
from pathlib import Path

from sourcecombine import main, find_and_combine_files, DEFAULT_CONFIG


def test_list_excluded_plain_text(tmp_path, monkeypatch, capsys):
    f1 = tmp_path / "include_me.txt"
    f1.write_text("Hello world")
    f2 = tmp_path / "exclude_me.tmp"
    f2.write_text("Temp file")

    test_args = ["sourcecombine.py", str(tmp_path), "--list-excluded", "--exclude-file", "*.tmp"]
    monkeypatch.setattr(sys, "argv", test_args)

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "EXCLUDED FILES" in captured.out or "exclude_me.tmp" in captured.out
    assert "exclude_me.tmp" in captured.out
    assert "(excluded)" in captured.out


def test_list_excluded_json(tmp_path, monkeypatch, capsys):
    f1 = tmp_path / "file1.py"
    f1.write_text("print('hello')")
    f2 = tmp_path / "file2.log"
    f2.write_text("Log entry")

    test_args = ["sourcecombine.py", str(tmp_path), "--list-excluded", "--exclude-extension", "log", "--json"]
    monkeypatch.setattr(sys, "argv", test_args)

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["total_excluded"] >= 1
    paths = [item["path"] for item in data["excluded_files"]]
    assert "file2.log" in paths or any(p.endswith("file2.log") for p in paths)


def test_list_exc_alias(tmp_path, monkeypatch, capsys):
    f1 = tmp_path / "skip.bak"
    f1.write_text("Backup file")

    test_args = ["sourcecombine.py", str(tmp_path), "--list-exc", "--exclude-extension", "bak"]
    monkeypatch.setattr(sys, "argv", test_args)

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "skip.bak" in captured.out


def test_list_excluded_various_reasons(tmp_path, capsys):
    # Binary file
    bin_file = tmp_path / "image.png"
    bin_file.write_bytes(b"\x00\x01\x02\x03\x04\x05\x06\x07")

    # Text file matching grep filter
    txt_file = tmp_path / "hello.txt"
    txt_file.write_text("NO_MATCH_HERE")

    config = {
        'search': {'root_folders': [str(tmp_path)]},
        'filters': {
            'skip_binary': True,
            'grep': 'MATCH_THIS',
        },
        'output': {}
    }

    stats = find_and_combine_files(config, None, list_excluded=True, json_format=True)
    assert 'excluded_files' in stats
    reasons = {item['path']: item['reason'] for item in stats['excluded_files']}
    assert "image.png" in reasons
    assert reasons["image.png"] == "binary"
    assert "hello.txt" in reasons
    assert reasons["hello.txt"] == "grep_mismatch"


def test_list_excluded_zero_excluded(tmp_path, capsys):
    f1 = tmp_path / "data.txt"
    f1.write_text("Clean data")

    config = {
        'search': {'root_folders': [str(tmp_path)]},
        'filters': {},
        'output': {}
    }

    stats = find_and_combine_files(config, None, list_excluded=True, json_format=False)
    captured = capsys.readouterr()
    assert "No files were excluded." in captured.out
