import sys; import os; from pathlib import Path; sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

import json
import logging
from sourcecombine import extract_files
import pytest

def test_extract_xml_malformed_tokens(tmp_path, caplog):
    """Verify that malformed tokens in XML don't crash extraction."""
    content = """<repository>
<file path="bad_tokens.py" tokens="not_a_number">
print("bad")
</file>
<file path="good.py" tokens="10">
print("good")
</file>
</repository>"""

    # This should not raise ValueError
    stats = extract_files(content, str(tmp_path), dry_run=True)
    assert stats['total_discovered'] >= 1
    assert "good.py" in [f[2] for f in stats['top_files']]

def test_extract_xml_malformed_lines(tmp_path):
    """Verify that malformed lines in XML don't crash extraction."""
    content = """<repository>
<file path="bad_lines.py" lines="invalid">
print("bad")
</file>
</repository>"""
    extract_files(content, str(tmp_path), dry_run=True)

def test_extract_xml_malformed_date(tmp_path):
    """Verify that malformed modified date in XML doesn't crash extraction."""
    content = """<repository>
<file path="bad_date.py" modified="not-a-date">
print("bad")
</file>
</repository>"""
    extract_files(content, str(tmp_path), dry_run=True)

def test_extract_xml_malformed_size(tmp_path):
    """Verify that malformed size in XML doesn't crash extraction."""
    content = """<repository>
<file path="bad_size.py" size="invalid-size">
print("bad")
</file>
</repository>"""
    extract_files(content, str(tmp_path), dry_run=True)

def test_extract_json_malformed_metadata(tmp_path):
    """Verify that malformed metadata in JSON doesn't crash extraction."""
    data = [
        {
            "path": "bad_meta.py",
            "content": "print('bad')",
            "tokens": "not_int",
            "size_bytes": "not_int",
            "lines": "not_int"
        }
    ]
    content = json.dumps(data)
    extract_files(content, str(tmp_path), dry_run=True)

def test_extract_jsonl_malformed_metadata(tmp_path):
    """Verify that malformed metadata in JSONL doesn't crash extraction."""
    content = '{"path": "bad.py", "content": "bad", "tokens": "invalid"}\n{"path": "good.py", "content": "good"}'
    extract_files(content, str(tmp_path), dry_run=True)
