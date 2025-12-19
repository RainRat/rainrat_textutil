import logging
from unittest.mock import patch, MagicMock
import pytest
from pathlib import Path
from utils import read_file_best_effort

def test_read_file_best_effort_retries_on_null_bytes_in_utf8(tmp_path):
    """Verify that a file which decodes as UTF-8 but contains null bytes triggers the retry logic (reading bytes)."""
    f = tmp_path / "nulls.txt"
    # Valid UTF-8 with a null byte
    content_bytes = b"hello\x00world"
    f.write_bytes(content_bytes)

    # We patch read_bytes to ensure we actually hit the fallback path.
    # If the initial open() worked and returned, read_bytes wouldn't be called.
    with patch("pathlib.Path.read_bytes", return_value=content_bytes) as mock_read:
        content = read_file_best_effort(f)
        assert content == "hello\x00world"
        mock_read.assert_called_once()

def test_read_file_raises_file_not_found(tmp_path):
    f = tmp_path / "nonexistent.txt"
    with pytest.raises(FileNotFoundError):
        read_file_best_effort(f)

def test_read_file_handles_read_bytes_exception(tmp_path):
    f = tmp_path / "unreadable.txt"
    f.write_bytes(b"\x00") # Force UnicodeError

    with patch("pathlib.Path.read_bytes", side_effect=PermissionError("Boom")), \
         patch("logging.warning") as mock_log:
        content = read_file_best_effort(f)
        assert content == ""

        # Ensure log was called
        assert mock_log.called, "logging.warning should have been called"
        args, _ = mock_log.call_args
        assert "Could not read" in args[0]

def test_read_file_heuristic_small_utf16_no_nulls(tmp_path):
    """
    If charset-normalizer guesses UTF-16 for a small file without BOM or nulls,
    we should fallback to latin-1 to avoid spurious UTF-16 classification.
    """
    f = tmp_path / "tricky.txt"
    f.write_bytes(b"\x20\xAC")

    mock_guess = MagicMock()
    mock_guess.best.return_value.encoding = "utf-16" # Hyphenated!

    with patch("utils.from_bytes", return_value=mock_guess):
        content = read_file_best_effort(f)
        # Should use latin-1 because of the fix
        # b"\x20\xAC".decode("latin-1") -> " \u00ac"
        assert content == " \u00ac"

def test_read_file_heuristic_small_utf16_with_nulls(tmp_path):
    """
    If the file has nulls, we respect the UTF-16 guess even if small.
    """
    f = tmp_path / "utf16_small.txt"
    # Use Little Endian 'a' -> 61 00. b'a\x00'
    data = b"\x61\x00"
    f.write_bytes(data)

    mock_guess = MagicMock()
    mock_guess.best.return_value.encoding = "utf-16"

    with patch("utils.from_bytes", return_value=mock_guess):
        content = read_file_best_effort(f)
        assert content == "a"

def test_read_file_fallback_lookup_error(tmp_path):
    f = tmp_path / "weird.txt"
    f.write_bytes(b"\x80") # Invalid UTF-8 to force detection logic

    mock_guess = MagicMock()
    mock_guess.best.return_value.encoding = "super-fake-encoding"

    with patch("utils.from_bytes", return_value=mock_guess), \
         patch("logging.warning") as mock_log:
        content = read_file_best_effort(f)
        assert content == "\ufffd"

        # Check that we logged the lookup error
        assert mock_log.called, "logging.warning should have been called for lookup error"
        found = any("is not supported" in str(arg) for call in mock_log.call_args_list for arg in call.args)
        assert found

def test_read_file_fallback_no_guess(tmp_path):
    f = tmp_path / "unknown.txt"
    f.write_bytes(b"\x80")

    mock_guess = MagicMock()
    mock_guess.best.return_value = None

    with patch("utils.from_bytes", return_value=mock_guess), \
         patch("logging.warning") as mock_log:
        content = read_file_best_effort(f)
        assert content == "\ufffd"
        found = any("Could not detect encoding" in str(arg) for call in mock_log.call_args_list for arg in call.args)
        assert found
