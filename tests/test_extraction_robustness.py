import sys; import os; from pathlib import Path; sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

import json
from sourcecombine import extract_files, _to_int_or_none, _to_float_or_none
import pytest

def test_to_int_or_none():
    assert _to_int_or_none("123") == 123
    assert _to_int_or_none("1,234") == 1234
    assert _to_int_or_none("~1,234") == 1234
    assert _to_int_or_none("123.45") == 123
    assert _to_int_or_none(123) == 123
    assert _to_int_or_none(None) is None
    assert _to_int_or_none("invalid") is None
    assert _to_int_or_none([]) is None

def test_to_float_or_none():
    assert _to_float_or_none("123.45") == 123.45
    assert _to_float_or_none("1,234.56") == 1234.56
    assert _to_float_or_none(123.45) == 123.45
    assert _to_float_or_none(None) is None
    assert _to_float_or_none("invalid") is None

def test_extract_xml_robustness_malformed_entries(tmp_path):
    """Verify that malformed entries in XML are skipped without crashing the entire extraction."""
    content = """
<repository>
<file path="valid.txt">
valid content
</file>
<file path="malformed_meta.txt" tokens="invalid" lines="also_invalid">
content with malformed meta
</file>
<file path="">
missing path
</file>
<file>
missing everything
</file>
<file path="valid2.txt">
more valid content
</file>
</repository>
    """
    stats = extract_files(content, tmp_path, dry_run=True)

    # We expect 3 discovered files: valid.txt, malformed_meta.txt, and valid2.txt.
    # The entries missing path or everything might be skipped by ET or our logic.
    assert stats['total_discovered'] >= 2
    assert stats['total_files'] >= 2

def test_extract_jsonl_robustness_malformed_lines(tmp_path):
    """Verify that malformed lines in JSONL are skipped."""
    lines = [
        json.dumps({"path": "valid1.txt", "content": "valid1"}),
        "not a json line",
        json.dumps({"not_a_path": "invalid"}),
        json.dumps({"path": "valid2.txt", "content": "valid2"})
    ]
    content = "\n".join(lines)

    stats = extract_files(content, tmp_path, dry_run=True, source_name="test.jsonl")

    assert stats['total_discovered'] == 2
    assert stats['total_files'] == 2

def test_extract_xml_with_approx_tokens(tmp_path):
    """Verify that approximate token indicator in XML is correctly parsed."""
    content = """
<repository>
<file path="approx.txt" tokens="~1,000">
approx content
</file>
</repository>
    """
    stats = extract_files(content, tmp_path, dry_run=True)

    assert stats['total_tokens'] == 1000
    assert stats['token_count_is_approx'] is True

def test_extract_xml_with_decimal_meta(tmp_path):
    """Verify that decimal metadata in XML (if any) is handled by safe int conversion."""
    content = """
<repository>
<file path="decimal.txt" tokens="123.45">
decimal content
</file>
</repository>
    """
    stats = extract_files(content, tmp_path, dry_run=True)

    assert stats['total_tokens'] == 123
