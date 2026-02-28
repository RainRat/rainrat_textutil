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

def test_should_include_grep_empty_content_coverage():
    """Cover sourcecombine.py line 449: fallback to empty string when no content/path."""
    filter_opts = {'grep': 'pattern'}
    search_opts = {}
    # No virtual_content, no file_path
    include, reason = should_include(None, Path("test.txt"), filter_opts, search_opts, return_reason=True)
    assert include is False
    assert reason == 'grep_mismatch'

def test_should_include_grep_error_coverage(caplog):
    """Cover sourcecombine.py lines 453-455: grep exception handling."""
    filter_opts = {'grep': 'pattern'}
    search_opts = {}

    with patch("re.search", side_effect=Exception("Regex error")):
        with caplog.at_level(logging.WARNING):
            # Passing None for file_path is safe as long as we don't trigger other checks
            include, reason = should_include(None, Path("test.txt"), filter_opts, search_opts, return_reason=True)

    assert include is False
    assert reason == 'grep_error'
    assert "Error while checking grep pattern" in caplog.text

def test_cli_grep_config_injection(tmp_path, monkeypatch):
    """Cover sourcecombine.py lines 2390-2392: CLI grep flag and config initialization."""
    root = tmp_path / "root"
    root.mkdir()
    (root / "file1.txt").write_text("TODO", encoding="utf-8")

    out_file = tmp_path / "out.txt"
    config_file = tmp_path / "sourcecombine.yml"
    # Set filters to something that is not a dict to trigger lines 2390-2391
    config_file.write_text("filters: null")

    # Pass the config file as the first positional argument
    monkeypatch.setattr(sys, "argv", ["sourcecombine.py", str(config_file), str(root), "-o", str(out_file), "--grep", "TODO"])

    # We mock find_and_combine_files to check the injected config
    with patch("sourcecombine.find_and_combine_files") as mock_combine:
        mock_combine.return_value = {
            'total_files': 1,
            'files_by_extension': {},
            'filter_reasons': {},
            'top_files': []
        }
        try:
            main()
        except SystemExit:
            pass

        # Check that the config passed to find_and_combine_files has the grep filter
        assert mock_combine.called
        called_config = mock_combine.call_args[0][0]
        assert called_config['filters']['grep'] == "TODO"

def test_should_include_grep_virtual_bytes_coverage():
    """Cover sourcecombine.py lines 440-444: virtual_content as bytes."""
    filter_opts = {'grep': 'TODO'}
    search_opts = {}
    virtual_content = b"This is a TODO item."
    include, reason = should_include(None, Path("test.txt"), filter_opts, search_opts, return_reason=True, virtual_content=virtual_content)
    assert include is True
    assert reason is None
