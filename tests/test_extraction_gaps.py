import pytest
import logging
from sourcecombine import extract_files

def test_extract_xml_malformed_entry(tmp_path, caplog):
    """Test extraction from XML with some malformed file entries."""
    # The XML has one valid entry and one malformed entry (invalid date)
    content = """<root>
    <file path="valid.py">print("valid")</file>
    <file path="invalid.py" modified="invalid-date">print("invalid")</file>
</root>"""
    output_dir = tmp_path / "extracted_xml"
    output_dir.mkdir()

    with caplog.at_level(logging.DEBUG):
        extract_files(content, output_dir)

    assert (output_dir / "valid.py").exists()
    assert (output_dir / "valid.py").read_text() == 'print("valid")'
    # The second file should NOT exist because its meta parsing failed
    assert not (output_dir / "invalid.py").exists()
    # Check if the malformed entry was skipped and logged
    assert "Skipping malformed XML file entry" in caplog.text

def test_extract_text_format(tmp_path):
    """Test extraction from the default SourceCombine text format."""
    # Note the exact format with triple dashes and single newline after file content
    content = """--- a.py ---
print("hello")
--- end a.py ---
--- subdir/b.txt ---
some text
--- end subdir/b.txt ---
"""
    output_dir = tmp_path / "extracted_text"
    output_dir.mkdir()

    extract_files(content, output_dir)

    assert (output_dir / "a.py").exists()
    assert (output_dir / "a.py").read_text() == 'print("hello")'
    assert (output_dir / "subdir/b.txt").exists()
    assert (output_dir / "subdir/b.txt").read_text() == "some text"

def test_extract_text_format_no_match(tmp_path):
    """Test text extraction with content that doesn't match the pattern."""
    content = "not a combined file"
    output_dir = tmp_path / "extracted_none"
    output_dir.mkdir()

    # This should log an error and exit, but we'll check if any files were created
    with pytest.raises(SystemExit):
        extract_files(content, output_dir)

    assert len(list(output_dir.iterdir())) == 0
