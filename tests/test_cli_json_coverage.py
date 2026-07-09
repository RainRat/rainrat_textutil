import sys
import json
from unittest.mock import patch, MagicMock
import pytest
from sourcecombine import main

def test_system_info_json_output(capsys):
    with patch("sys.argv", ["sourcecombine.py", "--system-info", "--json"]):
        with patch("importlib.util.find_spec", side_effect=lambda name: MagicMock()):
            with pytest.raises(SystemExit) as e:
                main()
            assert e.value.code == 0

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "version" in data
    assert "python" in data
    assert "dependencies" in data
    assert "tiktoken" in data["dependencies"]

def test_list_placeholders_json_output(capsys):
    with patch("sys.argv", ["sourcecombine.py", "--list-placeholders", "--json"]):
        with pytest.raises(SystemExit) as e:
            main()
        assert e.value.code == 0

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "File-Level Placeholders" in data
    assert "{{FILENAME}}" in data["File-Level Placeholders"]
    assert "Project Information (Global) Placeholders" in data

def test_list_languages_json_output(capsys):
    with patch("sys.argv", ["sourcecombine.py", "--list-languages", "--json"]):
        with pytest.raises(SystemExit) as e:
            main()
        assert e.value.code == 0

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "languages" in data
    assert "total" in data
    assert "python" in data["languages"]
