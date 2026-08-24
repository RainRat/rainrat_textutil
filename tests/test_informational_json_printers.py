import json
import sys
from unittest.mock import patch
import pytest

from sourcecombine import (
    main,
    print_system_info,
    print_placeholders,
    print_languages,
    print_project_info,
)


def test_print_system_info_json(capsys):
    print_system_info(json_format=True)
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "version" in data
    assert "python" in data
    assert "platform" in data
    assert "dependencies" in data


def test_print_placeholders_json(capsys):
    print_placeholders(json_format=True)
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "File-Level Placeholders" in data
    assert "{{FILENAME}}" in data["File-Level Placeholders"]


def test_print_placeholders_json_query(capsys):
    print_placeholders(query="FILENAME", json_format=True)
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "File-Level Placeholders" in data
    assert "{{FILENAME}}" in data["File-Level Placeholders"]


def test_print_languages_json(capsys):
    print_languages(json_format=True)
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "languages" in data
    assert "python" in data["languages"]
    assert data["total"] > 0


def test_print_languages_json_query(capsys):
    print_languages(query="python", json_format=True)
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "languages" in data
    assert "python" in data["languages"]


def test_print_project_info_json(capsys):
    sample_stats = {
        "project_name": "TestApp",
        "project_version": "1.0.0",
        "os": "Linux",
    }
    print_project_info(sample_stats, json_format=True)
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["project_name"] == "TestApp"
    assert data["project_version"] == "1.0.0"
    assert data["os"] == "Linux"


def test_cli_system_info_json(capsys):
    with patch.object(sys, "argv", ["sourcecombine.py", "--system-info", "--json"]):
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "version" in data
    assert "dependencies" in data


def test_cli_project_info_json(capsys):
    with patch.object(sys, "argv", ["sourcecombine.py", "--project-info", "--json"]):
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "project_name" in data


def test_cli_list_placeholders_json(capsys):
    with patch.object(
        sys, "argv", ["sourcecombine.py", "--list-placeholders", "--json"]
    ):
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "File-Level Placeholders" in data


def test_cli_list_languages_json(capsys):
    with patch.object(
        sys, "argv", ["sourcecombine.py", "--list-languages", "--json"]
    ):
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "languages" in data
