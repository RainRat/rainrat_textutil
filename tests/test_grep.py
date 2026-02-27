import os
import json
from pathlib import Path
import pytest
from sourcecombine import find_and_combine_files, extract_files
from utils import DEFAULT_CONFIG

def test_grep_filtering(tmp_path):
    # Setup test files
    dir1 = tmp_path / "src"
    dir1.mkdir()
    (dir1 / "file1.txt").write_text("This file has a TODO item.")
    (dir1 / "file2.txt").write_text("This file is clean.")
    (dir1 / "file3.txt").write_text("Another TODO here.")

    config = DEFAULT_CONFIG.copy()
    config['search'] = {'root_folders': [str(dir1)], 'recursive': True}
    config['filters'] = {'grep': 'TODO'}
    config['output'] = {'format': 'text', 'file': str(tmp_path / "combined.txt")}

    # Run combine
    stats = find_and_combine_files(config, str(tmp_path / "combined.txt"))

    # Verify stats
    assert stats['total_files'] == 2
    assert stats['filter_reasons'].get('grep_mismatch') == 1

    # Verify content
    combined_content = (tmp_path / "combined.txt").read_text()
    assert "file1.txt" in combined_content
    assert "file3.txt" in combined_content
    assert "file2.txt" not in combined_content

def test_grep_extraction(tmp_path):
    # Setup a combined JSON content
    combined_data = [
        {"path": "todo.txt", "content": "Need to fix this TODO."},
        {"path": "done.txt", "content": "All finished here."}
    ]
    content = json.dumps(combined_data)

    config = DEFAULT_CONFIG.copy()
    config['filters'] = {'grep': 'TODO'}

    output_dir = tmp_path / "extracted"
    output_dir.mkdir()

    # Run extraction
    stats = extract_files(content, str(output_dir), config=config)

    # Verify stats
    assert stats['total_files'] == 1
    assert stats['filter_reasons'].get('grep_mismatch') == 1

    # Verify files
    assert (output_dir / "todo.txt").exists()
    assert not (output_dir / "done.txt").exists()

def test_grep_invalid_regex():
    config = DEFAULT_CONFIG.copy()
    config['filters'] = {'grep': '['} # Invalid regex

    from utils import validate_config, InvalidConfigError
    with pytest.raises(InvalidConfigError) as excinfo:
        validate_config(config)
    assert "Invalid regex pattern in filters.grep" in str(excinfo.value)
