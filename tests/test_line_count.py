import os
import io
import pytest
import copy
from pathlib import Path
from sourcecombine import find_and_combine_files, FileProcessor
import utils

def test_line_count_calculation(tmp_path):
    """Test that line count is correctly calculated on processed content."""
    file_path = tmp_path / "test.txt"
    content = "line1\nline2\nline3"
    file_path.write_text(content, encoding='utf-8')

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    buffer = io.StringIO()
    processor = FileProcessor(config, config['output'])

    # Normal case
    tokens, approx, lines = processor.process_and_write(file_path, tmp_path, buffer)
    assert lines == 3

    # With whitespace compaction (e.g. collapsing blank lines)
    content_with_blanks = "line1\n\n\nline2"
    file_path.write_text(content_with_blanks, encoding='utf-8')
    config['processing']['compact_whitespace'] = True
    processor = FileProcessor(config, config['output'])

    tokens, approx, lines = processor.process_and_write(file_path, tmp_path, buffer)
    # Compact whitespace collapses 3 newlines to 2 (compact_blank_lines)
    # "line1\n\n\nline2" -> "line1\n\nline2"
    assert lines == 3 # line1, empty, line2

def test_line_count_placeholders(tmp_path):
    """Test that placeholders are correctly rendered in templates."""
    file_path = tmp_path / "test.txt"
    file_path.write_text("1\n2\n3\n4\n5", encoding='utf-8')

    output_file = tmp_path / "combined.txt"
    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    config['search'] = {'root_folders': [str(tmp_path)], 'recursive': True}
    config['output']['file'] = str(output_file)
    config['output']['header_template'] = "{{FILENAME}}: {{LINE_COUNT}} lines\n"
    config['output']['footer_template'] = "End {{FILENAME}}\n"
    config['output']['global_header_template'] = "Total Project Lines: {{TOTAL_LINES}}\n"

    stats = find_and_combine_files(config, str(output_file))

    # Check that aggregate total_lines is tracked
    # 1 (global header) + 1 (file header) + 5 (content) + 1 (footer) = 8 lines
    assert stats['total_lines'] == 8

    result = output_file.read_text(encoding='utf-8')
    assert "test.txt: 5 lines" in result
    assert "Total Project Lines: 8" in result

def test_line_count_in_summary(capsys, tmp_path):
    """Test that line count is visible in the execution summary."""
    from sourcecombine import _print_execution_summary
    import argparse

    stats = {
        'total_files': 1,
        'total_discovered': 1,
        'total_size_bytes': 10,
        'total_lines': 123,
        'total_tokens': 45,
        'files_by_extension': {'.txt': 1}
    }

    args = argparse.Namespace(
        dry_run=False,
        estimate_tokens=False,
        list_files=False,
        tree=False,
        max_depth=None,
        min_size=None,
        max_size=None
    )

    _print_execution_summary(stats, args, pairing_enabled=False)

    captured = capsys.readouterr()
    assert "Total Lines:" in captured.err
    assert "123" in captured.err

def test_line_count_in_metadata_summary():
    """Test the metadata summary helper includes lines."""
    from sourcecombine import _format_metadata_summary

    meta = {'files': 2, 'size': 1024, 'lines': 50, 'tokens': 100}
    summary = _format_metadata_summary(meta)

    assert "2 files" in summary
    assert "1.00 KB" in summary
    assert "50 lines" in summary
    assert "100 tokens" in summary

    # Test singular
    meta_singular = {'lines': 1}
    summary_singular = _format_metadata_summary(meta_singular)
    assert "1 line" in summary_singular

    # Test singular file
    meta_file = {'files': 1}
    summary_file = _format_metadata_summary(meta_file)
    assert "1 file" in summary_file
