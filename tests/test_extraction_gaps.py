import sys; import os; from pathlib import Path; sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))
import json
import logging
from sourcecombine import extract_files, _parse_combined_content

def test_extract_text_format_coverage(tmp_path):
    """Test extraction from SourceCombine default text format to cover branch in _parse_combined_content."""
    output_dir = tmp_path / "extracted"
    content = "--- file.txt ---\nHello\n--- end file.txt ---"

    stats = extract_files(content, str(output_dir))

    assert (output_dir / "file.txt").read_text(encoding="utf-8").strip() == "Hello"
    assert stats['total_files'] == 1

def test_extract_xml_malformed_entry_logged(tmp_path, caplog):
    """Test that malformed XML file entries are skipped and logged instead of crashing."""
    output_dir = tmp_path / "extracted"
    # The first file entry has an invalid 'modified' date format which should trigger the exception
    content = """<repository>
<file path="bad.txt" modified="invalid-date">
content
</file>
<file path="good.txt">
good content
</file>
</repository>"""

    with caplog.at_level(logging.DEBUG):
        stats = extract_files(content, str(output_dir))

    assert (output_dir / "good.txt").read_text(encoding="utf-8").strip() == "good content"
    assert not (output_dir / "bad.txt").exists()
    assert stats['total_files'] == 1
    assert "Skipping malformed XML file entry" in caplog.text

def test_parse_combined_content_json_none_metadata():
    """Test that _parse_combined_content handles None values for metadata in JSON."""
    content = json.dumps([{
        "path": "test.txt",
        "content": "hello",
        "tokens": None,
        "size_bytes": None,
        "lines": None
    }])

    files = _parse_combined_content(content)
    assert len(files) == 1
    path, file_content, meta = files[0]
    assert meta['tokens'] is None
    assert meta['size'] is None
    assert meta['lines'] is None

def test_extract_files_with_none_metadata(tmp_path):
    """Test that extract_files handles None values for metadata without TypeError."""
    output_dir = tmp_path / "extracted"
    # JSON content with explicit None values for metadata
    content = json.dumps([{
        "path": "test.txt",
        "content": "hello",
        "tokens": None,
        "size_bytes": None,
        "lines": None
    }])

    # This should not raise TypeError
    stats = extract_files(content, str(output_dir))

    assert stats['total_files'] == 1
    assert (output_dir / "test.txt").read_text(encoding="utf-8") == "hello"
