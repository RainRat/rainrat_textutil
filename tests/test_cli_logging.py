import logging
import os
import sys
from unittest.mock import patch, MagicMock
import pytest
from sourcecombine import CLILogFormatter, _LazyColor, C_YELLOW, C_RED, C_DIM, C_RESET

def test_cli_log_formatter_multiline_warning():
    formatter = CLILogFormatter()

    with patch('sys.stderr.isatty', return_value=True), \
         patch.dict(os.environ, {}, clear=True):

        record = logging.LogRecord(
            name="test", level=logging.WARNING, pathname="test.py", lineno=1,
            msg="Line 1\nLine 2", args=(), exc_info=None
        )

        formatted = formatter.format(record)

        lines = formatted.splitlines()
        assert "WARNING:" in lines[0]
        assert lines[0].endswith("Line 1")
        assert lines[1] == "         Line 2"

def test_cli_log_formatter_multiline_error():
    formatter = CLILogFormatter()
    with patch('sys.stderr.isatty', return_value=True), \
         patch.dict(os.environ, {}, clear=True):

        record = logging.LogRecord(
            name="test", level=logging.ERROR, pathname="test.py", lineno=1,
            msg="Err 1\nErr 2", args=(), exc_info=None
        )

        formatted = formatter.format(record)
        lines = formatted.splitlines()
        assert "ERROR:" in lines[0]
        assert lines[1] == "       Err 2"

def test_cli_log_formatter_multiline_debug():
    formatter = CLILogFormatter()
    with patch('sys.stderr.isatty', return_value=True), \
         patch.dict(os.environ, {}, clear=True):

        record = logging.LogRecord(
            name="test", level=logging.DEBUG, pathname="test.py", lineno=1,
            msg="Dbg 1\nDbg 2", args=(), exc_info=None
        )

        formatted = formatter.format(record)
        lines = formatted.splitlines()
        assert "DEBUG:" in lines[0]
        assert lines[1] == "       Dbg 2"

def test_cli_log_formatter_info():
    formatter = CLILogFormatter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="test.py", lineno=1,
        msg="Info message", args=(), exc_info=None
    )
    formatted = formatter.format(record)
    assert formatted == "Info message"

def test_lazy_color_str_mechanics():
    color = _LazyColor("\033[31m")

    with patch('sys.stderr.isatty', return_value=False), \
         patch('sys.stdout.isatty', return_value=False):
        assert str(color) == ""

    with patch('sys.stderr.isatty', return_value=True), \
         patch('os.getenv', side_effect=lambda k, default=None: None if k == "NO_COLOR" else default):
        assert str(color) == "\033[31m"

    with patch('sys.stderr.isatty', return_value=True), \
         patch('os.getenv', side_effect=lambda k, default=None: "1" if k == "NO_COLOR" else default):
        assert str(color) == ""

    with patch('sys.stderr.isatty', return_value=False), \
         patch('sys.stdout.isatty', return_value=True), \
         patch('os.getenv', return_value=None):
        assert str(color) == "\033[31m"

def test_lazy_color_format():
    color = _LazyColor("\033[31m")
    with patch('sys.stderr.isatty', return_value=True), \
         patch('os.getenv', return_value=None):
        formatted = f"{color:s}"
        assert formatted == "\033[31m"
