import sys
import os
from unittest.mock import MagicMock
import pytest
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

import utils
from sourcecombine import find_and_combine_files

def test_estimate_tokens_fallback_when_tiktoken_missing(monkeypatch):
    """Verify that estimate_tokens falls back to character count approximation when tiktoken is not available."""
    monkeypatch.setattr(utils, "tiktoken", None)

    text = "12345678"
    # Fallback is len // 4
    count, is_approx = utils.estimate_tokens(text)
    assert count == 2
    assert is_approx is True

def test_estimate_tokens_uses_tiktoken_when_available(monkeypatch):
    """Verify that estimate_tokens uses tiktoken for accurate counting when available."""
    mock_tiktoken = MagicMock()
    mock_encoding = MagicMock()
    # Mock encode returning 3 tokens
    mock_encoding.encode.return_value = [1, 2, 3]
    mock_tiktoken.get_encoding.return_value = mock_encoding

    monkeypatch.setattr(utils, "tiktoken", mock_tiktoken)

    text = "some text"
    count, is_approx = utils.estimate_tokens(text)

    assert count == 3
    assert is_approx is False
    mock_tiktoken.get_encoding.assert_called_with("cl100k_base")
    mock_encoding.encode.assert_called_with(text, disallowed_special=())

def test_estimate_tokens_fallback_on_tiktoken_error(monkeypatch):
    """Verify that estimate_tokens falls back if tiktoken raises an exception."""
    mock_tiktoken = MagicMock()
    mock_tiktoken.get_encoding.side_effect = Exception("Model not found")

    monkeypatch.setattr(utils, "tiktoken", mock_tiktoken)

    text = "1234"
    count, is_approx = utils.estimate_tokens(text)

    # Should fallback
    assert count == 1
    assert is_approx is True

def test_estimate_tokens_empty_string(monkeypatch):
    """Verify that estimate_tokens handles empty strings correctly."""
    monkeypatch.setattr(utils, "tiktoken", None)
    assert utils.estimate_tokens("") == (0, True)

def test_integration_find_and_combine_files_estimates_tokens(tmp_path, monkeypatch):
    """Verify that find_and_combine_files correctly aggregates token counts in stats."""
    # Setup files
    root = tmp_path / "root"
    root.mkdir()
    (root / "file1.txt").write_text("1234", encoding="utf-8") # 4 chars -> 1 token (approx)
    (root / "file2.txt").write_text("5678", encoding="utf-8") # 4 chars -> 1 token (approx)

    # Force fallback mode so we have deterministic counts
    monkeypatch.setattr(utils, "tiktoken", None)

    config = {
        "search": {"root_folders": [str(root)]},
        "output": {
            "file": str(tmp_path / "out.txt"),
            "header_template": "",
            "footer_template": "",
        }
    }

    stats = find_and_combine_files(
        config,
        output_path=str(tmp_path / "out.txt"),
        estimate_tokens=True
    )

    # 1 token per file * 2 files = 2 tokens
    assert stats['total_tokens'] == 2
    assert stats['token_count_is_approx'] is True
    assert stats['total_files'] == 2

def test_integration_estimate_tokens_with_mocked_tiktoken(tmp_path, monkeypatch):
    """Verify integration with a mocked tiktoken returning exact values."""
    root = tmp_path / "root"
    root.mkdir()
    (root / "file1.txt").write_text("content", encoding="utf-8")

    mock_tiktoken = MagicMock()
    mock_encoding = MagicMock()
    # Return 10 tokens for any non-empty input
    mock_encoding.encode.side_effect = lambda text, **kwargs: list(range(10)) if text else []
    mock_tiktoken.get_encoding.return_value = mock_encoding

    monkeypatch.setattr(utils, "tiktoken", mock_tiktoken)

    config = {
        "search": {"root_folders": [str(root)]},
        "output": {
            "file": str(tmp_path / "out.txt"),
            "header_template": "",
            "footer_template": "",
        }
    }

    stats = find_and_combine_files(
        config,
        output_path=str(tmp_path / "out.txt"),
        estimate_tokens=True
    )

    assert stats['total_tokens'] == 10
    assert stats['token_count_is_approx'] is False
