import sys
import os
import re
from pathlib import Path
import pytest
from unittest.mock import patch

sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

from sourcecombine import ColoredArgumentParser, main, C_BOLD, C_RED, C_CYAN, C_RESET

@pytest.fixture(autouse=True)
def force_color():
    """Fixture to force color output in tests by mocking _LazyColor._render."""
    with patch('sourcecombine._LazyColor._render', lambda self, only_stderr=False: self.code):
        yield

def test_colored_argument_parser_unrecognized_direct(capsys):
    parser = ColoredArgumentParser(prog="sourcecombine.py")
    parser.add_argument("--extension", "--ext")
    parser.add_argument("--exclude-folder")

    with pytest.raises(SystemExit) as excinfo:
        parser.parse_args(["--extensioooo"])
    assert excinfo.value.code == 2

    captured = capsys.readouterr()
    # Strip escape codes to assert text easily
    stripped_err = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', captured.err)
    assert "error: unrecognized arguments: --extensioooo" in stripped_err
    assert "Did you mean: --extension?" in stripped_err

    # Assert color codes exist in raw output
    assert "\x1b[" in captured.err

def test_colored_argument_parser_invalid_choice_direct(capsys):
    parser = ColoredArgumentParser(prog="sourcecombine.py")
    parser.add_argument("--format", choices=["text", "json", "markdown"])

    with pytest.raises(SystemExit) as excinfo:
        parser.parse_args(["--format", "textt"])
    assert excinfo.value.code == 2

    captured = capsys.readouterr()
    stripped_err = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', captured.err)
    assert "invalid choice: 'textt'" in stripped_err
    assert "Did you mean choice: text?" in stripped_err
    assert "\x1b[" in captured.err

def test_colored_argument_parser_no_suggestion_direct(capsys):
    parser = ColoredArgumentParser(prog="sourcecombine.py")
    parser.add_argument("--format", choices=["text", "json", "markdown"])

    with pytest.raises(SystemExit) as excinfo:
        parser.parse_args(["--format", "very_different_value"])
    assert excinfo.value.code == 2

    captured = capsys.readouterr()
    stripped_err = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', captured.err)
    assert "invalid choice: 'very_different_value'" in stripped_err
    assert "Did you mean choice:" not in stripped_err

def test_main_unrecognized_argument_integration(capsys):
    # Test unrecognized argument integration with main() via mocked sys.argv
    with patch.object(sys, 'argv', ['sourcecombine.py', '--extensioooo']):
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 2

    captured = capsys.readouterr()
    stripped_err = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', captured.err)
    assert "error: unrecognized arguments: --extensioooo" in stripped_err
    assert "Did you mean: --extension, --exclude-extension?" in stripped_err

def test_main_invalid_choice_integration(capsys):
    # Test invalid choice integration with main() via mocked sys.argv
    with patch.object(sys, 'argv', ['sourcecombine.py', '--format', 'textt']):
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 2

    captured = capsys.readouterr()
    stripped_err = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', captured.err)
    assert "invalid choice: 'textt'" in stripped_err
    assert "Did you mean choice: text?" in stripped_err
