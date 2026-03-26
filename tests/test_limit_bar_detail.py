import sys; import os; from pathlib import Path; sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))
from unittest.mock import MagicMock, patch
import sourcecombine

def test_limit_bar_detail_tokens(capsys):
    """Test that the token limit bar shows actual values."""
    stats = {
        'total_files': 1,
        'total_size_bytes': 10,
        'files_by_extension': {'.txt': 1},
        'total_tokens': 500,
        'max_total_tokens': 1000,
        'top_files': []
    }

    args = MagicMock()
    args.list_files = False
    args.tree = False
    args.extract = False

    with patch.dict(os.environ, {"NO_COLOR": "1"}):
        sourcecombine._print_execution_summary(stats, args, pairing_enabled=False)

    captured = capsys.readouterr()
    assert "Token Limit:" in captured.err
    assert "[#####-----]   50.0% (500 / 1,000)" in captured.err

def test_limit_bar_detail_size(capsys):
    """Test that the size limit bar shows formatted values."""
    stats = {
        'total_files': 1,
        'total_size_bytes': 1024 * 5, # 5 KB
        'files_by_extension': {'.txt': 1},
        'total_tokens': 0,
        'max_total_size_bytes': 1024 * 10, # 10 KB
        'top_files': []
    }

    args = MagicMock()
    args.list_files = False
    args.tree = False
    args.extract = False

    with patch.dict(os.environ, {"NO_COLOR": "1"}):
        sourcecombine._print_execution_summary(stats, args, pairing_enabled=False)

    captured = capsys.readouterr()
    assert "Size Limit:" in captured.err
    assert "[#####-----]   50.0% (5.00 KB / 10.00 KB)" in captured.err

def test_limit_bar_detail_files(capsys):
    """Test that the file limit bar shows actual values."""
    stats = {
        'total_files': 5,
        'max_files': 10,
        'total_size_bytes': 100,
        'files_by_extension': {'.txt': 5},
        'top_files': []
    }

    args = MagicMock()
    args.list_files = False
    args.tree = False
    args.extract = False

    with patch.dict(os.environ, {"NO_COLOR": "1"}):
        sourcecombine._print_execution_summary(stats, args, pairing_enabled=False)

    captured = capsys.readouterr()
    assert "File Limit:" in captured.err
    assert "[#####-----]   50.0% (5 / 10)" in captured.err
