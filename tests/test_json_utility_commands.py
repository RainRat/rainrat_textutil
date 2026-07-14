import json
import sys
from unittest.mock import patch, MagicMock
import pytest
from sourcecombine import main

@pytest.fixture(autouse=True)
def ensure_pyperclip_spec():
    """Ensure pyperclip has a __spec__ if it's a stub from other tests."""
    import pyperclip
    if not hasattr(pyperclip, '__spec__'):
        # Create a dummy spec if it's missing (happens if stubbed as SimpleNamespace)
        pyperclip.__spec__ = MagicMock(name='pyperclip_spec')
    yield

def test_project_info_json(capsys):
    with patch.object(sys, 'argv', ["sourcecombine.py", "--project-info", "--json"]):
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0

    captured = capsys.readouterr()
    # Check if stdout is valid JSON
    data = json.loads(captured.out)
    assert "project_name" in data
    assert "os" in data
    assert "python_version" in data
    # Ensure no logging noise in stdout
    assert captured.out.strip().startswith("{")
    assert captured.out.strip().endswith("}")

def test_system_info_json(capsys):
    with patch.object(sys, 'argv', ["sourcecombine.py", "--system-info", "--json"]):
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "version" in data
    assert "dependencies" in data
    assert captured.out.strip().startswith("{")

def test_list_languages_json(capsys):
    with patch.object(sys, 'argv', ["sourcecombine.py", "--list-languages", "--json"]):
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "languages" in data
    assert "total" in data
    assert "python" in data["languages"]
    assert captured.out.strip().startswith("{")

def test_list_placeholders_json(capsys):
    with patch.object(sys, 'argv', ["sourcecombine.py", "--list-placeholders", "--json"]):
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "File-Level Placeholders" in data
    assert "{{FILENAME}}" in data["File-Level Placeholders"]
    assert captured.out.strip().startswith("{")

def test_show_config_json(capsys):
    with patch.object(sys, 'argv', ["sourcecombine.py", "--show-config", "--json"]):
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "logging" in data
    assert "search" in data
    assert captured.out.strip().startswith("{")

def test_project_info_json_with_target(tmp_path, capsys):
    target = tmp_path / "some_dir"
    target.mkdir()
    with patch.object(sys, 'argv', ["sourcecombine.py", "--project-info", "--json", str(target)]):
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "project_name" in data
