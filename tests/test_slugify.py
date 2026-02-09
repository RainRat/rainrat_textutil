import os
import sys
from pathlib import Path
import re
import pytest

sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

from sourcecombine import _slugify_relative_dir

def test_slugify_basic_folders():
    assert _slugify_relative_dir("src") == "src"
    assert _slugify_relative_dir("src/lib") == "src/lib"
    assert _slugify_relative_dir("a/b/c") == "a/b/c"

def test_slugify_mixed_case():
    assert _slugify_relative_dir("Src") == "src"
    assert _slugify_relative_dir("SRC/Lib") == "src/lib"

def test_slugify_special_chars():
    assert _slugify_relative_dir("src/Hello World") == "src/hello-world"
    assert _slugify_relative_dir("src/foo@bar") == "src/foo-bar"
    assert _slugify_relative_dir("src/v1.2") == "src/v1.2"
    assert _slugify_relative_dir("src/main_files") == "src/main_files"

def test_slugify_multiple_separators():
    # 'foo--bar' -> 'foo-bar' (deduplicated dashes)
    assert _slugify_relative_dir("src/foo--bar") == "src/foo-bar"
    # 'foo  bar' -> 'foo-bar'
    assert _slugify_relative_dir("src/foo  bar") == "src/foo-bar"

def test_slugify_empty_components():
    assert _slugify_relative_dir("src//lib") == "src/unnamed/lib"
    assert _slugify_relative_dir("src/") == "src/unnamed"
    assert _slugify_relative_dir("/src") == "unnamed/src"

def test_slugify_root_and_dots():
    assert _slugify_relative_dir(".") == "root"
    assert _slugify_relative_dir("") == "root"

    # Path traversal safety
    assert _slugify_relative_dir("..") == "dot-dot"
    assert _slugify_relative_dir("../src") == "dot-dot/src"
    # Single dot as component
    assert _slugify_relative_dir("src/.") == "src/dot"

def test_slugify_unicode():
    # 'café' -> 'caf' (é replaced by -, then stripped)
    assert _slugify_relative_dir("src/café") == "src/caf"

    # '你好' -> 'unnamed' (all chars replaced -> --- -> stripped -> empty -> unnamed)
    assert _slugify_relative_dir("src/你好") == "src/unnamed"

def test_slugify_all_invalid():
    assert _slugify_relative_dir("!@#$%^") == "unnamed"
    assert _slugify_relative_dir("src/!@#") == "src/unnamed"
