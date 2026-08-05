import sys
import os
import pytest
from pathlib import Path

sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

from sourcecombine import ColoredArgumentParser

def test_colored_argument_parser_unrecognized_suggestion():
    parser = ColoredArgumentParser(prog="test")
    parser.add_argument("--format", choices=["text", "json", "xml"])

    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["--formt"])
    assert exc.value.code == 2

def test_colored_argument_parser_invalid_choice_suggestion():
    parser = ColoredArgumentParser(prog="test")
    parser.add_argument("--format", choices=["text", "json", "xml"])

    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["--format", "jzon"])
    assert exc.value.code == 2

def test_colored_argument_parser_no_suggestion():
    parser = ColoredArgumentParser(prog="test")
    parser.add_argument("--format", choices=["text", "json", "xml"])

    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["--xyzabc"])
    assert exc.value.code == 2

def test_colored_argument_parser_error_direct_unrecognized():
    parser = ColoredArgumentParser(prog="test")
    parser.add_argument("--format", choices=["text", "json", "xml"])

    with pytest.raises(SystemExit) as exc:
        parser.error("unrecognized arguments: --formt")
    assert exc.value.code == 2

def test_colored_argument_parser_error_direct_invalid_choice():
    parser = ColoredArgumentParser(prog="test")
    parser.add_argument("--format", choices=["text", "json", "xml"])

    with pytest.raises(SystemExit) as exc:
        parser.error("argument --format: invalid choice: 'jzon' (choose from 'text', 'json', 'xml')")
    assert exc.value.code == 2

def test_colored_argument_parser_error_direct_invalid_choice_double_quotes():
    parser = ColoredArgumentParser(prog="test")
    parser.add_argument("--format", choices=["text", "json", "xml"])

    with pytest.raises(SystemExit) as exc:
        parser.error('argument --format: invalid choice: "jzon" (choose from "text", "json", "xml")')
    assert exc.value.code == 2

def test_colored_argument_parser_error_non_spelling():
    parser = ColoredArgumentParser(prog="test")
    with pytest.raises(SystemExit) as exc:
        parser.error("some other error message")
    assert exc.value.code == 2
