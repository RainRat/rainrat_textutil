import json
import sys
from unittest.mock import patch
import pytest
from sourcecombine import main

def test_project_info_json(capsys):
    with patch.object(sys, "argv", ["sourcecombine.py", "--project-info", "--json"]):
        with pytest.raises(SystemExit) as excinfo:
            main()

    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "project_name" in data
    assert "os" in data
    assert "python_version" in data
    assert captured.out.strip().startswith("{")
    assert captured.out.strip().endswith("}")

def test_system_info_json(capsys):
    with patch.dict(sys.modules):
        if "pyperclip" in sys.modules and not hasattr(sys.modules["pyperclip"], "__spec__"):
            del sys.modules["pyperclip"]

        with patch.object(sys, "argv", ["sourcecombine.py", "--system-info", "--json"]):
            with pytest.raises(SystemExit) as excinfo:
                main()

    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "version" in data
    assert "dependencies" in data
    assert captured.out.strip().startswith("{")

def test_list_languages_json(capsys):
    with patch.object(sys, "argv", ["sourcecombine.py", "--list-languages", "--json"]):
        with pytest.raises(SystemExit) as excinfo:
            main()

    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "languages" in data
    assert "total" in data
    assert "python" in data["languages"]
    assert captured.out.strip().startswith("{")

def test_list_placeholders_json(capsys):
    with patch.object(sys, "argv", ["sourcecombine.py", "--list-placeholders", "--json"]):
        with pytest.raises(SystemExit) as excinfo:
            main()

    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "File-Level Placeholders" in data
    assert "{{FILENAME}}" in data["File-Level Placeholders"]
    assert captured.out.strip().startswith("{")

def test_show_config_json(capsys):
    with patch.object(sys, "argv", ["sourcecombine.py", "--show-config", "--json"]):
        with pytest.raises(SystemExit) as excinfo:
            main()

    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "logging" in data
    assert "search" in data
    assert captured.out.strip().startswith("{")
