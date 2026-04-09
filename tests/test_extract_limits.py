
import sys
import os
import json
from pathlib import Path
import pytest

# Add project root to path
sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

from sourcecombine import extract_files

@pytest.fixture
def combined_json_content():
    files = [
        {"path": "file1.txt", "content": "one\ntwo", "tokens": 10, "size_bytes": 100, "lines": 2},
        {"path": "file2.txt", "content": "three\nfour", "tokens": 20, "size_bytes": 200, "lines": 2},
        {"path": "file3.txt", "content": "five\nsix", "tokens": 30, "size_bytes": 300, "lines": 2},
    ]
    return json.dumps(files)

def test_extract_token_limit(tmp_path, combined_json_content):
    out_dir = tmp_path / "extract"
    out_dir.mkdir()

    config = {"filters": {"max_total_tokens": 15}} # Only file1 (10) fits. file2 (20) brings to 30.

    stats = extract_files(
        [("combined.json", combined_json_content)],
        str(out_dir),
        config=config
    )

    assert stats['total_files'] == 1
    assert (out_dir / "file1.txt").exists()
    assert not (out_dir / "file2.txt").exists()
    assert stats['token_limit_reached'] is True

def test_extract_size_limit(tmp_path, combined_json_content):
    out_dir = tmp_path / "extract"
    out_dir.mkdir()

    config = {"filters": {"max_total_size_bytes": 350}} # file1(100) + file2(200) = 300 fits. file3(300) brings to 600.

    stats = extract_files(
        [("combined.json", combined_json_content)],
        str(out_dir),
        config=config
    )

    assert stats['total_files'] == 2
    assert (out_dir / "file1.txt").exists()
    assert (out_dir / "file2.txt").exists()
    assert not (out_dir / "file3.txt").exists()
    assert stats['size_limit_reached'] is True

def test_extract_line_limit(tmp_path, combined_json_content):
    out_dir = tmp_path / "extract"
    out_dir.mkdir()

    config = {"filters": {"max_total_lines": 3}} # file1(2) fits. file2(2) brings to 4.

    stats = extract_files(
        [("combined.json", combined_json_content)],
        str(out_dir),
        config=config
    )

    assert stats['total_files'] == 1
    assert stats['line_limit_reached'] is True

def test_extract_multiple_limits(tmp_path, combined_json_content):
    out_dir = tmp_path / "extract"
    out_dir.mkdir()

    # Token limit is 15, Size limit is 500.
    # file1 fits (tokens 10 < 15, size 100 < 500)
    # file2 fails on tokens (10+20=30 > 15) even though size fits (100+200=300 < 500)
    config = {
        "filters": {
            "max_total_tokens": 15,
            "max_total_size_bytes": 500
        }
    }

    stats = extract_files(
        [("combined.json", combined_json_content)],
        str(out_dir),
        config=config
    )

    assert stats['total_files'] == 1
    assert stats['token_limit_reached'] is True
    assert stats.get('size_limit_reached') is not True

def test_extract_xml_limits(tmp_path):
    xml_content = """<repository>
<file path="a.py" tokens="10" size="100" lines="1">print('a')</file>
<file path="b.py" tokens="20" size="200" lines="1">print('b')</file>
</repository>"""
    out_dir = tmp_path / "extract_xml"
    out_dir.mkdir()

    config = {"filters": {"max_total_tokens": 15}}
    extract_files([("c.xml", xml_content)], str(out_dir), config=config)

    assert (out_dir / "a.py").exists()
    assert not (out_dir / "b.py").exists()

def test_extract_text_limits(tmp_path):
    text_content = "--- a.txt ---\ncontent a\n--- end a.txt ---\n--- b.txt ---\ncontent b\n--- end b.txt ---"
    out_dir = tmp_path / "extract_text"
    out_dir.mkdir()

    # a.txt: 1 line, ~2 tokens, ~9 bytes
    # b.txt: 1 line, ~2 tokens, ~9 bytes
    config = {"filters": {"max_total_lines": 1}}
    extract_files([("c.txt", text_content)], str(out_dir), config=config)

    assert (out_dir / "a.txt").exists()
    assert not (out_dir / "b.txt").exists()
