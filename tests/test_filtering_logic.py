import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

from sourcecombine import should_include


def test_should_include_returns_not_file_reason(tmp_path):
    folder = tmp_path / "subdir"
    folder.mkdir()

    result = should_include(
        folder,
        folder.relative_to(tmp_path),
        filter_opts={},
        search_opts={},
        return_reason=True,
    )
    assert result == (False, 'not_file')


def test_should_include_returns_excluded_reason(tmp_path):
    file_path = tmp_path / "excluded.txt"
    file_path.touch()

    filter_opts = {
        'exclusions': {
            'filenames': ['*.txt']
        }
    }

    result = should_include(
        file_path,
        file_path.relative_to(tmp_path),
        filter_opts=filter_opts,
        search_opts={},
        return_reason=True,
    )
    assert result == (False, 'excluded')


def test_should_include_returns_extension_reason(tmp_path):
    file_path = tmp_path / "script.py"
    file_path.touch()

    search_opts = {
        'effective_allowed_extensions': ('.c', '.h')
    }

    result = should_include(
        file_path,
        file_path.relative_to(tmp_path),
        filter_opts={},
        search_opts=search_opts,
        return_reason=True,
    )
    assert result == (False, 'extension')


def test_should_include_returns_not_included_reason(tmp_path):
    file_path = tmp_path / "unknown.txt"
    file_path.touch()

    filter_opts = {
        'inclusion_groups': {
            'group1': {
                'enabled': True,
                'filenames': ['*.py']
            }
        }
    }

    result = should_include(
        file_path,
        file_path.relative_to(tmp_path),
        filter_opts=filter_opts,
        search_opts={},
        return_reason=True,
    )
    assert result == (False, 'not_included')


def test_should_include_returns_binary_reason(tmp_path):
    file_path = tmp_path / "binary.bin"
    # Write a null byte to make it look binary
    file_path.write_bytes(b'\x00\x00\x00\x00')

    filter_opts = {
        'skip_binary': True
    }

    result = should_include(
        file_path,
        file_path.relative_to(tmp_path),
        filter_opts=filter_opts,
        search_opts={},
        return_reason=True,
    )
    assert result == (False, 'binary')


def test_should_include_returns_stat_error_reason(tmp_path):
    file_path = tmp_path / "test.txt"
    file_path.touch()

    # Mock stat to raise OSError, but is_file to return True (simulating a race condition or odd perm state)
    # Note: is_file normally calls stat, so we must mock is_file to bypass the failed stat call
    with patch.object(Path, 'stat', side_effect=OSError("Disk error")):
        with patch.object(Path, 'is_file', return_value=True):
            result = should_include(
                file_path,
                file_path.relative_to(tmp_path),
                filter_opts={'min_size_bytes': 10},
                search_opts={},
                return_reason=True,
            )
            assert result == (False, 'stat_error')


def test_should_include_returns_too_small_reason(tmp_path):
    file_path = tmp_path / "small.txt"
    file_path.write_text("123", encoding='utf-8')

    filter_opts = {
        'min_size_bytes': 10
    }

    result = should_include(
        file_path,
        file_path.relative_to(tmp_path),
        filter_opts=filter_opts,
        search_opts={},
        return_reason=True,
    )
    assert result == (False, 'too_small')


def test_should_include_returns_too_large_reason(tmp_path):
    file_path = tmp_path / "large.txt"
    file_path.write_text("1234567890", encoding='utf-8')

    filter_opts = {
        'max_size_bytes': 5
    }

    result = should_include(
        file_path,
        file_path.relative_to(tmp_path),
        filter_opts=filter_opts,
        search_opts={},
        return_reason=True,
    )
    assert result == (False, 'too_large')


def test_should_include_returns_true_when_accepted(tmp_path):
    file_path = tmp_path / "accepted.txt"
    file_path.touch()

    result = should_include(
        file_path,
        file_path.relative_to(tmp_path),
        filter_opts={},
        search_opts={},
        return_reason=True,
    )
    assert result == (True, None)
