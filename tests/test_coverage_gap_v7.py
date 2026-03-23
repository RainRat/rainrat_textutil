import sys, os; from pathlib import Path; sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))
import utils
import sourcecombine
import pytest
from unittest.mock import patch, MagicMock
import copy

def test_validate_search_allowed_languages_not_list():
    config = {'search': {'allowed_languages': 'not-a-list'}}
    with pytest.raises(utils.InvalidConfigError, match="search.allowed_languages must be a list of languages."):
        utils._validate_search_section(config)

def test_validate_search_allowed_languages_not_strings():
    config = {'search': {'allowed_languages': [123]}}
    with pytest.raises(utils.InvalidConfigError, match="Values in 'search.allowed_languages' must be text."):
        utils._validate_search_section(config)

def test_main_cli_injection_missing_filters(tmp_path):
    # This targets sourcecombine.py:2760, 2764, 2769 and 2789, 2794 (missing filters section)
    test_file = tmp_path / "test.py"
    test_file.write_text("print('hello')", encoding='utf-8')
    dummy_config = tmp_path / "config.yml"
    dummy_config.write_text("search: {root_folders: ['.']}", encoding='utf-8')

    file_list = tmp_path / "files.txt"
    file_list.write_text(str(test_file), encoding='utf-8')

    # Triggering exclusion injection (line 2760, 2764, 2769)
    config1 = {'search': {'root_folders': [str(tmp_path)]}}
    with patch('sourcecombine.load_and_validate_config', return_value=config1):
        with patch('sys.argv', ['sourcecombine.py', '--config', str(dummy_config), '--files-from', str(file_list), '--exclude-file', '*.tmp']):
            with patch('sourcecombine.find_and_combine_files', return_value={}):
                with patch('sourcecombine._print_execution_summary'):
                    sourcecombine.main()

    # Triggering inclusion injection (line 2789 and 2794)
    config2 = {'search': {'root_folders': [str(tmp_path)]}}
    with patch('sourcecombine.load_and_validate_config', return_value=config2):
        with patch('sys.argv', ['sourcecombine.py', '--config', str(dummy_config), '--files-from', str(file_list), '--include', '*.py']):
             with patch('sourcecombine.find_and_combine_files', return_value={}):
                with patch('sourcecombine._print_execution_summary'):
                    sourcecombine.main()

def test_main_cli_language_injection(tmp_path):
    # This targets sourcecombine.py:2805-2809
    test_file = tmp_path / "test.py"
    test_file.write_text("print('hello')", encoding='utf-8')
    dummy_config = tmp_path / "config.yml"
    dummy_config.write_text("search: {root_folders: ['.']}", encoding='utf-8')

    file_list = tmp_path / "files.txt"
    file_list.write_text(str(test_file), encoding='utf-8')

    # Case 2: allowed_languages is missing in config (triggers line 2807)
    config3 = {'search': {'root_folders': [str(tmp_path)]}}
    with patch('sourcecombine.load_and_validate_config', return_value=config3):
        with patch('sys.argv', ['sourcecombine.py', '--config', str(dummy_config), '--files-from', str(file_list), '--language', 'javascript']):
            with patch('sourcecombine.find_and_combine_files', return_value={}):
                with patch('sourcecombine._print_execution_summary'):
                    sourcecombine.main()
