import sys
from unittest.mock import patch
import pytest
from sourcecombine import ColoredArgumentParser


def test_colored_argument_parser_standard_error(capsys):
    parser = ColoredArgumentParser(prog="testprog")

    with pytest.raises(SystemExit) as exc_info:
        parser.error("some random error")

    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "testprog" in captured.err
    assert "error:" in captured.err
    assert "some random error" in captured.err


def test_colored_argument_parser_unrecognized_argument_no_suggestions(capsys):
    parser = ColoredArgumentParser(prog="testprog")
    parser.add_argument("--foo")

    with pytest.raises(SystemExit) as exc_info:
        # A very distant typo that difflib cutoff 0.6 won't match
        parser.error("unrecognized arguments: --xyz")

    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "unrecognized arguments: --xyz" in captured.err
    assert "Suggestions" not in captured.err


def test_colored_argument_parser_unrecognized_argument_with_suggestions(capsys):
    parser = ColoredArgumentParser(prog="testprog")
    parser.add_argument("--config")
    parser.add_argument("--extension")

    with pytest.raises(SystemExit) as exc_info:
        # Close match for --config
        parser.error("unrecognized arguments: --conf")

    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "unrecognized arguments: --conf" in captured.err
    assert "Suggestions:" in captured.err
    assert "--config" in captured.err


def test_colored_argument_parser_invalid_choice_no_suggestions(capsys):
    parser = ColoredArgumentParser(prog="testprog")
    parser.add_argument("--format", choices=["text", "markdown"])

    with pytest.raises(SystemExit) as exc_info:
        # Too far off from choices
        parser.error("argument --format: invalid choice: 'xyz' (choose from 'text', 'markdown')")

    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "invalid choice: 'xyz'" in captured.err
    assert "Did you mean:" not in captured.err


def test_colored_argument_parser_invalid_choice_with_suggestions(capsys):
    parser = ColoredArgumentParser(prog="testprog")
    parser.add_argument("--format", choices=["text", "markdown", "json"])

    with pytest.raises(SystemExit) as exc_info:
        # Close match to markdown
        parser.error("argument --format: invalid choice: 'mark' (choose from 'text', 'markdown', 'json')")

    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "invalid choice: 'mark'" in captured.err
    assert "Did you mean:" in captured.err
    assert "markdown" in captured.err
