import sys
import os
import argparse
from pathlib import Path
import pytest

sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

from sourcecombine import ColoredArgumentParser

def test_unrecognized_argument_suggestions():
    parser = ColoredArgumentParser(prog="test")
    parser.add_argument("--ext", action="store_true")
    parser.add_argument("--extension", action="store_true")
    parser.add_argument("--extract", action="store_true")

    with pytest.raises(SystemExit) as excinfo:
        parser.parse_args(["--exts"])
    assert excinfo.value.code == 2

def test_unrecognized_argument_suggestions_output(capsys):
    parser = ColoredArgumentParser(prog="test")
    parser.add_argument("--ext", action="store_true")

    with pytest.raises(SystemExit):
        parser.error("unrecognized arguments: --exts")

    captured = capsys.readouterr()
    assert "unrecognized arguments: --exts" in captured.err
    assert "did you mean: --ext" in captured.err

def test_invalid_choice_suggestions(capsys):
    parser = ColoredArgumentParser(prog="test")
    parser.add_argument("--format", "-f", choices=["text", "json", "jsonl"])

    with pytest.raises(SystemExit):
        parser.error("argument --format/-f: invalid choice: 'js'")

    captured = capsys.readouterr()
    assert "Did you mean: json, jsonl" in captured.err

def test_no_suggestions_for_no_match(capsys):
    parser = ColoredArgumentParser(prog="test")
    parser.add_argument("--ext", action="store_true")

    with pytest.raises(SystemExit):
        parser.error("unrecognized arguments: --completelydifferentthing")

    captured = capsys.readouterr()
    assert "unrecognized arguments: --completelydifferentthing" in captured.err
    assert "did you mean" not in captured.err

def test_invalid_choice_no_suggestions_no_match(capsys):
    parser = ColoredArgumentParser(prog="test")
    parser.add_argument("--format", "-f", choices=["text", "json", "jsonl"])

    with pytest.raises(SystemExit):
        parser.error("argument --format/-f: invalid choice: 'completelydifferent'")

    captured = capsys.readouterr()
    assert "Did you mean" not in captured.err
