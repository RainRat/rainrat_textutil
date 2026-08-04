import sys
import os
import argparse
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

from sourcecombine import ColoredArgumentParser

def test_unrecognized_argument_suggestion_single():
    parser = ColoredArgumentParser(prog="test")
    parser.add_argument("--exclude", action="store_true")

    with pytest.raises(SystemExit) as exc:
        with patch("sys.stderr.isatty", return_value=True), patch("os.getenv", return_value=None):
            parser.parse_args(["--exclued"])

    assert exc.value.code == 2

def test_unrecognized_argument_suggestion_no_match():
    parser = ColoredArgumentParser(prog="test")
    parser.add_argument("--exclude", action="store_true")

    with pytest.raises(SystemExit) as exc:
        with patch("sys.stderr.isatty", return_value=True), patch("os.getenv", return_value=None):
            # No option matches `--xyz` sufficiently
            parser.parse_args(["--xyz"])

    assert exc.value.code == 2

def test_unrecognized_argument_suggestion_multiple():
    parser = ColoredArgumentParser(prog="test")
    parser.add_argument("--exclude", action="store_true")
    parser.add_argument("--config", action="store")

    # Check that it handles multiple unrecognized arguments starting with -
    with patch("sys.stderr.write") as mock_write:
        with pytest.raises(SystemExit) as exc:
            with patch("sys.stderr.isatty", return_value=True), patch("os.getenv", return_value=None):
                parser.parse_args(["--exclued", "--configg"])
        assert exc.value.code == 2
        # Check that both suggestions are printed
        called_args = "".join(call[0][0] for call in mock_write.call_args_list)
        assert "Did you mean:" in called_args
        assert "--exclude" in called_args
        assert "--config" in called_args

def test_invalid_choice_suggestion():
    parser = ColoredArgumentParser(prog="test")
    parser.add_argument("--format", choices=["text", "json", "markdown"])

    with patch("sys.stderr.write") as mock_write:
        with pytest.raises(SystemExit) as exc:
            with patch("sys.stderr.isatty", return_value=True), patch("os.getenv", return_value=None):
                parser.parse_args(["--format", "jsn"])
        assert exc.value.code == 2
        called_args = "".join(call[0][0] for call in mock_write.call_args_list)
        assert "Did you mean:" in called_args
        assert "json" in called_args

def test_invalid_choice_suggestion_fallback_quotes():
    parser = ColoredArgumentParser(prog="test")

    # Directly test the fallback quote parsing logic in error() by crafting a custom error message
    with patch("sys.stderr.write") as mock_write:
        with pytest.raises(SystemExit) as exc:
            with patch("sys.stderr.isatty", return_value=True), patch("os.getenv", return_value=None):
                # Simulate Python older versions where the error has quotes
                parser.error("argument --format: invalid choice: 'jsn' (choose from 'text', 'json', 'markdown')")
        assert exc.value.code == 2
        called_args = "".join(call[0][0] for call in mock_write.call_args_list)
        assert "Did you mean:" in called_args
        assert "json" in called_args

def test_invalid_choice_suggestion_fallback_quotes_no_choose_from():
    parser = ColoredArgumentParser(prog="test")

    # Direct test when there is no "choose from" in parentheses but quotes are present
    with patch("sys.stderr.write") as mock_write:
        with pytest.raises(SystemExit) as exc:
            with patch("sys.stderr.isatty", return_value=True), patch("os.getenv", return_value=None):
                parser.error("argument --format: invalid choice: 'jsn' (choices are 'text', 'json', 'markdown')")
        assert exc.value.code == 2
        called_args = "".join(call[0][0] for call in mock_write.call_args_list)
        assert "Did you mean:" in called_args
        assert "json" in called_args

def test_no_color_on_non_tty():
    parser = ColoredArgumentParser(prog="test")
    parser.add_argument("--exclude", action="store_true")

    with patch("sys.stderr.write") as mock_write:
        with pytest.raises(SystemExit) as exc:
            with patch("sys.stderr.isatty", return_value=False), patch("os.getenv", return_value=None):
                parser.parse_args(["--exclued"])
        assert exc.value.code == 2
        called_args = "".join(call[0][0] for call in mock_write.call_args_list)
        assert "\033[1m" not in called_args
        assert "Did you mean: --exclude?" in called_args
