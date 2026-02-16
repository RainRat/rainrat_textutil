import sys
import os
from pathlib import Path
from unittest.mock import patch
import pytest

# Adjust sys.path to include the project root
sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

from sourcecombine import main

@pytest.fixture
def temp_cwd(tmp_path):
    """Context manager to change current working directory."""
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(original_cwd)

def test_compact_flag_injection(temp_cwd):
    """Verify that --compact flag enables whitespace compaction in config."""
    test_file = temp_cwd / "test.txt"
    test_file.write_text("line1\n\n\nline2", encoding="utf-8")

    output_file = temp_cwd / "output.txt"

    # Mock stats that main() expects for summary
    mock_stats_obj = {
        'total_files': 1,
        'total_discovered': 1,
        'total_size_bytes': 10,
        'files_by_extension': {'.txt': 1},
        'total_tokens': 5,
        'token_count_is_approx': True,
        'top_files': [],
        'filter_reasons': {}
    }

    # We patch find_and_combine_files to check the config it receives
    with patch('sourcecombine.find_and_combine_files') as mock_combine:
        mock_combine.return_value = mock_stats_obj
        with patch.object(sys, 'argv', ['sourcecombine.py', str(test_file), '--compact', '-o', str(output_file)]):
            main()

    # Verify find_and_combine_files was called with the correct config
    args, _ = mock_combine.call_args
    config = args[0]
    assert config['processing']['compact_whitespace'] is True

def test_compact_flag_functional(temp_cwd):
    """Verify that --compact flag actually reduces whitespace in the output."""
    test_file = temp_cwd / "test.txt"
    # Use 3 spaces so it doesn't trigger spaces_to_tabs (which needs 4)
    test_file.write_text("word1   word2\n\n\nword3", encoding="utf-8")

    output_file = temp_cwd / "output.txt"

    # Run main with the compact flag
    with patch.object(sys, 'argv', ['sourcecombine.py', str(test_file), '--compact', '-o', str(output_file)]):
        main()

    content = output_file.read_text(encoding="utf-8")
    # 3 spaces should be reduced to 2 (default compact_space_runs behavior)
    assert "word1  word2" in content
    # Multiple blank lines should be collapsed (default compact_blank_lines behavior)
    assert "word2\n\nword3" in content
    assert "\n\n\n" not in content
