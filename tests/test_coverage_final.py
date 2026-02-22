import os
import sys
import logging
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
import copy

# Adjust sys.path to include the project root
sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

from sourcecombine import find_and_combine_files, main
import utils

@pytest.fixture
def temp_env(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    (root / "file1.cpp").write_text("int main() {}", encoding="utf-8")
    (root / "file1.h").write_text("void main();", encoding="utf-8")
    (root / "small.txt").write_text("small", encoding="utf-8")
    (root / "large.txt").write_text("large content" * 10, encoding="utf-8")
    return root, tmp_path

def test_sort_by_tokens_with_size_exclusion_placeholder(temp_env):
    """Cover sourcecombine.py lines related to sort_by='tokens' + size exclusion with placeholder."""
    root, tmp_path = temp_env
    out_file = tmp_path / "out1.txt"

    config = {
        "search": {"root_folders": [str(root)]},
        "filters": {"max_size_bytes": 10},
        "output": {
            "file": str(out_file),
            "sort_by": "tokens",
            "max_size_placeholder": "Too big: {{FILENAME}}"
        }
    }

    stats = find_and_combine_files(config, output_path=str(out_file))
    # small.txt (included)
    # large.txt, file1.cpp, file1.h (placeholders)
    assert stats['total_files'] == 4

def test_main_cli_flags_format_and_sort_coverage(temp_env):
    """Cover sourcecombine.py CLI flags for format and sort."""
    root, tmp_path = temp_env

    mock_stats = {
        'total_files': 1, 'total_discovered': 1, 'total_size_bytes': 10,
        'files_by_extension': {'.txt': 1}, 'total_tokens': 5,
        'token_count_is_approx': False, 'top_files': [], 'filter_reasons': {}
    }

    with patch('sourcecombine.find_and_combine_files', return_value=mock_stats) as mock_combine:
        # Test --markdown and --sort
        with patch('sys.argv', ['sourcecombine.py', str(root), '--markdown', '--sort', 'size', '--reverse']):
            main()

        _, kwargs = mock_combine.call_args
        assert kwargs['output_format'] == 'markdown'

        args, _ = mock_combine.call_args
        config = args[0]
        assert config['output']['sort_by'] == 'size'
        assert config['output']['sort_reverse'] is True

        # Test --json
        with patch('sys.argv', ['sourcecombine.py', str(root), '--json']):
            main()
        _, kwargs = mock_combine.call_args
        assert kwargs['output_format'] == 'json'

        # Test --xml
        with patch('sys.argv', ['sourcecombine.py', str(root), '--xml']):
            main()
        _, kwargs = mock_combine.call_args
        assert kwargs['output_format'] == 'xml'

def test_main_compact_no_processing_section_coverage(temp_env):
    """Cover sourcecombine.py --compact without processing section."""
    root, tmp_path = temp_env

    config_file = tmp_path / "config.yml"
    config_file.write_text("search: {root_folders: ['.']}", encoding="utf-8")

    mock_stats = {
        'total_files': 0, 'total_discovered': 0, 'total_size_bytes': 0,
        'files_by_extension': {}, 'total_tokens': 0,
        'token_count_is_approx': False, 'top_files': [], 'filter_reasons': {}
    }

    with patch('sourcecombine.find_and_combine_files', return_value=mock_stats) as mock_combine:
        with patch('sys.argv', ['sourcecombine.py', str(config_file), '--compact']):
            main()

        args, _ = mock_combine.call_args
        config = args[0]
        assert config['processing']['compact_whitespace'] is True

def test_main_logging_setup_gap_coverage(temp_env):
    """Cover sourcecombine.py logging setup when no handlers exist."""
    root, tmp_path = temp_env
    root_logger = logging.getLogger()
    old_handlers = root_logger.handlers[:]
    root_logger.handlers[:] = []

    mock_stats = {
        'total_files': 0, 'total_discovered': 0, 'total_size_bytes': 0,
        'files_by_extension': {}, 'total_tokens': 0,
        'token_count_is_approx': False, 'top_files': [], 'filter_reasons': {}
    }

    try:
        with patch('sourcecombine.find_and_combine_files', return_value=mock_stats):
            with patch('sys.argv', ['sourcecombine.py', str(root)]):
                main()
        assert len(root_logger.handlers) > 0
    finally:
        root_logger.handlers[:] = old_handlers
