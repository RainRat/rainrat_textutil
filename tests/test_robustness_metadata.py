import sys; import os; from pathlib import Path; sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))
import utils
import sourcecombine
import pytest
from datetime import datetime

def test_parse_size_value_with_approx_prefix():
    assert utils.parse_size_value("~10KB") == 10240
    assert utils.parse_size_value("~ 1.5 MB") == int(1.5 * 1024 * 1024)

def test_extract_xml_with_approx_size(tmp_path):
    content = """
<repository>
<file path="approx.txt" size="~1 KB">
approx content
</file>
</repository>
    """
    stats = sourcecombine.extract_files(content, tmp_path, dry_run=True)

    # Verify metadata was parsed and flagged as approx
    assert stats['total_size_bytes'] == 1024
    assert stats['token_count_is_approx'] is True

def test_extract_files_sorting_by_modified_from_metadata(tmp_path):
    # Two files in XML with explicit modified times.
    # file1.txt is newer (2024), file2.txt is older (2023).
    content = """
<repository>
<file path="file1.txt" modified="2024-01-01T12:00:00">
new
</file>
<file path="file2.txt" modified="2023-01-01T12:00:00">
old
</file>
</repository>
    """
    # Sort by modified, ascending (oldest first)
    stats = sourcecombine.extract_files(content, tmp_path, dry_run=True, sort_by='modified')

    assert stats['top_files'][0][2] == "file2.txt"
    assert stats['top_files'][1][2] == "file1.txt"

def test_extract_xml_modified_preservation(tmp_path):
    # Fixed timestamp
    ts = datetime(2023, 5, 20, 10, 0, 0)
    iso_ts = ts.isoformat()
    expected_timestamp = ts.timestamp()

    content = f"""
<repository>
<file path="time.txt" modified="{iso_ts}">
content
</file>
</repository>
    """
    sourcecombine.extract_files(content, tmp_path, dry_run=False)

    target = tmp_path / "time.txt"
    assert target.exists()
    # Check if modification time was preserved
    assert target.stat().st_mtime == pytest.approx(expected_timestamp, abs=1)
