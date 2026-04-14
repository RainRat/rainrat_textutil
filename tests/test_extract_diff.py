import sys
import os
from pathlib import Path

# Ensure repo root is on path
sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

import json
from sourcecombine import extract_files

def test_extract_show_diff_existing_file(tmp_path, capsys):
    output_dir = tmp_path / "extracted"
    output_dir.mkdir()

    existing_file = output_dir / "test.txt"
    existing_file.write_text("old content\n", encoding="utf-8")

    data = [{"path": "test.txt", "content": "new content\n"}]
    content = json.dumps(data)

    extract_files(content, str(output_dir), show_diff=True)

    captured = capsys.readouterr()
    assert "--- a/test.txt" in captured.err
    assert "+++ b/test.txt" in captured.err
    assert "-old content" in captured.err
    assert "+new content" in captured.err

    assert existing_file.read_text(encoding="utf-8") == "new content\n"

def test_extract_show_diff_no_change(tmp_path, capsys):
    output_dir = tmp_path / "extracted"
    output_dir.mkdir()

    existing_file = output_dir / "test.txt"
    existing_file.write_text("same content\n", encoding="utf-8")

    data = [{"path": "test.txt", "content": "same content\n"}]
    content = json.dumps(data)

    extract_files(content, str(output_dir), show_diff=True)

    captured = capsys.readouterr()
    assert "--- a/test.txt" not in captured.err
    assert "+++ b/test.txt" not in captured.err

def test_extract_show_diff_new_file(tmp_path, capsys):
    output_dir = tmp_path / "extracted"
    output_dir.mkdir()

    data = [{"path": "new_file.txt", "content": "new content\n"}]
    content = json.dumps(data)

    extract_files(content, str(output_dir), show_diff=True)

    captured = capsys.readouterr()
    assert "--- a/new_file.txt" not in captured.err
    assert (output_dir / "new_file.txt").exists()

def test_extract_show_diff_dry_run(tmp_path, capsys):
    output_dir = tmp_path / "extracted"
    output_dir.mkdir()

    existing_file = output_dir / "test.txt"
    existing_file.write_text("old content\n", encoding="utf-8")

    data = [{"path": "test.txt", "content": "new content\n"}]
    content = json.dumps(data)

    extract_files(content, str(output_dir), show_diff=True, dry_run=True)

    captured = capsys.readouterr()
    assert "--- a/test.txt" in captured.err
    assert "-old content" in captured.err
    assert "+new content" in captured.err

    assert existing_file.read_text(encoding="utf-8") == "old content\n"
