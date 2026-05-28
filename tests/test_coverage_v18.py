import sys
import os
import io
import csv
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

# Adjust sys.path to include the project root
sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

import sourcecombine
import utils

def test_paired_unrooted_path_with_parts(tmp_path):
    """Cover line 1423: out_file = root_path / out_path"""
    root = tmp_path / "project"
    root.mkdir()
    src = root / "file.cpp"
    src.write_text("content", encoding="utf-8")

    config = {"processing": {}, "output": {"header_template": "", "footer_template": ""}}
    processor = sourcecombine.FileProcessor(config, config["output"], dry_run=False)

    pairs = [("file", [src])]
    out_folder = None # Trigger the else branch

    # We want out_path.parts > 1, so template should have a slash
    template = "subdir/{{STEM}}.out"

    # Mock relative_to to return a relative path
    with patch('pathlib.Path.relative_to', return_value=Path("file.cpp")):
        sourcecombine._process_paired_files(
            pairs,
            template=template,
            source_exts=(".cpp",),
            header_exts=(".h",),
            root_path=root,
            out_folder=out_folder,
            processor=processor,
            processing_bar=None,
            dry_run=False,
        )

    assert (root / "subdir/file.out").exists()

def test_find_and_combine_files_oserror_fallback_none(tmp_path):
    """Cover lines 2329-2330: OSError fallback to None"""
    with patch('pathlib.Path.resolve', side_effect=OSError):
        with patch('pathlib.Path.absolute', side_effect=OSError):
            # We need to pass an output_path that is not '-'
            config = {'output': {}, 'processing': {}, 'search': {'root_folders': [str(tmp_path)]}}
            stats = sourcecombine.find_and_combine_files(config, output_path=str(tmp_path / "some/path"))
            # Should not crash and reach end
            assert stats is not None

def test_find_and_combine_files_unique_oserror(tmp_path):
    """Cover lines 2445-2446: OSError fallback in unique check"""
    f = tmp_path / "test.py"
    f.write_text("print(1)", encoding="utf-8")

    config = {
        'search': {'root_folders': [str(tmp_path)]},
        'filters': {'unique': True},
        'output': {}
    }

    with patch('pathlib.Path.resolve', side_effect=OSError):
        # Pass output_path to avoid the InvalidConfigError
        stats = sourcecombine.find_and_combine_files(config, output_path="-")
        assert stats['total_files'] == 1

def test_main_csv_flag():
    """Cover line 4142: args.format = 'csv' from --csv flag"""
    with patch('sys.argv', ['sourcecombine.py', '--csv', '--dry-run']):
        with patch('sourcecombine.find_and_combine_files', return_value={'total_files':0}) as mock_find:
            with patch('sourcecombine._print_execution_summary'):
                with patch('sys.exit'):
                    sourcecombine.main()
                    config = mock_find.call_args[0][0]
                    assert config['output']['format'] == 'csv'

def test_main_csv_extension_auto_detect():
    """Cover line 4182: args.format = 'csv' from output extension"""
    with patch('sys.argv', ['sourcecombine.py', '-o', 'out.csv', '--dry-run']):
        with patch('sourcecombine.find_and_combine_files', return_value={'total_files':0}) as mock_find:
            with patch('sourcecombine._print_execution_summary'):
                with patch('sys.exit'):
                    sourcecombine.main()
                    config = mock_find.call_args[0][0]
                    assert config['output']['format'] == 'csv'

def test_main_csv_auto_suffix():
    """Cover line 4229: auto-suffix .csv"""
    # Need to have a format set to csv but output filename must be DEFAULT_OUTPUT_FILENAME
    with patch('sys.argv', ['sourcecombine.py', '--csv', '--dry-run']):
        with patch('sourcecombine.find_and_combine_files', return_value={'total_files':0}) as mock_find:
            with patch('sourcecombine._print_execution_summary'):
                with patch('sys.exit'):
                    sourcecombine.main()
                    # Check the actual output_path passed to find_and_combine_files (2nd arg)
                    output_path = mock_find.call_args[0][1]
                    assert output_path.endswith('.csv')

