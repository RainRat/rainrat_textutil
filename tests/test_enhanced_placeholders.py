import os
import platform
import sys
from pathlib import Path
from sourcecombine import _render_template, _render_global_template, find_and_combine_files

def test_system_placeholders():
    rel_path = Path("test.py")
    git_info = {
        "os": "TestOS",
        "python_version": "3.99.9",
        "platform": "TestPlatform",
        "arch": "TestArch"
    }

    template = "{{OS}} {{PYTHON_VERSION}} {{PLATFORM}} {{ARCH}}"
    rendered = _render_template(template, rel_path, content="print('hi')", git_info=git_info)
    assert rendered == "TestOS 3.99.9 TestPlatform TestArch"

def test_env_placeholders(monkeypatch):
    monkeypatch.setenv("TEST_VAR", "TestValue")
    rel_path = Path("test.py")

    template = "Value: {{ENV:TEST_VAR}}, Missing: {{ENV:MISSING}}"
    rendered = _render_template(template, rel_path, content="print('hi')")
    assert rendered == "Value: TestValue, Missing: "

def test_global_system_placeholders():
    stats = {
        "os": "TestOS",
        "python_version": "3.99.9",
        "platform": "TestPlatform",
        "arch": "TestArch"
    }

    template = "{{OS}} {{PYTHON_VERSION}} {{PLATFORM}} {{ARCH}}"
    rendered = _render_global_template(template, stats)
    assert rendered == "TestOS 3.99.9 TestPlatform TestArch"

def test_global_env_placeholders(monkeypatch):
    monkeypatch.setenv("GLOBAL_VAR", "GlobalValue")
    stats = {}

    template = "Value: {{ENV:GLOBAL_VAR}}"
    rendered = _render_global_template(template, stats)
    assert rendered == "Value: GlobalValue"

def test_full_integration(tmp_path, monkeypatch):
    monkeypatch.setenv("MY_ENV_VAR", "EnvVarValue")

    # Create a dummy project
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "file1.txt").write_text("content1")

    output_file = tmp_path / "combined.txt"

    config = {
        'search': {'root_folders': [str(project_dir)], 'recursive': True},
        'filters': {},
        'output': {
            'file': str(output_file),
            'global_header_template': "OS: {{OS}}, ENV: {{ENV:MY_ENV_VAR}}",
            'header_template': "FILE: {{FILENAME}}, PYTHON: {{PYTHON_VERSION}}\n",
            'footer_template': "\n",
            'format': 'text'
        },
        'processing': {}
    }

    find_and_combine_files(config, str(output_file))

    content = output_file.read_text()
    assert f"OS: {platform.system()}" in content
    assert "ENV: EnvVarValue" in content
    assert "FILE: file1.txt" in content
    assert f"PYTHON: {sys.version.split()[0]}" in content
