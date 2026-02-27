import json
import os
import sys
from pathlib import Path
import pytest
from sourcecombine import find_and_combine_files, main, extract_files
from utils import DEFAULT_CONFIG

def test_jsonl_max_size_placeholder(tmp_path):
    # Gap: sourcecombine.py:924
    (tmp_path / "large.txt").write_text("very large content")

    config = DEFAULT_CONFIG.copy()
    config['search'] = {'root_folders': [str(tmp_path)]}
    config['filters'] = {'max_size_bytes': 5} # "very large content" is more than 5 bytes
    config['output'] = {'max_size_placeholder': "SKIPPED: {{FILENAME}}"}

    output_path = tmp_path / "output.jsonl"
    find_and_combine_files(config, str(output_path), output_format='jsonl')

    content = output_path.read_text()
    # Each entry in JSONL should end with a newline
    assert content.endswith('\n')
    data = json.loads(content.strip())
    assert data['path'] == "large.txt"
    assert data['content'] == "SKIPPED: large.txt"

def test_smart_extension_jsonl(tmp_path, monkeypatch):
    # Gap: sourcecombine.py:2300
    (tmp_path / "file.txt").write_text("hello")

    cwd = Path.cwd()
    os.chdir(tmp_path)
    try:
        # Use a non-default filename by format
        monkeypatch.setattr("sys.argv", ["sourcecombine.py", "--format", "jsonl"])
        main()
        # Default filename for jsonl should be combined_files.jsonl
        assert Path("combined_files.jsonl").exists()
    finally:
        os.chdir(cwd)

def test_extract_jsonl_edge_cases(tmp_path):
    # Gaps: sourcecombine.py:2432, 2437-2438

    # 2432: empty line in JSONL
    content_with_empty_line = '{"path": "a.txt", "content": "a"}\n\n{"path": "b.txt", "content": "b"}'
    extract_dir = tmp_path / "extract1"
    extract_files(content_with_empty_line, str(extract_dir), source_name="test1.jsonl")
    assert (extract_dir / "a.txt").read_text() == "a"
    assert (extract_dir / "b.txt").read_text() == "b"

    # 2437-2438: invalid entry (not a dict with path/content)
    # Now it skips malformed lines instead of aborting.
    content_invalid_entry = '{"path": "a.txt", "content": "a"}\n{"not_path": "invalid"}\n{"path": "b.txt", "content": "b"}'
    extract_dir = tmp_path / "extract2"
    extract_files(content_invalid_entry, str(extract_dir), source_name="test2.jsonl")
    assert (extract_dir / "a.txt").read_text() == "a"
    assert (extract_dir / "b.txt").read_text() == "b"
