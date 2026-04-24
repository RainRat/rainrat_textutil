import logging
import sys
from sourcecombine import CLILogFormatter

def test_formatter_with_exc_info_and_newline():
    formatter = CLILogFormatter()
    try:
        raise ValueError("test error")
    except ValueError:
        exc_info = sys.exc_info()

    record = logging.LogRecord(
        name="test",
        level=logging.ERROR,
        pathname="test.py",
        lineno=1,
        msg="Error occurred\n",
        args=(),
        exc_info=exc_info
    )

    formatted = formatter.format(record)
    assert "Error occurred\n" in formatted
    assert "ValueError: test error" in formatted

def test_formatter_with_stack_info_and_newline():
    formatter = CLILogFormatter()

    record = logging.LogRecord(
        name="test",
        level=logging.ERROR,
        pathname="test.py",
        lineno=1,
        msg="Stack trace follows\n",
        args=(),
        exc_info=None,
    )
    record.stack_info = "fake stack info"

    formatted = formatter.format(record)
    assert "Stack trace follows\n" in formatted
    assert "fake stack info" in formatted

def test_formatter_multiline_with_prefix():
    formatter = CLILogFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.WARNING,
        pathname="test.py",
        lineno=1,
        msg="Line 1\nLine 2",
        args=(),
        exc_info=None
    )

    formatted = formatter.format(record)
    assert "WARNING: Line 1" in formatted
    assert "        Line 2" in formatted