def test_parse_combined_content_csv_error_direct():
    """Cover lines 4498-4499: csv.Error and other items handling"""
    content = "path,size_bytes,tokens,tokens_is_approx,lines,language,sha256,content,modified\nfile.txt,4,1,False,1,text,hash,data,invalid_float"

    # Passing 'invalid_float' for modified will trigger ValueError when calling float()
    res = sourcecombine._parse_combined_content(content)
    # It should catch ValueError and pass, but since it didn't return early,
    # it will continue to Text matching and return [] because it doesn't match.
    assert res == []

def test_summary_ui_wide_and_truncation(monkeypatch, capsys):
    """Cover lines 5145-5147, 5150, 5153, 5160, 5167, 5173"""
    stats = {
        'total_files': 1,
        'total_discovered': 1,
        'total_size_bytes': 100,
        'files_by_extension': {'.py': 1},
        'total_tokens': 10,
        'token_count_is_approx': False,
        'git_branch': 'a' * 70, # Trigger branch truncation
        'git_commit_short': None, # Trigger project_ctx with no commit
        'project_name': 'b' * 90, # Trigger project truncation
        'top_files': []
    }

    args = MagicMock()
    args.dry_run = False
    args.estimate_tokens = False
    args.list_files = False
    args.tree = False
    args.extract = False

    monkeypatch.setenv("NO_COLOR", "1")

    # Mock wide terminal
    # Mock it in sourcecombine module
    with patch('sourcecombine.sys.stderr.isatty', return_value=True):
        with patch('sourcecombine.shutil.get_terminal_size', return_value=MagicMock(columns=200, lines=24)):
            # Provide long source and destination descriptions that DON'T start with from ' or to '
            # to trigger the else branch of truncation.
            source_desc = "C" * 150
            destination_desc = "D" * 150

            sourcecombine._print_execution_summary(
                stats, args, pairing_enabled=False,
                source_desc=source_desc,
                destination_desc=destination_desc
            )

    captured = capsys.readouterr().err
    assert "..." in captured
    assert "bbbb" in captured
    assert "aaaa" in captured
    assert "CCCC" in captured
    assert "DDDD" in captured

def test_summary_ui_truncation_with_quotes(monkeypatch, capsys):
    """Cover lines 5165 and 5171"""
    stats = {
        'total_files': 1,
        'total_discovered': 1,
        'total_size_bytes': 100,
        'files_by_extension': {'.py': 1},
        'total_tokens': 10,
        'token_count_is_approx': False,
        'top_files': []
    }

    args = MagicMock()
    args.dry_run = False
    args.estimate_tokens = False
    args.list_files = False
    args.tree = False
    args.extract = False

    monkeypatch.setenv("NO_COLOR", "1")

    # Mock wide terminal
    with patch('sourcecombine.sys.stderr.isatty', return_value=True):
        with patch('sourcecombine.shutil.get_terminal_size', return_value=MagicMock(columns=200, lines=24)):
            # Provide long source and destination descriptions that START with from ' or to '
            source_desc = "from '" + "c" * 150 + "'"
            destination_desc = "to '" + "d" * 150 + "'"

            sourcecombine._print_execution_summary(
                stats, args, pairing_enabled=False,
                source_desc=source_desc,
                destination_desc=destination_desc
            )

    captured = capsys.readouterr().err
    assert "..." in captured
    assert "cccc" in captured
    assert "dddd" in captured

def test_summary_ui_narrow_terminal(monkeypatch, capsys):
    """Cover the if branch of line 5140: term_width <= 80"""
    stats = {
        'total_files': 1,
        'total_discovered': 1,
        'total_size_bytes': 100,
        'files_by_extension': {'.py': 1},
        'total_tokens': 10,
        'token_count_is_approx': False,
        'top_files': []
    }

    args = MagicMock()
    args.dry_run = False
    args.estimate_tokens = False
    args.list_files = False
    args.tree = False
    args.extract = False

    monkeypatch.setenv("NO_COLOR", "1")

    # Mock narrow terminal
    with patch('sourcecombine.sys.stderr.isatty', return_value=True):
        with patch('sourcecombine.shutil.get_terminal_size', return_value=MagicMock(columns=70, lines=24)):
            sourcecombine._print_execution_summary(
                stats, args, pairing_enabled=False
            )

    captured = capsys.readouterr().err
    assert "SUCCESS" in captured
