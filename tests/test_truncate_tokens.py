import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

# Ensure repo root is on path
sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

from utils import truncate_tokens, process_content

def test_truncate_tokens_no_tiktoken():
    """Test truncation using character-based approximation when tiktoken is missing."""
    with patch('utils.tiktoken', None):
        text = "word " * 100 # 500 characters
        # 10 tokens approx = 40 chars
        truncated = truncate_tokens(text, 10)
        assert len(truncated) == 40
        assert truncated == text[:40]

def test_truncate_tokens_with_tiktoken():
    """Test truncation using tiktoken when available."""
    # We mock tiktoken to avoid dependency on actual encoding behavior in tests
    mock_tiktoken = MagicMock()
    mock_encoding = MagicMock()
    # Mock tokens: each 'word ' is one token
    mock_encoding.encode.return_value = list(range(100))
    mock_encoding.decode.side_effect = lambda tokens: "word " * len(tokens)
    mock_tiktoken.get_encoding.return_value = mock_encoding

    with patch('utils.tiktoken', mock_tiktoken):
        text = "word " * 100
        truncated = truncate_tokens(text, 10)
        assert truncated == "word " * 10
        mock_encoding.encode.assert_called_once()
        mock_encoding.decode.assert_called_once_with(list(range(10)))

def test_truncate_tokens_zero_limit():
    assert truncate_tokens("some text", 0) == "some text"
    assert truncate_tokens("some text", -1) == "some text"

def test_process_content_truncation():
    options = {'max_tokens': 10}
    text = "word " * 100

    # Character fallback: 10 * 4 = 40 chars
    with patch('utils.tiktoken', None):
        processed = process_content(text, options)
        assert len(processed) == 40

def test_process_content_order():
    """Ensure max_lines is applied before max_tokens."""
    text = "line1\nline2\nline3\nline4\nline5"
    # max_lines=2 -> "line1\nline2\n"
    # max_tokens=1 -> character fallback 4 chars -> "line"
    options = {'max_lines': 2, 'max_tokens': 1}

    with patch('utils.tiktoken', None):
        processed = process_content(text, options)
        assert processed == "line"
