import os
from pathlib import Path
import pytest
from sourcecombine import should_include, main
import utils
from unittest.mock import patch

def test_should_include_exclude_language(tmp_path):
    filter_opts = {}
    search_opts = {'excluded_languages': ['python']}

    py_file = tmp_path / "test.py"
    py_file.write_text("print('hello')", encoding="utf-8")

    js_file = tmp_path / "test.js"
    js_file.write_text("console.log('hello')", encoding="utf-8")

    # Python file should be excluded
    assert should_include(py_file, Path("test.py"), filter_opts, search_opts) is False

    # JavaScript file should be included
    assert should_include(js_file, Path("test.js"), filter_opts, search_opts) is True

def test_should_include_exclude_language_with_reason(tmp_path):
    filter_opts = {}
    search_opts = {'excluded_languages': ['python']}

    py_file = tmp_path / "test.py"
    py_file.write_text("print('hello')", encoding="utf-8")

    include, reason = should_include(py_file, Path("test.py"), filter_opts, search_opts, return_reason=True)
    assert include is False
    assert reason == 'language_excluded'

def test_should_include_allowed_and_excluded_languages(tmp_path):
    filter_opts = {}
    search_opts = {
        'allowed_languages': ['python', 'javascript'],
        'excluded_languages': ['python']
    }

    py_file = tmp_path / "test.py"
    py_file.write_text("print('hello')", encoding="utf-8")

    js_file = tmp_path / "test.js"
    js_file.write_text("console.log('hello')", encoding="utf-8")

    html_file = tmp_path / "test.html"
    html_file.write_text("<html></html>", encoding="utf-8")

    # Python file: matches allowed, but matches excluded -> False
    assert should_include(py_file, Path("test.py"), filter_opts, search_opts) is False

    # JavaScript file: matches allowed, not excluded -> True
    assert should_include(js_file, Path("test.js"), filter_opts, search_opts) is True

    # HTML file: doesn't match allowed -> False (reason language_mismatch)
    include, reason = should_include(html_file, Path("test.html"), filter_opts, search_opts, return_reason=True)
    assert include is False
    assert reason == 'language_mismatch'

def test_exclude_language_cli(tmp_path):
    # Create some test files
    py_file = tmp_path / "test.py"
    py_file.write_text("print('hello')", encoding="utf-8")

    js_file = tmp_path / "test.js"
    js_file.write_text("console.log('hello')", encoding="utf-8")

    output_file = tmp_path / "combined.txt"

    # Run main with --exclude-language python
    test_args = [
        "sourcecombine.py",
        str(tmp_path),
        "-o", str(output_file),
        "--exclude-lang", "python"
    ]

    with patch("sys.argv", test_args):
        main()

    content = output_file.read_text(encoding="utf-8")
    assert "test.js" in content
    assert "test.py" not in content

def test_exclude_language_config(tmp_path):
    # Create some test files
    py_file = tmp_path / "test.py"
    py_file.write_text("print('hello')", encoding="utf-8")

    js_file = tmp_path / "test.js"
    js_file.write_text("console.log('hello')", encoding="utf-8")

    config_file = tmp_path / "sourcecombine.yml"
    config_file.write_text("""
search:
  excluded_languages:
    - python
""", encoding="utf-8")

    output_file = tmp_path / "combined.txt"

    test_args = [
        "sourcecombine.py",
        str(tmp_path),
        "--config", str(config_file),
        "-o", str(output_file)
    ]

    with patch("sys.argv", test_args):
        main()

    content = output_file.read_text(encoding="utf-8")
    assert "test.js" in content
    assert "test.py" not in content

def test_exclude_language_shebang(tmp_path):
    # Create an extensionless file with a python shebang
    script_file = tmp_path / "myscript"
    script_file.write_text("#!/usr/bin/env python3\nprint('hello')", encoding="utf-8")

    filter_opts = {}
    search_opts = {'excluded_languages': ['python']}

    # Should be excluded based on shebang
    assert should_include(script_file, Path("myscript"), filter_opts, search_opts) is False

    # Should be included if we don't exclude python
    assert should_include(script_file, Path("myscript"), filter_opts, {}) is True
