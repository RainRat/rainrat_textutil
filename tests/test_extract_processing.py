import sys; import os; from pathlib import Path; sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

import json
from sourcecombine import extract_files
import utils

def test_extract_with_compact(tmp_path):
    """Test that extraction respects the --compact flag."""
    data = [
        {
            "path": "test.txt",
            "content": "Line 1\n\n\nLine 2\n    Line 3",
            "size_bytes": 30
        }
    ]
    content = json.dumps(data)

    config = utils.DEFAULT_CONFIG.copy()
    config['processing'] = {'compact_whitespace': True}

    # Extract to tmp_path
    stats = extract_files(content, tmp_path, config=config)

    extracted_file = tmp_path / "test.txt"
    assert extracted_file.exists()

    extracted_content = extracted_file.read_text()
    # Compact should reduce 3 newlines to 2, and 4 spaces to 1 tab (default settings)
    assert "\n\n\n" not in extracted_content
    assert "\n\n" in extracted_content
    assert "\tLine 3" in extracted_content

def test_extract_with_replace(tmp_path):
    """Test that extraction respects regex replacements."""
    data = [
        {
            "path": "secret.txt",
            "content": "My secret key is: 12345",
        }
    ]
    content = json.dumps(data)

    config = utils.DEFAULT_CONFIG.copy()
    config['processing'] = {
        'regex_replacements': [{'pattern': r'12345', 'replacement': 'REDACTED'}]
    }

    extract_files(content, tmp_path, config=config)

    extracted_file = tmp_path / "secret.txt"
    assert extracted_file.read_text() == "My secret key is: REDACTED"

def test_extract_information_update_after_processing(tmp_path):
    """Test that stats are updated correctly if processing changes content."""
    original_content = "Hello World"
    data = [{"path": "test.txt", "content": original_content}]
    content = json.dumps(data)

    config = utils.DEFAULT_CONFIG.copy()
    config['processing'] = {
        'regex_replacements': [{'pattern': 'Hello', 'replacement': 'Hi'}]
    }

    # Hi World is 8 bytes, Hello World was 11 bytes
    stats = extract_files(content, tmp_path, config=config)

    assert stats['total_size_bytes'] == 8
    assert stats['top_files'][0][1] == 8
