import sys; import os; from pathlib import Path; sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))
import utils
from sourcecombine import should_include
from pathlib import Path

def test_allowed_languages_case_insensitivity():
    """Verify that allowed_languages handles mixed casing during validation and inclusion."""
    config = {
        'search': {
            'allowed_languages': ['PYTHON', 'JavaScript']
        }
    }
    utils.validate_config(config)

    # Validation should have lowercased them
    assert config['search']['allowed_languages'] == ['python', 'javascript']

    filter_opts = config['filters']
    search_opts = config['search']

    # Test inclusion
    assert should_include(None, Path("test.py"), filter_opts, search_opts) is True
    assert should_include(None, Path("test.js"), filter_opts, search_opts) is True
    assert should_include(None, Path("test.txt"), filter_opts, search_opts) is False

def test_exclude_languages_case_insensitivity():
    """Verify that exclude_languages handles mixed casing during validation and inclusion."""
    config = {
        'search': {
            'exclude_languages': ['PyThOn']
        }
    }
    utils.validate_config(config)

    # Validation should have lowercased them
    assert config['search']['exclude_languages'] == ['python']

    filter_opts = config['filters']
    search_opts = config['search']

    # Test exclusion
    assert should_include(None, Path("test.py"), filter_opts, search_opts) is False
    assert should_include(None, Path("test.js"), filter_opts, search_opts) is True

def test_custom_languages_case_insensitivity():
    """Verify that custom_languages handles mixed casing for both keys and values."""
    config = {
        'search': {
            'custom_languages': {'.MyExt': 'MyLang'}
        }
    }
    utils.validate_config(config)

    # Validation should have lowercased keys and values
    assert config['search']['custom_languages'] == {'.myext': 'mylang'}

    filter_opts = config['filters']
    search_opts = config['search']

    # Test that the custom mapping works with the lowercased value
    search_opts['allowed_languages'] = ['mylang']
    assert should_include(None, Path("test.myext"), filter_opts, search_opts) is True

    # Test that it still works if user tries to allow with different case (though they shouldn't usually after validation)
    config2 = {
        'search': {
            'custom_languages': {'.EXT': 'LANG'},
            'allowed_languages': ['lAnG']
        }
    }
    utils.validate_config(config2)
    assert config2['search']['allowed_languages'] == ['lang']
    assert config2['search']['custom_languages'] == {'.ext': 'lang'}
    assert should_include(None, Path("test.ext"), config2['filters'], config2['search']) is True

def test_language_tag_overrides_case_insensitivity():
    """Verify that get_language_tag handles mixed case overrides correctly."""
    overrides = {'.PY': 'PYTHON_CUSTOM', 'Makefile': 'MAKE_CUSTOM', 'js': 'JS_CUSTOM'}

    # utils.get_language_tag doesn't normalize overrides itself,
    # it expects them to be normalized or it does direct lookups.
    # But wait, utils.get_language_tag implementation:
    # if name in overrides: return overrides[name]
    # it uses name.lower() for name, so if we want case-insensitivity in overrides
    # they MUST be lowercased before passing to get_language_tag.
    # Our validation logic now does this.

    normalized_overrides = {k.lower(): v.lower() for k, v in overrides.items()}

    assert utils.get_language_tag("test.py", overrides=normalized_overrides) == "python_custom"
    assert utils.get_language_tag("Makefile", overrides=normalized_overrides) == "make_custom"
    assert utils.get_language_tag("test.js", overrides=normalized_overrides) == "js_custom"
