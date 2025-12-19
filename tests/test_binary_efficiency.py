import pytest
from unittest.mock import MagicMock, patch, mock_open
from pathlib import Path
import utils

def test_looks_binary_reads_only_prefix():
    """
    Verifies that _looks_binary does not read the entire file using read_bytes().
    It must use open() with a limited read to avoid loading large files into memory.
    """
    # Use a dummy path
    p = Path("fake.file")

    # Patch Path.read_bytes to intercept calls to it.
    with patch("pathlib.Path.read_bytes") as mock_read_bytes:
        # Patch builtins.open to mock file opening.
        # We set read_data to a small byte string to simulate a file content.
        m_open = mock_open(read_data=b"some content")
        with patch("builtins.open", m_open):
            utils._looks_binary(p)

            # The test: read_bytes should NOT be called.
            # Currently (before fix), this assertion will fail.
            mock_read_bytes.assert_not_called()

            # Verify that we are indeed using open()
            # After fix, this should pass.
            m_open.assert_called()
