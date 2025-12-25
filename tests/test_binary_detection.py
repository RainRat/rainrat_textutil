import pytest
from unittest.mock import patch, mock_open
from pathlib import Path
import utils

def test_looks_binary_handles_os_error():
    """Verify that _looks_binary returns False when an OSError occurs during file opening."""
    with patch("builtins.open", side_effect=OSError("Permission denied")):
        assert utils._looks_binary(Path("fake.txt")) is False

def test_looks_binary_returns_false_on_empty_read():
    """Verify that _looks_binary returns False if the file is empty."""
    with patch("builtins.open", mock_open(read_data=b"")):
        assert utils._looks_binary(Path("empty.txt")) is False

def test_looks_binary_true_on_null_byte():
    """Verify that _looks_binary returns True if a null byte is present."""
    # A single null byte should be enough
    with patch("builtins.open", mock_open(read_data=b"text\x00more")):
        assert utils._looks_binary(Path("binary.bin")) is True

def test_looks_binary_true_on_high_control_chars():
    """Verify that _looks_binary returns True if >30% are non-text control characters."""
    # Allowed control chars: 9, 10, 12, 13 (\t, \n, \f, \r)
    # 0x01 is a non-text control char.
    # Create a sample where > 30% are 0x01.
    # 10 bytes: 4 bytes of 0x01, 6 bytes of text. 4/10 = 40% > 30%
    data = b"\x01\x01\x01\x01abcdef"
    with patch("builtins.open", mock_open(read_data=data)):
        assert utils._looks_binary(Path("control.bin")) is True

def test_looks_binary_false_on_text_file():
    """Verify that _looks_binary returns False for a normal text file."""
    data = b"Hello world\nThis is text."
    with patch("builtins.open", mock_open(read_data=data)):
        assert utils._looks_binary(Path("text.txt")) is False

def test_looks_binary_respects_allowed_control_chars():
    """Verify that tabs and newlines do not count as binary control characters."""
    # 10 bytes: 4 bytes of allowed control (e.g. \t), 6 bytes of text.
    # Should be 0% non-text control.
    data = b"\t\t\n\nabcdef"
    with patch("builtins.open", mock_open(read_data=data)):
        assert utils._looks_binary(Path("script.sh")) is False
