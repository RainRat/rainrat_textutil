import json
import subprocess
import pytest

def test_project_info_json():
    result = subprocess.run(
        ["python3", "sourcecombine.py", "--project-info", "--json"],
        capture_output=True,
        text=True,
        check=True
    )
    # Check if stdout is valid JSON
    data = json.loads(result.stdout)
    assert "project_name" in data
    assert "os" in data
    assert "python_version" in data
    # Ensure no logging noise in stdout
    assert result.stdout.strip().startswith("{")
    assert result.stdout.strip().endswith("}")

def test_system_info_json():
    result = subprocess.run(
        ["python3", "sourcecombine.py", "--system-info", "--json"],
        capture_output=True,
        text=True,
        check=True
    )
    data = json.loads(result.stdout)
    assert "version" in data
    assert "dependencies" in data
    assert result.stdout.strip().startswith("{")

def test_list_languages_json():
    result = subprocess.run(
        ["python3", "sourcecombine.py", "--list-languages", "--json"],
        capture_output=True,
        text=True,
        check=True
    )
    data = json.loads(result.stdout)
    assert "languages" in data
    assert "total" in data
    assert "python" in data["languages"]
    assert result.stdout.strip().startswith("{")

def test_list_placeholders_json():
    result = subprocess.run(
        ["python3", "sourcecombine.py", "--list-placeholders", "--json"],
        capture_output=True,
        text=True,
        check=True
    )
    data = json.loads(result.stdout)
    assert "File-Level Placeholders" in data
    assert "{{FILENAME}}" in data["File-Level Placeholders"]
    assert result.stdout.strip().startswith("{")

def test_show_config_json():
    result = subprocess.run(
        ["python3", "sourcecombine.py", "--show-config", "--json"],
        capture_output=True,
        text=True,
        check=True
    )
    data = json.loads(result.stdout)
    assert "logging" in data
    assert "search" in data
    assert result.stdout.strip().startswith("{")
