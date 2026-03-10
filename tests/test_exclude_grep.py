import os
import json
import sys
import logging
import re
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from sourcecombine import find_and_combine_files, extract_files, should_include, main
from utils import DEFAULT_CONFIG

def test_exclude_grep_filtering(tmp_path):
    # Setup test files
    dir1 = tmp_path / "src"
    dir1.mkdir()
    (dir1 / "file1.txt").write_text("This file has a TODO item.")
    (dir1 / "file2.txt").write_text("This file is clean.")
    (dir1 / "file3.txt").write_text("Another TODO here.")
    (dir1 / "file4.txt").write_text("Skip this file please.")

    config = DEFAULT_CONFIG.copy()
    config['search'] = {'root_folders': [str(dir1)], 'recursive': True}
    config['filters'] = {'exclude_grep': 'TODO'}
    config['output'] = {'format': 'text', 'file': str(tmp_path / "combined.txt")}

    # Run combine
    stats = find_and_combine_files(config, str(tmp_path / "combined.txt"))

    # Verify stats: file1 and file3 should be excluded. file2 and file4 should be included.
    assert stats['total_files'] == 2
    assert stats['filter_reasons'].get('exclude_grep_match') == 2

    # Verify content
    combined_content = (tmp_path / "combined.txt").read_text()
    assert "file2.txt" in combined_content
    assert "file4.txt" in combined_content
    assert "file1.txt" not in combined_content
    assert "file3.txt" not in combined_content

def test_combined_grep_and_exclude_grep(tmp_path):
    # Setup test files
    dir1 = tmp_path / "src"
    dir1.mkdir()
    (dir1 / "file1.txt").write_text("Include this TODO.")
    (dir1 / "file2.txt").write_text("Include this TODO but EXCLUDE.")
    (dir1 / "file3.txt").write_text("No match here.")

    config = DEFAULT_CONFIG.copy()
    config['search'] = {'root_folders': [str(dir1)], 'recursive': True}
    # Must contain TODO but MUST NOT contain EXCLUDE
    config['filters'] = {'grep': 'TODO', 'exclude_grep': 'EXCLUDE'}
    config['output'] = {'format': 'text', 'file': str(tmp_path / "combined.txt")}

    # Run combine
    stats = find_and_combine_files(config, str(tmp_path / "combined.txt"))

    # file1: matches TODO, no EXCLUDE -> Included
    # file2: matches TODO, matches EXCLUDE -> Excluded
    # file3: no TODO -> Excluded
    assert stats['total_files'] == 1
    assert stats['filter_reasons'].get('grep_mismatch') == 1
    assert stats['filter_reasons'].get('exclude_grep_match') == 1

    combined_content = (tmp_path / "combined.txt").read_text()
    assert "file1.txt" in combined_content
    assert "file2.txt" not in combined_content
    assert "file3.txt" not in combined_content

def test_exclude_grep_extraction(tmp_path):
    # Setup a combined JSON content
    combined_data = [
        {"path": "todo.txt", "content": "Need to fix this TODO."},
        {"path": "clean.txt", "content": "All finished here."}
    ]
    content = json.dumps(combined_data)

    config = DEFAULT_CONFIG.copy()
    config['filters'] = {'exclude_grep': 'TODO'}

    output_dir = tmp_path / "extracted"
    output_dir.mkdir()

    # Run extraction
    stats = extract_files(content, str(output_dir), config=config)

    # Verify stats
    assert stats['total_files'] == 1
    assert stats['filter_reasons'].get('exclude_grep_match') == 1

    # Verify files
    assert (output_dir / "clean.txt").exists()
    assert not (output_dir / "todo.txt").exists()

def test_exclude_grep_invalid_regex():
    config = DEFAULT_CONFIG.copy()
    config['filters'] = {'exclude_grep': '['} # Invalid regex

    from utils import validate_config, InvalidConfigError
    with pytest.raises(InvalidConfigError) as excinfo:
        validate_config(config)
    assert "Invalid search pattern in filters.exclude_grep" in str(excinfo.value)

def test_cli_exclude_grep_config_injection(tmp_path, monkeypatch):
    root = tmp_path / "root"
    root.mkdir()
    (root / "file1.txt").write_text("TODO", encoding="utf-8")

    out_file = tmp_path / "out.txt"

    # Use -E alias
    monkeypatch.setattr(sys, "argv", ["sourcecombine.py", str(root), "-o", str(out_file), "-E", "TODO"])

    with patch("sourcecombine.find_and_combine_files") as mock_combine:
        mock_combine.return_value = {
            'total_files': 0,
            'files_by_extension': {},
            'filter_reasons': {'exclude_grep_match': 1},
            'top_files': [],
            'total_discovered': 1,
            'excluded_folder_count': 0
        }
        try:
            main()
        except SystemExit:
            pass

        assert mock_combine.called
        called_config = mock_combine.call_args[0][0]
        assert called_config['filters']['exclude_grep'] == "TODO"
