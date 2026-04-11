import sys; import os; from pathlib import Path; sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))
import utils
import pytest

def test_detect_language_from_shebang_all_interpreters():
    # Test all interpreters mapped in detect_language_from_shebang
    cases = [
        ("#!/usr/bin/python3", "python"),
        ("#!/usr/bin/node", "javascript"),
        ("#!/usr/bin/ruby", "ruby"),
        ("#!/usr/bin/perl", "perl"),
        ("#!/usr/bin/php", "php"),
        ("#!/bin/bash", "bash"),
        ("#!/bin/zsh", "bash"),
        ("#!/bin/sh", "bash"),
        ("#!/usr/bin/groovy", "groovy"),
        ("#!/usr/bin/env node", "javascript"),
    ]
    for content, expected in cases:
        assert utils.detect_language_from_shebang(content) == expected

def test_get_language_tag_precedence():
    # filename > extension with dot > extension without dot
    overrides = {
        "special_name": "special-lang",
        ".ext": "dot-ext-lang",
        "ext": "no-dot-ext-lang"
    }

    # 1. Filename match
    assert utils.get_language_tag("special_name", overrides=overrides) == "special-lang"

    # 2. Extension with dot match
    assert utils.get_language_tag("test.ext", overrides=overrides) == "dot-ext-lang"

    # 3. Extension without dot match
    overrides_no_dot = {"py": "custom-py"}
    assert utils.get_language_tag("test.py", overrides=overrides_no_dot) == "custom-py"

def test_count_lines_edge_cases():
    assert utils.count_lines("") == 0
    assert utils.count_lines("line1") == 1
    assert utils.count_lines("line1\nline2") == 2
    assert utils.count_lines("line1\n") == 1
    assert utils.count_lines("\n") == 1
    assert utils.count_lines("a\nb\n") == 2

def test_get_language_tag_shebang_fallback():
    # Extensionless file with shebang
    content = "#!/usr/bin/node\nconsole.log('hi');"
    assert utils.get_language_tag("my-script", content=content) == "javascript"

    # Recognized extension should still take precedence over shebang
    content_py = "#!/bin/bash\nprint('actually python')"
    assert utils.get_language_tag("test.py", content=content_py) == "python"

def test_get_language_tag_unknown_extension_shebang_fallback():
    content = "#!/usr/bin/ruby\nputs 'hi'"
    assert utils.get_language_tag("test.unknown", content=content) == "ruby"
