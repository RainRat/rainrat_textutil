import pytest
from pathlib import Path
from sourcecombine import should_include
import utils
import sys
import sourcecombine

def test_language_exclusion_basic():
    filter_opts = {}
    search_opts = {'exclude_languages': ['python']}

    # Python file should be excluded
    res, reason = should_include(None, Path("test.py"), filter_opts, search_opts, return_reason=True)
    assert res is False
    assert reason == 'language_excluded'

    # Javascript file should be included
    res, reason = should_include(None, Path("test.js"), filter_opts, search_opts, return_reason=True)
    assert res is True

def test_language_exclusion_with_inclusion():
    filter_opts = {}
    search_opts = {
        'allowed_languages': ['python', 'javascript'],
        'exclude_languages': ['python']
    }

    # Python is in both, exclusion should take priority
    res, reason = should_include(None, Path("test.py"), filter_opts, search_opts, return_reason=True)
    assert res is False
    assert reason == 'language_excluded'

    # Javascript is only in allowed
    res, reason = should_include(None, Path("test.js"), filter_opts, search_opts, return_reason=True)
    assert res is True

    # C++ is in neither
    res, reason = should_include(None, Path("test.cpp"), filter_opts, search_opts, return_reason=True)
    assert res is False
    assert reason == 'language_mismatch'

def test_language_exclusion_case_insensitivity():
    # Note: utils.get_language_tag returns lower case tags from its mapping
    filter_opts = {}
    search_opts = {'exclude_languages': ['python']}

    # Extension is .PY but mapping gives 'python'
    res, reason = should_include(None, Path("test.PY"), filter_opts, search_opts, return_reason=True)
    assert res is False
    assert reason == 'language_excluded'

def test_language_exclusion_cli_integration(monkeypatch, capsys, tmp_path):
    # Create some test files in tmp_path
    py_file = tmp_path / "test_cli.py"
    js_file = tmp_path / "test_cli.js"
    py_file.write_text("print('hello')")
    js_file.write_text("console.log('hello')")

    # Mock sys.argv to exclude python and search in tmp_path
    test_args = ["sourcecombine.py", str(tmp_path), "--exclude-lang", "python", "--list-files"]
    monkeypatch.setattr(sys, "argv", test_args)

    sourcecombine.main()

    captured = capsys.readouterr()
    assert "test_cli.js" in captured.out
    assert "test_cli.py" not in captured.out
