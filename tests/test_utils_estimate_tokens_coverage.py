import sys
import os
from pathlib import Path

sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

from unittest.mock import MagicMock, patch
import utils

def test_estimate_tokens_with_mocked_tiktoken_success():
    mock_tiktoken = MagicMock()
    mock_encoding = MagicMock()
    mock_encoding.encode.return_value = [1, 2, 3]
    mock_tiktoken.get_encoding.return_value = mock_encoding

    with patch('utils.tiktoken', mock_tiktoken):
        count, is_approx = utils.estimate_tokens("test string", encoding_name="test_encoding")

        assert count == 3
        assert is_approx is False
        mock_tiktoken.get_encoding.assert_called_once_with("test_encoding")
        mock_encoding.encode.assert_called_once_with("test string", disallowed_special=())
