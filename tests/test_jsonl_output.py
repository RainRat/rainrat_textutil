import json
import os
import sys
from pathlib import Path
import pytest
from sourcecombine import find_and_combine_files, main
from utils import DEFAULT_CONFIG

def test_jsonl_output(tmp_path):
    # Create dummy files
    (tmp_path / "file1.txt").write_text("content1")
    (tmp_path / "file2.txt").write_text("content2")

    config = DEFAULT_CONFIG.copy()
    config['search'] = {'root_folders': [str(tmp_path)]}
    output_path = tmp_path / "output.jsonl"

    stats = find_and_combine_files(config, str(output_path), output_format='jsonl')

    content = output_path.read_text()
    lines = content.strip().split('\n')
    assert len(lines) == 2

    data1 = json.loads(lines[0])
    data2 = json.loads(lines[1])

    assert data1['path'] == "file1.txt"
    assert data1['content'] == "content1"
    assert data2['path'] == "file2.txt"
    assert data2['content'] == "content2"

def test_jsonl_extraction(tmp_path):
    jsonl_content = (
        '{"path": "src/a.py", "content": "print(1)"}\n'
        '{"path": "src/b.py", "content": "print(2)"}\n'
    )
    archive_path = tmp_path / "archive.jsonl"
    archive_path.write_text(jsonl_content)

    from sourcecombine import extract_files
    extract_dir = tmp_path / "extracted"
    extract_files(jsonl_content, str(extract_dir), source_name="test.jsonl")

    assert (extract_dir / "src/a.py").read_text() == "print(1)"
    assert (extract_dir / "src/b.py").read_text() == "print(2)"

def test_auto_detection(tmp_path, monkeypatch):
    (tmp_path / "test.txt").write_text("hello")

    # We need to mock sys.argv and call main()
    output_md = tmp_path / "output.md"
    monkeypatch.setattr("sys.argv", ["sourcecombine.py", str(tmp_path), "-o", str(output_md)])

    # main() doesn't call sys.exit() on success
    main()

    content = output_md.read_text()
    assert "## test.txt" in content
    assert "```txt" in content

def test_auto_detection_jsonl(tmp_path, monkeypatch):
    (tmp_path / "test.txt").write_text("hello")
    output_jsonl = tmp_path / "output.jsonl"
    monkeypatch.setattr("sys.argv", ["sourcecombine.py", str(tmp_path), "-o", str(output_jsonl)])

    main()

    content = output_jsonl.read_text()
    data = json.loads(content.strip())
    assert data['path'] == "test.txt"
    assert data['content'] == "hello"

def test_format_override_auto_detection(tmp_path, monkeypatch):
    # If -j is used with -o out.md, it should be JSON
    (tmp_path / "test.txt").write_text("hello")
    output_md = tmp_path / "output.md"
    monkeypatch.setattr("sys.argv", ["sourcecombine.py", str(tmp_path), "-o", str(output_md), "-j"])

    main()

    content = output_md.read_text()
    # It should be a JSON list
    assert content.startswith('[')
    data = json.loads(content)
    assert data[0]['path'] == "test.txt"
