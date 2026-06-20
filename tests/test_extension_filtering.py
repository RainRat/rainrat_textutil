import os
import pytest
from pathlib import Path
from sourcecombine import should_include, main
from utils import validate_config, DEFAULT_CONFIG
import copy
from unittest.mock import patch

def test_extension_normalization():
    config = {
        'search': {
            'allowed_extensions': ['py', '.JS'],
            'exclude_extensions': ['LOG', 'tmp']
        }
    }
    validate_config(config)
    assert config['search']['allowed_extensions'] == ['.py', '.js']
    assert config['search']['exclude_extensions'] == ['.log', '.tmp']
    assert config['search']['effective_allowed_extensions'] == ('.py', '.js')
    assert config['search']['effective_exclude_extensions'] == ('.log', '.tmp')

def test_should_include_exclude_extensions():
    search_opts = {
        'effective_allowed_extensions': (),
        'effective_exclude_extensions': ('.log', '.tmp')
    }
    filter_opts = {}

    # Allowed
    assert should_include(None, Path("test.py"), filter_opts, search_opts) is True
    # Excluded
    assert should_include(None, Path("test.log"), filter_opts, search_opts) is False
    assert should_include(None, Path("test.tmp"), filter_opts, search_opts) is False

    # Reason check
    include, reason = should_include(None, Path("test.log"), filter_opts, search_opts, return_reason=True)
    assert include is False
    assert reason == 'extension'

def test_extension_filter_priority():
    # If both allowed and exclude are set
    search_opts = {
        'effective_allowed_extensions': ('.py', '.js'),
        'effective_exclude_extensions': ('.js',)
    }
    filter_opts = {}

    assert should_include(None, Path("test.py"), filter_opts, search_opts) is True
    # .js is in allowed but ALSO in exclude. Exclude should win (or rather, allowed filters first, then exclude)
    assert should_include(None, Path("test.js"), filter_opts, search_opts) is False

def test_pairing_exclude_extensions_conflict():
    config = {
        'pairing': {'enabled': True},
        'search': {'root_folders': ['.'], 'exclude_extensions': ['.log']}
    }
    with pytest.raises(Exception, match="'exclude_extensions' cannot be used when pairing is enabled"):
        validate_config(config)

def test_cli_extension_injection(tmp_path):
    # Test that CLI flags are correctly injected into config
    with patch('sys.argv', ['sourcecombine.py', '--ext', 'py', '--exclude-ext', 'log', '--dry-run']):
        with patch('sourcecombine.find_and_combine_files') as mock_find:
            mock_find.return_value = {}
            try:
                main()
            except SystemExit:
                pass

            args, kwargs = mock_find.call_args
            config = args[0]
            assert 'py' in config['search']['allowed_extensions']
            assert 'log' in config['search']['exclude_extensions']

def test_extension_normalization_mixed_types():
    config = {
        'search': {
            'allowed_extensions': ['.py', 'js'],
        }
    }
    validate_config(config)
    assert config['search']['allowed_extensions'] == ['.py', '.js']
