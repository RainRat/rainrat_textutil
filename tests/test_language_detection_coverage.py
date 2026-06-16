import pytest
from pathlib import Path
from utils import (
    detect_language_from_shebang,
    get_language_tag,
    get_all_languages,
    count_lines,
    add_line_numbers,
    remove_line_numbers
)

def test_count_lines():
    assert count_lines("") == 0
    assert count_lines("one") == 1
    assert count_lines("one\ntwo") == 2
    assert count_lines("one\ntwo\n") == 2

def test_detect_language_from_shebang_edge_cases():
    assert detect_language_from_shebang("") is None
    assert detect_language_from_shebang("no shebang") is None
    assert detect_language_from_shebang("#!/usr/bin/unknown") is None

def test_detect_language_from_shebang_interpreters():
    assert detect_language_from_shebang("#!/usr/bin/python3") == "python"
    assert detect_language_from_shebang("#!/usr/bin/node") == "javascript"
    assert detect_language_from_shebang("#!/usr/bin/ruby") == "ruby"
    assert detect_language_from_shebang("#!/usr/bin/perl") == "perl"
    assert detect_language_from_shebang("#!/usr/bin/php") == "php"
    assert detect_language_from_shebang("#!/bin/bash") == "bash"
    assert detect_language_from_shebang("#!/bin/zsh") == "bash"
    assert detect_language_from_shebang("#!/bin/sh") == "bash"
    assert detect_language_from_shebang("#!/usr/bin/groovy") == "groovy"

def test_get_language_tag_overrides():
    overrides = {
        "makefile": "make",
        ".special": "special-lang",
        "no-dot": "no-dot-lang"
    }
    # Filename override
    assert get_language_tag("Makefile", overrides=overrides) == "make"
    # Extension with dot
    assert get_language_tag("test.special", overrides=overrides) == "special-lang"
    # Extension without dot
    assert get_language_tag("test.no-dot", overrides=overrides) == "no-dot-lang"

def test_get_language_tag_shebang_integration():
    # Extensionless file with shebang
    assert get_language_tag("script", content="#!/usr/bin/python") == "python"
    # Unrecognized extension with shebang
    assert get_language_tag("script.xyz", content="#!/usr/bin/node") == "javascript"
    # Fallback to text for extensionless no shebang
    assert get_language_tag("README") == "text"
    # Fallback to extension for unrecognized no shebang
    assert get_language_tag("test.xyz") == "xyz"

def test_get_all_languages():
    langs = get_all_languages()
    assert isinstance(langs, list)
    assert len(langs) > 0
    assert "python" in langs
    assert langs == sorted(langs)

def test_add_line_numbers_newline_edge_case():
    text = "line1\nline2\n"
    result = add_line_numbers(text)
    assert result == "1: line1\n2: line2\n"

    text_no_newline = "line1\nline2"
    result_no_newline = add_line_numbers(text_no_newline)
    assert result_no_newline == "1: line1\n2: line2"

def test_remove_line_numbers_edge_cases():
    # Empty string
    assert remove_line_numbers("") == ""

    # Newline preservation
    text = "1: line1\n2: line2\n"
    result = remove_line_numbers(text)
    assert result == "line1\nline2\n"

    # Not enough matches
    text_few = "1: line1\nline2\nline3"
    assert remove_line_numbers(text_few) == text_few
