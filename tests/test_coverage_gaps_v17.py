import sys
import os
import csv
import io
import logging
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

# Adjust sys.path to include the project root
sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

import sourcecombine

def test_summary_ui_wide_terminal_truncation_full(monkeypatch, capsys):
    """Cover lines 5145-5147, 5150, 5153, 5158, 5160, 5165, 5171, 5167, 5173."""
    stats = {
        'total_files': 1,
        'total_discovered': 1,
        'total_size_bytes': 100,
        'files_by_extension': {'.py': 1},
        'total_tokens': 10,
        'token_count_is_approx': False,
        'git_branch': 'very-long-branch-name-that-exceeds-sixty-characters-limit-to-trigger-truncation',
        'git_commit_short': 'abcdefg',
        'project_name': 'VeryLongProjectNameThatExceedsEightyCharactersLimitToTriggerTruncationForWideTerminalWidth',
        'top_files': []
    }

    args = MagicMock()
    args.dry_run = False
    args.estimate_tokens = False
    args.list_files = False
    args.tree = False
    args.extract = False

    monkeypatch.setenv("NO_COLOR", "1")

    terminal_size = MagicMock()
    terminal_size.columns = 100
    terminal_size.lines = 20

    with patch('sourcecombine.sys.stderr.isatty', return_value=True):
        with patch('sourcecombine.shutil.get_terminal_size', return_value=terminal_size):
            # Test with git_commit (Line 5158) and long "from/to" (Lines 5165, 5171)
            sourcecombine._print_execution_summary(
                stats,
                args,
                pairing_enabled=False,
                source_desc="from '" + "a" * 130 + "'",
                destination_desc="to '" + "b" * 130 + "'"
            )

            # Test without git_commit (Line 5160) and plain long desc (Lines 5167, 5173)
            stats_no_commit = stats.copy()
            stats_no_commit['git_commit_short'] = 'N/A'
            sourcecombine._print_execution_summary(
                stats_no_commit,
                args,
                pairing_enabled=False,
                source_desc="a" * 130,
                destination_desc="b" * 130
            )

    captured = capsys.readouterr()
    stderr = captured.err

    # Verify that truncation happened (lines were covered)
    assert "..." in stderr
    assert "abcdefg" in stderr
    assert "from '" in stderr
    assert "to '" in stderr

def test_csv_extraction_error_fallback(capsys):
    """Cover lines 4498-4499."""
    content = "path,size_bytes,tokens,tokens_is_approx,lines,language,sha256,content,modified\n"
    content += "path/to/file,100,10,False,5,python,hash,content,invalid_modified\n"
    content += "\n--- test.py ---\nprint('hello')\n--- end test.py ---"

    files = sourcecombine._parse_combined_content(content)
    assert len(files) == 1
    assert files[0][0] == "test.py"

def test_csv_cli_args_and_auto_ext(monkeypatch):
    """Cover lines 4142, 4182, 4229."""
    def mock_main_with_args(argv):
        with patch('sys.argv', argv):
            with patch('sourcecombine.find_and_combine_files') as mock_combine:
                mock_combine.return_value = {}
                with patch('sourcecombine._print_execution_summary'):
                    with patch('sys.exit'):
                        sourcecombine.main()
                        return mock_combine.call_args[0][0]

    config1 = mock_main_with_args(['sourcecombine.py', '--csv', '.'])
    assert config1['output']['format'] == 'csv'
    assert config1['output']['file'] == 'combined_files.csv'

    config2 = mock_main_with_args(['sourcecombine.py', '-o', 'out.csv', '.'])
    assert config2['output']['format'] == 'csv'

def test_find_and_combine_pairing_root_path_fallback(tmp_path):
    """Cover line 1423."""
    root = tmp_path / "project"
    root.mkdir()
    (root / "main.py").write_text("print(1)")

    paired_items = [("nested/out", [root / "main.py"])]
    processor = MagicMock()
    processor.create_backups = False

    with patch('sourcecombine._render_paired_filename', return_value="nested/out.txt"):
        sourcecombine._process_paired_files(
            paired_items,
            template="{{STEM}}",
            source_exts=(".py",),
            header_exts=(".h",),
            root_path=root,
            out_folder=None,
            processor=processor,
            processing_bar=None,
            dry_run=True
        )

def test_abs_output_path_oserror_fallback(tmp_path):
    """Cover lines 2329-2330."""
    root = tmp_path / "project"
    root.mkdir()
    (root / "main.py").write_text("print(1)")
    config = {'output': {'file': 'some/path'}}

    with patch('sourcecombine.Path.resolve', side_effect=OSError("Resolve failure")):
        with patch('sourcecombine.Path.absolute', side_effect=OSError("Absolute failure")):
             sourcecombine.find_and_combine_files(config, 'some/path', dry_run=True)

def test_get_files_from_paths_oserror_seen_paths(tmp_path):
    """Cover lines 2445-2446."""
    (tmp_path / "file.txt").write_text("test")

    config = {
        'filter': {'unique': True},
        'search': {'root_folders': [str(tmp_path)]}
    }

    # Mocking Path.resolve on the instance level for specific file
    with patch('pathlib.Path.resolve', side_effect=OSError("Resolve failure")):
        with patch('sourcecombine.collect_file_paths', return_value=([Path(tmp_path / "file.txt")], Path(tmp_path), 0)):
             with patch('sourcecombine.should_include', return_value=(True, None)):
                  # Avoid other resolve calls in find_and_combine_files
                  with patch('sourcecombine.Path.absolute', return_value=Path('output.txt')):
                       sourcecombine.find_and_combine_files(config, 'output.txt', dry_run=True)

def test_summary_ui_terminal_80_exactly(monkeypatch, capsys):
    """Cover line 5093 logic for terminal size exactly 80."""
    stats = {
        'total_files': 1,
        'total_discovered': 1,
        'total_size_bytes': 100,
        'files_by_extension': {'.py': 1},
        'total_tokens': 10,
        'token_count_is_approx': False,
        'top_files': []
    }
    args = MagicMock(dry_run=False, estimate_tokens=False, list_files=False, tree=False, extract=False)
    monkeypatch.setenv("NO_COLOR", "1")

    terminal_size = MagicMock()
    terminal_size.columns = 80
    terminal_size.lines = 20

    with patch('sourcecombine.sys.stderr.isatty', return_value=True):
        with patch('sourcecombine.shutil.get_terminal_size', return_value=terminal_size):
            sourcecombine._print_execution_summary(stats, args, pairing_enabled=False)

    captured = capsys.readouterr()
    assert "SUCCESS" in captured.err

def test_csv_format_explicit_in_config(monkeypatch):
    """Cover line 4182 via config if needed."""
    with patch('sys.argv', ['sourcecombine.py', '-o', 'my.csv', '.']):
        with patch('sourcecombine.find_and_combine_files') as mock_combine:
            mock_combine.return_value = {}
            with patch('sourcecombine._print_execution_summary'):
                with patch('sys.exit'):
                    sourcecombine.main()
                    assert mock_combine.call_args[0][0]['output']['format'] == 'csv'
