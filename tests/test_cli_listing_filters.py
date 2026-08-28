import sys
import os
import io
import json
import pytest
from unittest.mock import patch

from sourcecombine import main, print_languages, print_placeholders

def test_print_languages_unfiltered():
    captured_output = io.StringIO()
    sys.stdout = captured_output
    try:
        print_languages()
    finally:
        sys.stdout = sys.__stdout__
    output = captured_output.getvalue()
    assert "=== SUPPORTED LANGUAGES ===" in output
    assert "python" in output
    assert "javascript" in output

def test_print_languages_filtered_match():
    captured_output = io.StringIO()
    sys.stdout = captured_output
    try:
        print_languages(query="python")
    finally:
        sys.stdout = sys.__stdout__
    output = captured_output.getvalue()
    assert "=== SUPPORTED LANGUAGES (FILTERED BY 'python') ===" in output
    assert "python" in output
    assert "javascript" not in output

def test_print_languages_filtered_no_match():
    captured_output = io.StringIO()
    sys.stdout = captured_output
    try:
        print_languages(query="nonexistentlang12345")
    finally:
        sys.stdout = sys.__stdout__
    output = captured_output.getvalue()
    assert "=== SUPPORTED LANGUAGES (FILTERED BY 'nonexistentlang12345') ===" in output
    assert "No languages matched the filter query 'nonexistentlang12345'." in output
    assert "Matching: 0 languages supported." in output

def test_print_placeholders_unfiltered():
    captured_output = io.StringIO()
    sys.stdout = captured_output
    try:
        print_placeholders()
    finally:
        sys.stdout = sys.__stdout__
    output = captured_output.getvalue()
    assert "=== TEMPLATE PLACEHOLDERS ===" in output
    assert "{{FILENAME}}" in output
    assert "{{GIT_BRANCH}}" in output

def test_print_placeholders_filtered_match():
    captured_output = io.StringIO()
    sys.stdout = captured_output
    try:
        print_placeholders(query="git")
    finally:
        sys.stdout = sys.__stdout__
    output = captured_output.getvalue()
    assert "=== TEMPLATE PLACEHOLDERS (FILTERED BY 'git') ===" in output
    assert "{{GIT_BRANCH}}" in output
    assert "{{FILENAME}}" not in output

def test_print_placeholders_filtered_no_match():
    captured_output = io.StringIO()
    sys.stdout = captured_output
    try:
        print_placeholders(query="nonexistentplaceholder12345")
    finally:
        sys.stdout = sys.__stdout__
    output = captured_output.getvalue()
    assert "=== TEMPLATE PLACEHOLDERS (FILTERED BY 'nonexistentplaceholder12345') ===" in output
    assert "File-Level Placeholders" not in output
    assert "Git Placeholders" not in output
    assert "No template placeholders matched the filter query 'nonexistentplaceholder12345'." in output
    assert "Matching: 0 template placeholders supported." in output

def test_cli_list_languages_filtered(capsys):
    test_args = ["sourcecombine.py", "--list-languages", "python"]
    with patch.object(sys, "argv", test_args):
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 0
    captured = capsys.readouterr()
    assert "=== SUPPORTED LANGUAGES (FILTERED BY 'python') ===" in captured.out
    assert "python" in captured.out
    assert "javascript" not in captured.out

def test_cli_list_languages_filtered_json(capsys):
    test_args = ["sourcecombine.py", "--list-languages", "python", "--json"]
    with patch.object(sys, "argv", test_args):
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "python" in data["languages"]
    assert "javascript" not in data["languages"]
    assert data["total"] == 1

def test_cli_list_placeholders_filtered(capsys):
    test_args = ["sourcecombine.py", "--list-placeholders", "git"]
    with patch.object(sys, "argv", test_args):
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 0
    captured = capsys.readouterr()
    assert "=== TEMPLATE PLACEHOLDERS (FILTERED BY 'git') ===" in captured.out
    assert "{{GIT_BRANCH}}" in captured.out
    assert "{{FILENAME}}" not in captured.out

def test_cli_list_placeholders_filtered_json(capsys):
    test_args = ["sourcecombine.py", "--list-placeholders", "git", "--json"]
    with patch.object(sys, "argv", test_args):
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "Git Placeholders" in data
    assert "File-Level Placeholders" not in data
    assert "{{GIT_BRANCH}}" in data["Git Placeholders"]
