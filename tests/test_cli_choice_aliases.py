import pytest
from unittest.mock import patch
from sourcecombine import main, parse_sort_choice, parse_format_choice


def test_parse_sort_choice_unit():
    assert parse_sort_choice("date") == "modified"
    assert parse_sort_choice("time") == "modified"
    assert parse_sort_choice("mtime") == "modified"
    assert parse_sort_choice("lang") == "language"
    assert parse_sort_choice("token") == "tokens"
    assert parse_sort_choice("line") == "lines"
    assert parse_sort_choice("SIZE") == "size"
    assert parse_sort_choice("Language") == "language"
    assert parse_sort_choice("unknown") == "unknown"
    assert parse_sort_choice(123) == 123


def test_parse_format_choice_unit():
    assert parse_format_choice("md") == "markdown"
    assert parse_format_choice("txt") == "text"
    assert parse_format_choice("JSON") == "json"
    assert parse_format_choice("Xml") == "xml"
    assert parse_format_choice("unknown") == "unknown"
    assert parse_format_choice(123) == 123


def test_cli_sort_aliases(capsys):
    test_cases = [
        ("date", "modified"),
        ("time", "modified"),
        ("mtime", "modified"),
        ("lang", "language"),
        ("token", "tokens"),
        ("line", "lines"),
        ("SIZE", "size"),
    ]
    for input_sort, expected in test_cases:
        with patch("sys.argv", ["sourcecombine.py", "--sort", input_sort, "--show-config"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0
            captured = capsys.readouterr()
            assert f'"sort_by": "{expected}"' in captured.out or f'sort_by: {expected}' in captured.out


def test_cli_format_aliases(capsys):
    test_cases = [
        ("md", "markdown"),
        ("txt", "text"),
        ("JSON", "json"),
        ("Xml", "xml"),
    ]
    for input_fmt, expected in test_cases:
        with patch("sys.argv", ["sourcecombine.py", "--format", input_fmt, "--show-config"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0
            captured = capsys.readouterr()
            assert f'"format": "{expected}"' in captured.out or f'format: {expected}' in captured.out
