import json
import sys
import importlib.util
from unittest.mock import patch
import pytest
from sourcecombine import main

def test_project_info_json(capsys):
    with patch.object(sys, 'argv', ["sourcecombine.py", "--project-info", "--json"]):
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 0

    out, err = capsys.readouterr()
    data = json.loads(out)
    assert "project_name" in data
    assert "os" in data
    assert "python_version" in data
    # Ensure no logging noise in stdout
    assert out.strip().startswith("{")
    assert out.strip().endswith("}")

def test_system_info_json(capsys):
    # Fix for pyperclip stub in test_sourcecombine.py causing ValueError in find_spec
    if "pyperclip" in sys.modules and not hasattr(sys.modules["pyperclip"], "__spec__"):
        try:
            sys.modules["pyperclip"].__spec__ = importlib.util.spec_from_loader("pyperclip", None)
        except Exception:
            pass

    with patch.object(sys, 'argv', ["sourcecombine.py", "--system-info", "--json"]):
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 0

    out, err = capsys.readouterr()
    data = json.loads(out)
    assert "version" in data
    assert "dependencies" in data
    assert out.strip().startswith("{")
    assert out.strip().endswith("}")

def test_list_languages_json(capsys):
    with patch.object(sys, 'argv', ["sourcecombine.py", "--list-languages", "--json"]):
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 0

    out, err = capsys.readouterr()
    data = json.loads(out)
    assert "languages" in data
    assert "total" in data
    assert "python" in data["languages"]
    assert out.strip().startswith("{")
    assert out.strip().endswith("}")

def test_list_placeholders_json(capsys):
    with patch.object(sys, 'argv', ["sourcecombine.py", "--list-placeholders", "--json"]):
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 0

    out, err = capsys.readouterr()
    data = json.loads(out)
    assert "File-Level Placeholders" in data
    assert "{{FILENAME}}" in data["File-Level Placeholders"]
    assert out.strip().startswith("{")
    assert out.strip().endswith("}")

def test_show_config_json(capsys):
    with patch.object(sys, 'argv', ["sourcecombine.py", "--show-config", "--json"]):
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 0

    out, err = capsys.readouterr()
    data = json.loads(out)
    assert "logging" in data
    assert "search" in data
    assert out.strip().startswith("{")
    assert out.strip().endswith("}")
