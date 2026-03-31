import sys; import os; from pathlib import Path; sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))
import pytest
from unittest.mock import patch, MagicMock
import sourcecombine
import copy

def test_main_cli_replacement_injection_none_config(tmp_path):
    """
    Targets sourcecombine.py lines 3094-3099 and 3102-3107.
    Covers the case where regex_replacements or line_regex_replacements are explicitly None in the config.
    """
    # Config with None instead of lists for replacements
    bad_config = {
        'search': {
            'root_folders': [str(tmp_path)],
            'recursive': True
        },
        'filters': {
            'exclusions': {'filenames': [], 'folders': []},
            'inclusion_groups': {}
        },
        'pairing': {'enabled': False},
        'output': {'file': str(tmp_path / "out.txt")},
        'logging': {'level': 'INFO'},
        'processing': {
            'regex_replacements': None,
            'line_regex_replacements': None
        }
    }

    with patch('sourcecombine.load_and_validate_config', return_value=bad_config), \
         patch('sourcecombine.utils.validate_config'), \
         patch('sys.argv', [
             'sourcecombine.py',
             '--config', 'dummy.yml',
             '--replace', 'foo', 'bar',
             '--replace-line', 'baz', 'qux'
         ]), \
         patch('sourcecombine.find_and_combine_files', return_value={}), \
         patch('sourcecombine._print_execution_summary'), \
         patch('sys.exit'):

        sourcecombine.main()

        # Verify that the lists were correctly initialized and rules were added
        assert isinstance(bad_config['processing']['regex_replacements'], list)
        assert len(bad_config['processing']['regex_replacements']) == 1
        assert bad_config['processing']['regex_replacements'][0] == {'pattern': 'foo', 'replacement': 'bar'}

        assert isinstance(bad_config['processing']['line_regex_replacements'], list)
        assert len(bad_config['processing']['line_regex_replacements']) == 1
        assert bad_config['processing']['line_regex_replacements'][0] == {'pattern': 'baz', 'replacement': 'qux'}

def test_main_cli_replacement_injection_existing_list(tmp_path):
    """
    Covers the branch where regex_replacements is already a list (not None).
    """
    config = {
        'search': {
            'root_folders': [str(tmp_path)],
            'recursive': True
        },
        'filters': {
            'exclusions': {'filenames': [], 'folders': []},
            'inclusion_groups': {}
        },
        'pairing': {'enabled': False},
        'output': {'file': str(tmp_path / "out.txt")},
        'logging': {'level': 'INFO'},
        'processing': {
            'regex_replacements': [{'pattern': 'orig', 'replacement': 'new'}],
            'line_regex_replacements': []
        }
    }

    # We use a copy for the return value but we want to check the same object or the one modified
    with patch('sourcecombine.load_and_validate_config', return_value=config), \
         patch('sourcecombine.utils.validate_config'), \
         patch('sys.argv', [
             'sourcecombine.py',
             '--config', 'dummy.yml',
             '--replace', 'foo', 'bar',
             '--replace-line', 'baz', 'qux'
         ]), \
         patch('sourcecombine.find_and_combine_files', return_value={}), \
         patch('sourcecombine._print_execution_summary'), \
         patch('sys.exit'):

        sourcecombine.main()

        assert len(config['processing']['regex_replacements']) == 2
        assert config['processing']['regex_replacements'][0] == {'pattern': 'orig', 'replacement': 'new'}
        assert config['processing']['regex_replacements'][1] == {'pattern': 'foo', 'replacement': 'bar'}
        assert len(config['processing']['line_regex_replacements']) == 1
        assert config['processing']['line_regex_replacements'][0] == {'pattern': 'baz', 'replacement': 'qux'}
