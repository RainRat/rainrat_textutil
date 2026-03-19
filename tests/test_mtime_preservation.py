import os
import time
from pathlib import Path
import json
import pytest
from sourcecombine import find_and_combine_files, extract_files
from utils import DEFAULT_CONFIG
import copy

def test_mtime_preservation_json(tmp_path):
    # Setup
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    test_file = src_dir / "test.txt"
    test_file.write_text("hello", encoding="utf-8")

    # Set back in time
    past_time = time.time() - 10000
    os.utime(test_file, (past_time, past_time))
    expected_mtime = test_file.stat().st_mtime

    # Combine to JSON
    config = copy.deepcopy(DEFAULT_CONFIG)
    config['search']['root_folders'] = [str(src_dir)]
    output_json = tmp_path / "combined.json"

    find_and_combine_files(config, str(output_json), output_format='json')

    # Verify JSON contains modified field
    with open(output_json, "r") as f:
        data = json.load(f)
        assert "modified" in data[0]
        assert data[0]["modified"] == pytest.approx(expected_mtime)

    # Extract
    extract_dir = tmp_path / "extracted"
    extract_dir.mkdir()

    extract_files(output_json.read_text(), str(extract_dir))

    # Verify preserved
    extracted_file = extract_dir / "test.txt"
    assert extracted_file.exists()
    assert extracted_file.stat().st_mtime == pytest.approx(expected_mtime)

def test_mtime_preservation_xml(tmp_path):
    # Setup
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    test_file = src_dir / "test.txt"
    test_file.write_text("hello", encoding="utf-8")

    # Set back in time
    past_time = time.time() - 10000
    # Use integer for easier ISO comparison if needed, though isoformat handles it
    past_time = int(past_time)
    os.utime(test_file, (past_time, past_time))
    expected_mtime = test_file.stat().st_mtime

    # Combine to XML
    config = copy.deepcopy(DEFAULT_CONFIG)
    config['search']['root_folders'] = [str(src_dir)]
    output_xml = tmp_path / "combined.xml"

    find_and_combine_files(config, str(output_xml), output_format='xml')

    # Verify XML contains modified attribute
    content = output_xml.read_text()
    assert 'modified="' in content

    # Extract
    extract_dir = tmp_path / "extracted"
    extract_dir.mkdir()

    extract_files(content, str(extract_dir))

    # Verify preserved
    extracted_file = extract_dir / "test.txt"
    assert extracted_file.exists()
    # XML might lose sub-second precision depending on isoformat, but we used int
    assert extracted_file.stat().st_mtime == pytest.approx(expected_mtime)
