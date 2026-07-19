import sys
import os
import argparse
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

from sourcecombine import ColoredHelpFormatter

def test_colored_help_formatter_heading_coloring():
    formatter = ColoredHelpFormatter(prog="test")
    with patch("sys.stdout.isatty", return_value=True), patch("sys.stderr.isatty", return_value=True), patch("os.getenv", return_value=None):
        formatter.start_section("options")
        formatter.add_text("some text")
        formatter.end_section()
        help_text = formatter.format_help()
        assert "\033[1m\033[36moptions\033[0m" in help_text

def test_colored_help_formatter_heading_no_color():
    formatter = ColoredHelpFormatter(prog="test")
    with patch("sys.stdout.isatty", return_value=False), patch("sys.stderr.isatty", return_value=False), patch("os.getenv", return_value=None):
        formatter.start_section("options")
        formatter.add_text("some text")
        formatter.end_section()
        help_text = formatter.format_help()
        assert "\033[1m\033[36moptions\033[0m" not in help_text
        assert "options" in help_text

def test_colored_help_formatter_action_invocation_positional():
    formatter = ColoredHelpFormatter(prog="test")
    action = argparse.Action(option_strings=[], dest="targets", metavar="TARGET", nargs="*")
    with patch("sys.stdout.isatty", return_value=True), patch("sys.stderr.isatty", return_value=True), patch("os.getenv", return_value=None):
        res = formatter._format_action_invocation(action)
        assert "\033[1m[TARGET ...]\033[0m" in res

def test_colored_help_formatter_action_invocation_positional_no_color():
    formatter = ColoredHelpFormatter(prog="test")
    action = argparse.Action(option_strings=[], dest="targets", metavar="TARGET", nargs="*")
    with patch("sys.stdout.isatty", return_value=False), patch("sys.stderr.isatty", return_value=False), patch("os.getenv", return_value=None):
        res = formatter._format_action_invocation(action)
        assert "\033[1m" not in res
        assert "[TARGET ...]" in res

def test_colored_help_formatter_action_invocation_optional_flag_only():
    formatter = ColoredHelpFormatter(prog="test")
    action = argparse.Action(option_strings=["-v", "--verbose"], dest="verbose", nargs=0)
    with patch("sys.stdout.isatty", return_value=True), patch("sys.stderr.isatty", return_value=True), patch("os.getenv", return_value=None):
        res = formatter._format_action_invocation(action)
        assert "\033[1m-v\033[0m" in res
        assert "\033[1m--verbose\033[0m" in res

def test_colored_help_formatter_action_invocation_optional_flag_with_metavar():
    formatter = ColoredHelpFormatter(prog="test")
    action = argparse.Action(option_strings=["-o", "--output"], dest="output", metavar="PATH", nargs=1)
    with patch("sys.stdout.isatty", return_value=True), patch("sys.stderr.isatty", return_value=True), patch("os.getenv", return_value=None):
        res = formatter._format_action_invocation(action)
        assert "\033[1m-o\033[0m" in res
        assert "\033[90mPATH\033[0m" in res
        assert "\033[1m--output\033[0m" in res

def test_colored_help_formatter_action_invocation_optional_no_color():
    formatter = ColoredHelpFormatter(prog="test")
    action = argparse.Action(option_strings=["-o", "--output"], dest="output", metavar="PATH", nargs=1)
    with patch("sys.stdout.isatty", return_value=False), patch("sys.stderr.isatty", return_value=False), patch("os.getenv", return_value=None):
        res = formatter._format_action_invocation(action)
        assert "\033[1m" not in res
        assert "\033[90m" not in res
        assert "PATH" in res
        assert "-o" in res
        assert "--output" in res

def test_ansi_string_len():
    from sourcecombine import AnsiString
    s = AnsiString("\033[1m-o\033[0m \033[90mPATH\033[0m")
    assert len(s) == 7
    assert s == "\033[1m-o\033[0m \033[90mPATH\033[0m"
