import sys
import os
from pathlib import Path
import json
import logging
import yaml
from unittest.mock import MagicMock, patch
import pytest

sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

import sourcecombine


def test_cli_ignores_and_exclusions_none_defaults(tmp_path):
    config_file = tmp_path / "config.yml"
    config_data = {
        'search': {
            'root_folders': [str(tmp_path)],
            'ignore_files': None,
            'exclude_extensions': None,
        }
    }
    with open(config_file, 'w') as f:
        yaml.dump(config_data, f)

    with patch('utils.validate_config'), \
         patch('sourcecombine.validate_config'), \
         patch('sourcecombine.find_and_combine_files') as mock_combine:
        mock_combine.return_value = {}
        args = [
            str(config_file),
            '--ignore-file', 'foo.txt',
            '--exclude-extension', '.tmp'
        ]
        with patch.object(sys, 'argv', ['sourcecombine.py'] + args):
            sourcecombine.main()

        assert mock_combine.called
        config_passed = mock_combine.call_args[0][0]
        assert 'foo.txt' in config_passed['search']['ignore_files']
        assert '.tmp' in config_passed['search']['exclude_extensions']


def test_extension_normalization_non_string_and_dots(tmp_path):
    config_data = {
        'search': {
            'root_folders': [str(tmp_path)],
            'allowed_extensions': [123, '.py'],
            'exclude_extensions': [456, '.tmp'],
        },
        'pairing': {
            'enabled': True,
            'source_extensions': [789, 'cpp'],
            'header_extensions': ['.h'],
            'include_mismatched': False,
        }
    }

    with patch('sourcecombine.load_and_validate_config', return_value=config_data), \
         patch('utils.validate_config'), \
         patch('sourcecombine.validate_config'), \
         patch('sourcecombine.find_and_combine_files') as mock_combine:
        mock_combine.return_value = {}

        with patch.object(sys, 'argv', ['sourcecombine.py', 'dummy_config.yml', str(tmp_path)]):
            sourcecombine.main()

        assert mock_combine.called
        config_passed = mock_combine.call_args[0][0]
        search = config_passed['search']
        assert search['effective_allowed_extensions'] == ('.cpp', '.h')


def test_extension_normalization_non_pairing(tmp_path):
    config_data = {
        'search': {
            'root_folders': [str(tmp_path)],
            'allowed_extensions': [123, '.py'],
            'exclude_extensions': [456, '.tmp'],
        },
        'pairing': {
            'enabled': False,
        }
    }

    with patch('sourcecombine.load_and_validate_config', return_value=config_data), \
         patch('utils.validate_config'), \
         patch('sourcecombine.validate_config'), \
         patch('sourcecombine.find_and_combine_files') as mock_combine:
        mock_combine.return_value = {}

        with patch.object(sys, 'argv', ['sourcecombine.py', 'dummy_config.yml', str(tmp_path)]):
            sourcecombine.main()

        assert mock_combine.called
        config_passed = mock_combine.call_args[0][0]
        search = config_passed['search']
        assert search['effective_allowed_extensions'] == ('.py',)
        assert search['effective_exclude_extensions'] == ('.tmp',)


def test_extract_files_with_null_content(tmp_path, caplog):
    caplog.set_level(logging.INFO)
    data = [
        {"path": "empty_file.txt", "content": None, "size_bytes": 0}
    ]
    content = json.dumps(data)

    stats = sourcecombine.extract_files(content, tmp_path, dry_run=False)

    target_file = tmp_path / "empty_file.txt"
    assert not target_file.exists()
    assert "Skipping extraction for file without content" in caplog.text


def test_print_execution_summary_secondary_metrics(capsys):
    stats = {
        'total_files': 2,
        'total_size_bytes': 1000,
        'total_lines': 50,
        'total_tokens': 100,
        'top_files': [
            (100, 500, 'dir1/file1.py', 'OK', 30),
            (0, 500, 'dir1/file2.py', '', 20)
        ],
        'tokens_by_language': {'python': 100},
        'lines_by_language': {'python': 50},
        'size_by_language': {'python': 1000},
        'files_by_language': {'python': 2},
    }

    args = MagicMock()
    args.quiet = False
    args.dry_run = False
    args.estimate_tokens = False
    args.list_files = False
    args.tree = False
    args.extract = False
    args.apply_in_place = False

    with patch('shutil.get_terminal_size', return_value=MagicMock(columns=120)), \
         patch('sourcecombine._get_primary_metric', return_value='lines'):

        sourcecombine._print_execution_summary(
            stats, args, pairing_enabled=False, destination_desc="to 'combined.txt'"
        )

    captured = capsys.readouterr()
    assert "TOKENS" in captured.err


def test_print_execution_summary_languages_by_lines(capsys):
    stats = {
        'total_files': 1,
        'total_size_bytes': 500,
        'total_lines': 50,
        'total_tokens': 0,
        'top_files': [
            (0, 500, 'file1.py', '', 50)
        ],
        'tokens_by_language': {},
        'lines_by_language': {'python': 50},
        'size_by_language': {'python': 500},
        'files_by_language': {'python': 1},
    }

    args = MagicMock()
    args.quiet = False
    args.dry_run = False
    args.estimate_tokens = False
    args.list_files = False
    args.tree = False
    args.extract = False
    args.apply_in_place = False

    with patch('shutil.get_terminal_size', return_value=MagicMock(columns=120)):
        sourcecombine._print_execution_summary(
            stats, args, pairing_enabled=False, destination_desc="to 'combined.txt'"
        )

    captured = capsys.readouterr()
    assert "Languages (by lines)" in captured.err


def test_print_execution_summary_footer_truncation(capsys):
    stats = {
        'total_files': 1,
        'total_size_bytes': 100,
        'top_files': [(0, 100, 'file1.py', '', 10)],
    }

    args = MagicMock()
    args.quiet = False
    args.dry_run = False
    args.estimate_tokens = False
    args.list_files = False
    args.tree = False
    args.extract = False
    args.apply_in_place = False

    with patch('shutil.get_terminal_size', return_value=MagicMock(columns=40)):
        sourcecombine._print_execution_summary(
            stats, args, pairing_enabled=False, destination_desc="to " + "a" * 100
        )

    captured = capsys.readouterr()
    assert "..." in captured.err
