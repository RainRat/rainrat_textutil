import os
import sys
import platform
import pytest
from pathlib import Path
from sourcecombine import find_and_combine_files, _render_template, _render_global_template

def test_system_placeholders_in_render_template():
    git_info = {
        'os': platform.system(),
        'python_version': platform.python_version(),
        'platform': platform.platform(),
        'arch': platform.machine(),
        'git_status': '3 modified'
    }
    template = "OS: {{OS}}, Python: {{PYTHON_VERSION}}, Platform: {{PLATFORM}}, Arch: {{ARCH}}, Status: {{GIT_STATUS}}"
    result = _render_template(template, Path("test.py"), git_info=git_info, content="")

    assert platform.system() in result
    assert platform.python_version() in result
    assert platform.platform() in result
    assert platform.machine() in result
    assert '3 modified' in result

def test_env_placeholder_in_render_template():
    os.environ['TEST_SC_VAR'] = 'SOURCE_COMBINE_VALUE'
    template = "Value: {{ENV:TEST_SC_VAR}}"
    result = _render_template(template, Path("test.py"), content="")
    assert 'SOURCE_COMBINE_VALUE' in result
    del os.environ['TEST_SC_VAR']

def test_system_placeholders_in_global_render():
    stats = {
        'os': platform.system(),
        'python_version': platform.python_version(),
        'platform': platform.platform(),
        'arch': platform.machine(),
        'total_files': 1,
        'total_size_bytes': 100,
        'total_tokens': 10,
        'total_lines': 5
    }
    template = "OS: {{OS}}, Python: {{PYTHON_VERSION}}, Platform: {{PLATFORM}}, Arch: {{ARCH}}"
    result = _render_global_template(template, stats)

    assert platform.system() in result
    assert platform.python_version() in result
    assert platform.platform() in result
    assert platform.machine() in result

def test_env_placeholder_in_global_render():
    os.environ['GLOBAL_SC_VAR'] = 'GLOBAL_VALUE'
    template = "Value: {{ENV:GLOBAL_SC_VAR}}"
    result = _render_global_template(template, {})
    assert 'GLOBAL_VALUE' in result
    del os.environ['GLOBAL_SC_VAR']

def test_project_overview_includes_system_info(capsys, tmp_path):
    # This is a bit more involved as it needs to run find_and_combine_files
    # or _generate_project_overview directly.
    from sourcecombine import _generate_project_overview
    stats = {
        'os': platform.system(),
        'python_version': platform.python_version(),
        'project_name': 'TestProj',
        'total_files': 1,
        'total_size_bytes': 100,
        'total_tokens': 10,
        'total_lines': 5,
        'datetime': '2023-01-01 12:00:00'
    }

    # Test text format
    result_text = _generate_project_overview(stats, output_format='text')
    assert f"OS:           {platform.system()}" in result_text
    assert f"Python:       {platform.python_version()}" in result_text

    # Test markdown format
    result_md = _generate_project_overview(stats, output_format='markdown')
    assert f"- **OS:** {platform.system()}" in result_md
    assert f"- **Python:** {platform.python_version()}" in result_md
