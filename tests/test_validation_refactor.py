import pytest
import utils
from utils import validate_config

def test_language_validation_lowercasing():
    config = {
        'search': {
            'allowed_languages': ['Python', 'JavaScript'],
            'exclude_languages': ['HTML', 'CSS']
        }
    }
    validate_config(config)
    assert config['search']['allowed_languages'] == ['python', 'javascript']
    assert config['search']['exclude_languages'] == ['html', 'css']

def test_language_validation_invalid_type():
    config = {
        'search': {
            'allowed_languages': 'not a list'
        }
    }
    # Use utils.InvalidConfigError directly to be robust against module reloads
    with pytest.raises(utils.InvalidConfigError, match="search.allowed_languages must be a list of languages."):
        validate_config(config)

def test_language_validation_invalid_item_type():
    config = {
        'search': {
            'exclude_languages': ['python', 123]
        }
    }
    with pytest.raises(utils.InvalidConfigError, match="Values in 'search.exclude_languages' must be text."):
        validate_config(config)

def test_extension_validation_lowercasing_and_dots():
    config = {
        'search': {
            'allowed_extensions': ['PY', '.JS']
        }
    }
    validate_config(config)
    assert config['search']['allowed_extensions'] == ['.py', '.js']

def test_extension_validation_invalid_type():
    config = {
        'search': {
            'exclude_extensions': 'not a list'
        }
    }
    with pytest.raises(utils.InvalidConfigError, match="search.exclude_extensions must be a list"):
        validate_config(config)

def test_extension_validation_invalid_item_type():
    config = {
        'search': {
            'exclude_extensions': [None]
        }
    }
    with pytest.raises(utils.InvalidConfigError, match="Values in 'search.exclude_extensions' must be text."):
        validate_config(config)
