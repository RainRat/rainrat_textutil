import sys; import os; from pathlib import Path; sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))
import utils
import pytest
from unittest.mock import patch, MagicMock

def test_get_project_identity_license_fallbacks(tmp_path):
    # Test Step 11: Search for LICENSE or COPYING files if license is still missing
    project_dir = tmp_path / "license_fallbacks"
    project_dir.mkdir()

    # Test COPYING
    (project_dir / "COPYING").write_text("The GPL License\n...", encoding="utf-8")
    identity = utils.get_project_identity(project_dir)
    assert identity["project_license"] == "GPL"
    (project_dir / "COPYING").unlink()

    # Test LICENSE.md
    (project_dir / "LICENSE.md").write_text("Mozilla Public License 2.0\n...", encoding="utf-8")
    identity = utils.get_project_identity(project_dir)
    assert identity["project_license"] == "Mozilla"
    (project_dir / "LICENSE.md").unlink()

    # Test Unlicense
    (project_dir / "LICENSE").write_text("The Unlicense\n...", encoding="utf-8")
    identity = utils.get_project_identity(project_dir)
    assert identity["project_license"] == "Unlicense"
    (project_dir / "LICENSE").unlink()

def test_get_project_identity_license_name_cleaning(tmp_path):
    project_dir = tmp_path / "license_cleaning"
    project_dir.mkdir()

    cases = [
        ("The MIT License", "MIT"),
        ("Apache License Version 2.0", "Apache"),
        ("BSD 3-Clause License", "BSD"),
        ("ISC License (ISC)", "ISC"),
        ("Zlib License", "Zlib"),
    ]

    for input_text, expected in cases:
        license_file = project_dir / "LICENSE"
        license_file.write_text(input_text, encoding="utf-8")
        identity = utils.get_project_identity(project_dir)
        assert identity["project_license"] == expected
        license_file.unlink()

def test_get_project_identity_manifest_no_license_info(tmp_path):
    # Test that Step 11 is reached when a manifest is found but contains no license info.
    pkg_json = tmp_path / "package.json"
    pkg_json.write_text('{"name": "no-license-manifest"}', encoding="utf-8")

    license_file = tmp_path / "LICENSE"
    license_file.write_text("MIT License", encoding="utf-8")

    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "no-license-manifest"
    assert identity["project_license"] == "MIT"

def test_get_project_identity_gradle_kts(tmp_path):
    settings = tmp_path / "settings.gradle.kts"
    settings.write_text('rootProject.name = "gradle-kts-project"', encoding='utf-8')

    build = tmp_path / "build.gradle.kts"
    build.write_text('version = "2.3.4"', encoding='utf-8')

    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "gradle-kts-project"
    assert identity["project_version"] == "2.3.4"

def test_get_project_identity_dotnet_sln_no_match(tmp_path):
    sln = tmp_path / "Empty.sln"
    sln.write_text('No projects here', encoding='utf-8')

    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "Empty"

def test_get_project_identity_dotnet_sln_invalid_path(tmp_path):
    sln = tmp_path / "Invalid.sln"
    sln.write_text('Project("{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}") = "MyProj", "missing\\MyProj.csproj"', encoding='utf-8')

    identity = utils.get_project_identity(tmp_path)
    # Falls back to solution stem because referenced csproj is missing
    assert identity["project_name"] == "Invalid"

def test_get_project_identity_clojure_exception(tmp_path):
    project_clj = tmp_path / "project.clj"
    project_clj.touch()
    with patch.object(Path, "read_text", side_effect=Exception("Clojure error")):
        identity = utils.get_project_identity(tmp_path)
        assert identity["project_name"] == tmp_path.name

def test_get_project_identity_cocoapods_exception(tmp_path):
    podspec = tmp_path / "My.podspec"
    podspec.touch()
    with patch.object(Path, "read_text", side_effect=Exception("Podspec error")):
        identity = utils.get_project_identity(tmp_path)
        assert identity["project_name"] == tmp_path.name

def test_get_project_identity_ruby_exception(tmp_path):
    gemspec = tmp_path / "My.gemspec"
    gemspec.touch()
    with patch.object(Path, "read_text", side_effect=Exception("Gemspec error")):
        identity = utils.get_project_identity(tmp_path)
        assert identity["project_name"] == tmp_path.name

def test_get_project_identity_elixir_exception(tmp_path):
    mix_exs = tmp_path / "mix.exs"
    mix_exs.touch()
    with patch.object(Path, "read_text", side_effect=Exception("Mix error")):
        identity = utils.get_project_identity(tmp_path)
        assert identity["project_name"] == tmp_path.name

def test_get_project_identity_readme_exception(tmp_path):
    readme = tmp_path / "README.md"
    readme.touch()
    with patch.object(Path, "read_text", side_effect=Exception("README error")):
        identity = utils.get_project_identity(tmp_path)
        assert identity["project_name"] == tmp_path.name

def test_get_project_identity_license_file_exception(tmp_path):
    license_file = tmp_path / "LICENSE"
    license_file.touch()
    # Mocking read_text on Path instance specifically for LICENSE file is tricky,
    # we'll mock it generally inside get_project_identity context
    with patch.object(Path, "read_text", side_effect=Exception("License error")):
        identity = utils.get_project_identity(tmp_path)
        assert identity["project_license"] == ""

# Consolidating from test_utils_project_name_gaps.py
def test_get_project_name_package_json_invalid(tmp_path):
    pkg_json = tmp_path / "package.json"
    pkg_json.write_text("{invalid json", encoding='utf-8')
    assert utils.get_project_identity(tmp_path)["project_name"] == tmp_path.name

def test_get_project_name_pyproject_toml_section_match(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    content = "[project]\n  name = \"regex-section-match\""
    pyproject.write_text(content, encoding='utf-8')
    assert utils.get_project_identity(tmp_path)["project_name"] == "regex-section-match"

def test_get_project_name_pyproject_toml_invalid_regex(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[project]\nfoo = 'bar'", encoding='utf-8')
    assert utils.get_project_identity(tmp_path)["project_name"] == tmp_path.name

def test_get_project_name_exception_fallback(tmp_path):
    with patch("utils.Path.resolve", side_effect=Exception("Unresolved")):
        assert utils.get_project_identity("/some/path")["project_name"] == "Project"

def test_get_project_name_pyproject_exception_handled(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("name = 'test'", encoding='utf-8')
    with patch("utils.re.search", side_effect=Exception("Regex Error")):
        assert utils.get_project_identity(tmp_path)["project_name"] == tmp_path.name
