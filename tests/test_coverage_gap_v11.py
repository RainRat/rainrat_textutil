import sys; import os; from pathlib import Path; sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

import pytest
from unittest.mock import patch, MagicMock
import sourcecombine
import utils

def test_main_map_lang_injection_null_config(tmp_path):
    """
    Cover sourcecombine.py lines 2987-2989:
    if custom_langs is None:
        custom_langs = config['search']['custom_languages'] = {}
    """
    config = {
        'search': {'root_folders': [str(tmp_path)], 'custom_languages': None},
        'logging': {'level': 'INFO'},
        'filters': {'exclusions': {'filenames': [], 'folders': []}, 'inclusion_groups': {}},
        'pairing': {}, 'output': {}, 'processing': {}
    }

    # We MUST patch both sourcecombine.utils.validate_config AND sourcecombine.validate_config
    # to prevent either call from fixing our 'custom_languages': None value.
    with patch("sourcecombine.load_and_validate_config", return_value=config), \
         patch("sourcecombine.utils.validate_config"), \
         patch("sourcecombine.validate_config"), \
         patch("sys.argv", ["sourcecombine.py", "-k", "dummy.yml", "--map-lang", ".mjml", "html"]), \
         patch("sourcecombine.find_and_combine_files", return_value={}), \
         patch("sourcecombine._print_execution_summary"), \
         patch("sys.exit"):

        sourcecombine.main()
        assert config['search']['custom_languages'] == {".mjml": "html"}

def test_main_allowed_languages_injection_null_config(tmp_path):
    """Cover sourcecombine.py line 2999: search['allowed_languages'] = []"""
    config = {
        'search': {'root_folders': [str(tmp_path)], 'allowed_languages': None},
        'logging': {'level': 'INFO'},
        'filters': {'exclusions': {'filenames': [], 'folders': []}, 'inclusion_groups': {}},
        'pairing': {}, 'output': {}, 'processing': {}
    }
    with patch("sourcecombine.load_and_validate_config", return_value=config), \
         patch("sourcecombine.utils.validate_config"), \
         patch("sourcecombine.validate_config"), \
         patch("sys.argv", ["sourcecombine.py", "-k", "dummy.yml", "--language", "python"]), \
         patch("sourcecombine.find_and_combine_files", return_value={}), \
         patch("sourcecombine._print_execution_summary"), \
         patch("sys.exit"):

        sourcecombine.main()
        assert config['search']['allowed_languages'] == ["python"]

def test_main_exclude_languages_injection_null_config(tmp_path):
    """Cover sourcecombine.py line 3005: search['exclude_languages'] = []"""
    config = {
        'search': {'root_folders': [str(tmp_path)], 'exclude_languages': None},
        'logging': {'level': 'INFO'},
        'filters': {'exclusions': {'filenames': [], 'folders': []}, 'inclusion_groups': {}},
        'pairing': {}, 'output': {}, 'processing': {}
    }
    with patch("sourcecombine.load_and_validate_config", return_value=config), \
         patch("sourcecombine.utils.validate_config"), \
         patch("sourcecombine.validate_config"), \
         patch("sys.argv", ["sourcecombine.py", "-k", "dummy.yml", "--exclude-language", "ruby"]), \
         patch("sourcecombine.find_and_combine_files", return_value={}), \
         patch("sourcecombine._print_execution_summary"), \
         patch("sys.exit"):

        sourcecombine.main()
        assert config['search']['exclude_languages'] == ["ruby"]

def test_validate_search_custom_languages_not_dict():
    """Cover utils.py line 496: if not isinstance(custom_langs, dict):"""
    config = {'search': {'custom_languages': "not a dict"}}
    with pytest.raises(utils.InvalidConfigError, match="search.custom_languages must be a dictionary."):
        utils._validate_search_section(config)

def test_validate_search_custom_languages_invalid_key_value():
    """Cover utils.py line 499: key and value type checks."""
    # Invalid key
    config = {'search': {'custom_languages': {123: "text"}}}
    with pytest.raises(utils.InvalidConfigError, match="Both keys and values in 'search.custom_languages' must be text."):
        utils._validate_search_section(config)
    # Invalid value
    config = {'search': {'custom_languages': {".txt": 123}}}
    with pytest.raises(utils.InvalidConfigError, match="Both keys and values in 'search.custom_languages' must be text."):
        utils._validate_search_section(config)
