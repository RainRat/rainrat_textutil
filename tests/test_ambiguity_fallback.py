import os
import sys
from pathlib import Path
import pytest

# Ensure we can import sourcecombine from parent directory
sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

from sourcecombine import _select_preferred_path

def test_select_preferred_path_skips_ambiguity():
    """
    Test that if the first preferred extension is ambiguous (multiple files),
    the function skips it and checks the next preferred extension.
    """
    # Setup:
    # .c is ambiguous (2 files)
    # .cc is unambiguous (1 file)
    ext_map = {
        '.c': [Path('dir1/foo.c'), Path('dir2/foo.c')],
        '.cc': [Path('dir1/foo.cc')],
    }
    preferred_exts = ['.c', '.cc']

    # Execution
    result = _select_preferred_path(ext_map, preferred_exts)

    # Verification
    # Before fix: returned None (stopped at .c)
    # After fix: returns dir1/foo.cc (skipped .c, found .cc)
    assert result is not None
    assert str(result) == os.path.join('dir1', 'foo.cc')

def test_select_preferred_path_returns_none_if_all_ambiguous():
    """
    Test that if all preferred extensions are ambiguous, it returns None.
    """
    ext_map = {
        '.c': [Path('dir1/foo.c'), Path('dir2/foo.c')],
        '.cc': [Path('dir1/foo.cc'), Path('dir2/foo.cc')],
    }
    preferred_exts = ['.c', '.cc']

    result = _select_preferred_path(ext_map, preferred_exts)
    assert result is None

def test_select_preferred_path_returns_first_unambiguous():
    """
    Test that it returns the first unambiguous match, respecting order.
    """
    ext_map = {
        '.c': [Path('dir1/foo.c')],
        '.cc': [Path('dir1/foo.cc')],
    }
    preferred_exts = ['.c', '.cc']

    result = _select_preferred_path(ext_map, preferred_exts)
    assert str(result) == os.path.join('dir1', 'foo.c')

def test_select_preferred_path_handles_missing_extensions():
    """
    Test that it skips extensions not present in the map.
    """
    ext_map = {
        '.cc': [Path('dir1/foo.cc')],
    }
    preferred_exts = ['.c', '.cc']

    result = _select_preferred_path(ext_map, preferred_exts)
    assert str(result) == os.path.join('dir1', 'foo.cc')
