import sys; import os; from pathlib import Path; sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))
import utils
import pytest
from unittest.mock import patch

def test_get_project_name_package_json_invalid(tmp_path):
    pkg_json = tmp_path / "package.json"
    pkg_json.write_text("{invalid json", encoding='utf-8')
    # Should skip package.json and fallback to folder name
    assert utils.get_project_identity(tmp_path)["project_name"] == tmp_path.name

def test_get_project_name_pyproject_toml_section_match(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    # Testing the second regex: r'\[project\][^\[]*name\s*=\s*["\']([^"\']+)["\']'
    # We need the first regex (top level name) NOT to match.
    # The first regex is re.search(r'^name\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
    # By indenting 'name' in [project], it won't match '^name'.
    content = "[project]\n  name = \"regex-section-match\""
    pyproject.write_text(content, encoding='utf-8')
    assert utils.get_project_identity(tmp_path)["project_name"] == "regex-section-match"

def test_get_project_name_pyproject_toml_invalid_regex(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    # Create a file that exists but has no name match
    pyproject.write_text("[project]\nfoo = 'bar'", encoding='utf-8')
    assert utils.get_project_identity(tmp_path)["project_name"] == tmp_path.name

def test_get_project_name_exception_fallback(tmp_path):
    # Trigger the outermost except Exception
    with patch("utils.Path.resolve", side_effect=Exception("Unresolved")):
        assert utils.get_project_identity("/some/path")["project_name"] == "Project"

def test_get_project_name_pyproject_exception_handled(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("name = 'test'", encoding='utf-8')

    with patch("utils.re.search", side_effect=Exception("Regex Error")):
        # Exception in pyproject parsing should be caught and fallback to folder name
        assert utils.get_project_identity(tmp_path)["project_name"] == tmp_path.name
