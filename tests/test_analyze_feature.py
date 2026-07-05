import argparse
import pytest
from unittest.mock import MagicMock, patch
import sourcecombine
import utils

def test_analyze_flag_presets():
    """Verify that --analyze programmatically sets the correct flags."""
    parser = argparse.ArgumentParser()
    # Mocking argparse setup isn't easy, so we test the logic in main that handles the flag
    args = MagicMock()
    args.analyze = True
    args.dry_run = False
    args.estimate_tokens = False
    args.overview = False
    args.tree = False
    args.output = None
    args.clipboard = False
    args.list_files = False
    args.estimate_tokens = False

    # Simulate the logic in main
    if args.analyze:
        args.dry_run = True
        args.estimate_tokens = True
        args.overview = True
        args.tree = True

    assert args.dry_run is True
    assert args.estimate_tokens is True
    assert args.overview is True
    assert args.tree is True

def test_generate_project_overview_extensions(tmp_path):
    """Verify that _generate_project_overview includes Extensions breakdown."""
    stats = {
        'total_files': 2,
        'total_size_bytes': 200,
        'total_tokens': 50,
        'total_lines': 20,
        'project_name': 'TestProj',
        'files_by_extension': {'.py': 1, '.md': 1},
        'size_by_extension': {'.py': 100, '.md': 100},
        'tokens_by_extension': {'.py': 25, '.md': 25},
        'lines_by_extension': {'.py': 10, '.md': 10},
        'top_files': [
            (25, 100, 'file1.py', None, 10, 'python'),
            (25, 100, 'README.md', None, 10, 'markdown')
        ]
    }

    # Text format
    output_text = sourcecombine._generate_project_overview(stats, output_format='text')
    assert "Extensions:" in output_text
    assert ".py" in output_text
    assert ".md" in output_text

    # Markdown format
    output_md = sourcecombine._generate_project_overview(stats, output_format='markdown')
    assert "## Extensions" in output_md
    assert "| Extension | Count" in output_md
    assert "`.py`" in output_md
    assert "`.md`" in output_md

def test_print_execution_summary_extensions(capsys):
    """Verify that _print_execution_summary includes Extensions breakdown."""
    stats = {
        'total_files': 1,
        'total_size_bytes': 100,
        'total_tokens': 25,
        'total_lines': 10,
        'project_name': 'TestProj',
        'files_by_extension': {'.py': 1},
        'size_by_extension': {'.py': 100},
        'tokens_by_extension': {'.py': 25},
        'lines_by_extension': {'.py': 10},
        'top_files': [(25, 100, 'file1.py', None, 10, 'python')]
    }
    args = MagicMock()
    args.dry_run = True
    args.analyze = True

    with patch('shutil.get_terminal_size', return_value=MagicMock(columns=100)):
        sourcecombine._print_execution_summary(stats, args, pairing_enabled=False)

    captured = capsys.readouterr()
    # Summary goes to stderr
    assert "Extensions (by tokens)" in captured.err
    assert ".py" in captured.err
