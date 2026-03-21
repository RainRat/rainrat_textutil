import pytest
from pathlib import Path, PurePath
from sourcecombine import should_include

def test_should_include_nested_folder_exclusion():
    """Verify that a folder exclusion pattern (e.g., 'src/gen') excludes subfolders (e.g., 'src/gen/assets')."""
    filter_opts = {
        'exclusions': {
            'folders': ['src/generated']
        }
    }
    search_opts = {}

    # 1. Direct parent matches
    rel_path = PurePath("src/generated/file.txt")
    include, reason = should_include(None, rel_path, filter_opts, search_opts, return_reason=True)
    assert include is False
    assert reason == 'excluded'

    # 2. Grandparent matches
    rel_path = PurePath("src/generated/assets/data.json")
    include, reason = should_include(None, rel_path, filter_opts, search_opts, return_reason=True)
    assert include is False
    assert reason == 'excluded'

    # 3. Deeply nested grandparent matches
    rel_path = PurePath("src/generated/sub/deep/folder/test.py")
    include, reason = should_include(None, rel_path, filter_opts, search_opts, return_reason=True)
    assert include is False
    assert reason == 'excluded'

    # 4. Similar but non-matching path should be included
    rel_path = PurePath("src/other/file.txt")
    include = should_include(None, rel_path, filter_opts, search_opts)
    assert include is True

def test_should_include_folder_pattern_with_wildcards():
    """Verify folder exclusion patterns with wildcards match nested descendants."""
    filter_opts = {
        'exclusions': {
            'folders': ['build-*', 'dist/v[0-9]']
        }
    }
    search_opts = {}

    # Build folder with suffix
    rel_path = PurePath("build-prod/assets/bundle.js")
    include, reason = should_include(None, rel_path, filter_opts, search_opts, return_reason=True)
    assert include is False
    assert reason == 'excluded'

    # Dist folder with version number
    rel_path = PurePath("dist/v1/app.py")
    include, reason = should_include(None, rel_path, filter_opts, search_opts, return_reason=True)
    assert include is False
    assert reason == 'excluded'

def test_should_include_folder_part_match_remains_intact():
    """Verify that the existing 'any part' folder matching still works (e.g., '.git')."""
    filter_opts = {
        'exclusions': {
            'folders': ['.git']
        }
    }
    search_opts = {}

    # File inside a folder named '.git' anywhere in the path
    rel_path = PurePath("vendor/lib/.git/config")
    include, reason = should_include(None, rel_path, filter_opts, search_opts, return_reason=True)
    assert include is False
    assert reason == 'excluded'
