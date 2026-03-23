import sys
from pathlib import Path
import pytest
from unittest.mock import MagicMock

# Ensure repo root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sourcecombine import should_include
import utils

def test_should_include_language_filter():
    filter_opts = {}
    search_opts = {'allowed_languages': ['python']}

    # Python file should be included
    assert should_include(None, Path("script.py"), filter_opts, search_opts) is True

    # Javascript file should NOT be included
    assert should_include(None, Path("script.js"), filter_opts, search_opts) is False

    # Reason check
    include, reason = should_include(None, Path("script.js"), filter_opts, search_opts, return_reason=True)
    assert include is False
    assert reason == 'language_mismatch'

def test_should_include_multiple_languages():
    filter_opts = {}
    search_opts = {'allowed_languages': ['python', 'javascript']}

    assert should_include(None, Path("script.py"), filter_opts, search_opts) is True
    assert should_include(None, Path("script.js"), filter_opts, search_opts) is True
    assert should_include(None, Path("styles.css"), filter_opts, search_opts) is False

def test_language_filter_interaction_with_extensions():
    filter_opts = {}
    # Extension filter only allows .py
    search_opts = {
        'allowed_languages': ['python', 'javascript'],
        'effective_allowed_extensions': ('.py',)
    }

    # script.py matches both, so included
    assert should_include(None, Path("script.py"), filter_opts, search_opts) is True

    # script.js matches language but not extension, so excluded
    assert should_include(None, Path("script.js"), filter_opts, search_opts) is False

def test_get_all_languages():
    langs = utils.get_all_languages()
    assert isinstance(langs, list)
    assert 'python' in langs
    assert 'javascript' in langs
    assert 'cpp' in langs
    # Should be sorted
    assert langs == sorted(list(set(langs)))

def test_list_languages_cli(capsys):
    from sourcecombine import main
    import sys
    from unittest.mock import patch

    test_args = ["sourcecombine.py", "--list-languages"]
    with patch.object(sys, 'argv', test_args):
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 0

    captured = capsys.readouterr()
    assert "python" in captured.out
    assert "javascript" in captured.out
    assert "Supported Languages:" in captured.out
