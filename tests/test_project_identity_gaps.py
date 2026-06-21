import pytest
from pathlib import Path
from unittest.mock import patch
from utils import get_project_identity

def test_gradle_kts_detection(tmp_path):
    settings_kts = tmp_path / "settings.gradle.kts"
    settings_kts.write_text('rootProject.name = "gradle-kts-project"', encoding='utf-8')

    build_kts = tmp_path / "build.gradle.kts"
    build_kts.write_text('version = "1.2.3-kts"', encoding='utf-8')

    identity = get_project_identity(tmp_path)
    assert identity["project_name"] == "gradle-kts-project"
    assert identity["project_version"] == "1.2.3-kts"

def test_dotnet_sln_fallback_to_stem(tmp_path):
    sln = tmp_path / "MySolution.sln"
    sln.write_text('Project("{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}") = "MyProj", "NonExistent.csproj", "{GUID}"', encoding='utf-8')

    identity = get_project_identity(tmp_path)
    # The current logic for .sln fallback if no .csproj matches
    # actually skips setting project_name from content if target_file is .sln
    # and manifest_found becomes True.
    # So it keeps the initial project_name (folder name).
    assert identity["project_name"] == tmp_path.name

def test_get_project_identity_exceptions(tmp_path):
    # Test exceptions in various manifest parsers to cover 'except Exception: pass'

    # 1. Node.js exception (via _parse_json_manifest)
    (tmp_path / "package.json").write_text("{", encoding='utf-8')
    with patch("utils.Path.read_text", side_effect=Exception("Read Error")):
        identity = get_project_identity(tmp_path)
        assert identity["project_name"] == tmp_path.name

    # 2. .NET exception
    (tmp_path / "Test.csproj").write_text("<Project>", encoding='utf-8')
    with patch("utils.Path.read_text", side_effect=Exception("Read Error")):
        identity = get_project_identity(tmp_path)
        assert identity["project_name"] == tmp_path.name

    # 3. Gradle exception
    (tmp_path / "settings.gradle").write_text("rootProject.name = 'test'", encoding='utf-8')
    with patch("utils.Path.read_text", side_effect=Exception("Read Error")):
        identity = get_project_identity(tmp_path)
        assert identity["project_name"] == tmp_path.name

    # 4. Clojure exception
    (tmp_path / "project.clj").write_text("(defproject ...)", encoding='utf-8')
    with patch("utils.Path.read_text", side_effect=Exception("Read Error")):
        identity = get_project_identity(tmp_path)
        assert identity["project_name"] == tmp_path.name

    # 5. CocoaPods exception
    (tmp_path / "Test.podspec").write_text("Spec.new ...", encoding='utf-8')
    with patch("utils.Path.read_text", side_effect=Exception("Read Error")):
        identity = get_project_identity(tmp_path)
        assert identity["project_name"] == tmp_path.name

    # 6. PHP exception
    (tmp_path / "composer.json").write_text('{"name": "test"}', encoding='utf-8')
    with patch("utils.Path.read_text", side_effect=Exception("Read Error")):
        identity = get_project_identity(tmp_path)
        assert identity["project_name"] == tmp_path.name

    # 7. Java exception
    (tmp_path / "pom.xml").write_text("<project>", encoding='utf-8')
    with patch("utils.Path.read_text", side_effect=Exception("Read Error")):
        identity = get_project_identity(tmp_path)
        assert identity["project_name"] == tmp_path.name

    # 8. Rust exception
    (tmp_path / "Cargo.toml").write_text("[package]", encoding='utf-8')
    with patch("utils.Path.read_text", side_effect=Exception("Read Error")):
        identity = get_project_identity(tmp_path)
        assert identity["project_name"] == tmp_path.name

    # 9. Python exception (pyproject.toml)
    (tmp_path / "pyproject.toml").write_text("[project]", encoding='utf-8')
    with patch("utils.Path.read_text", side_effect=Exception("Read Error")):
        identity = get_project_identity(tmp_path)
        assert identity["project_name"] == tmp_path.name

    # 10. Go exception
    (tmp_path / "go.mod").write_text("module test", encoding='utf-8')
    with patch("utils.Path.read_text", side_effect=Exception("Read Error")):
        identity = get_project_identity(tmp_path)
        assert identity["project_name"] == tmp_path.name

    # 11. Ruby exception
    (tmp_path / "test.gemspec").write_text("Gem::Spec ...", encoding='utf-8')
    with patch("utils.Path.read_text", side_effect=Exception("Read Error")):
        identity = get_project_identity(tmp_path)
        assert identity["project_name"] == tmp_path.name

    # 12. Elixir exception
    (tmp_path / "mix.exs").write_text("def project ...", encoding='utf-8')
    with patch("utils.Path.read_text", side_effect=Exception("Read Error")):
        identity = get_project_identity(tmp_path)
        assert identity["project_name"] == tmp_path.name

    # 13. Swift exception
    (tmp_path / "Package.swift").write_text("let package ...", encoding='utf-8')
    with patch("utils.Path.read_text", side_effect=Exception("Read Error")):
        identity = get_project_identity(tmp_path)
        assert identity["project_name"] == tmp_path.name

def test_readme_license_fallback_exceptions(tmp_path):
    # 14. README exception
    (tmp_path / "README.md").write_text("# My Project", encoding='utf-8')
    # To test Step 10 exception, we need manifest_found to be False.
    with patch("utils.Path.read_text", side_effect=Exception("Read Error")):
        identity = get_project_identity(tmp_path)
        assert identity["project_name"] == tmp_path.name

    # 15. LICENSE exception
    (tmp_path / "LICENSE").write_text("MIT License", encoding='utf-8')
    # Mocking read_text for LICENSE specifically
    original_read_text = Path.read_text
    def mock_read_text(self, *args, **kwargs):
        if self.name == "LICENSE":
            raise Exception("License Error")
        return original_read_text(self, *args, **kwargs)

    with patch("utils.Path.read_text", side_effect=mock_read_text, autospec=True):
        identity = get_project_identity(tmp_path)
        assert identity["project_license"] == ""

def test_license_cleaning_logic(tmp_path):
    # Coverage for the regex-based license cleaning in step 11
    license_file = tmp_path / "LICENSE"

    # Test "The MIT License" -> "MIT"
    license_file.write_text("The MIT License\nCopyright (c) 2023", encoding='utf-8')
    identity = get_project_identity(tmp_path)
    assert identity["project_license"] == "MIT"

    # Test "Apache License Version 2.0" -> "Apache" (based on regex)
    license_file.write_text("Apache License\nVersion 2.0", encoding='utf-8')
    identity = get_project_identity(tmp_path)
    assert identity["project_license"] == "Apache"

    # Test short line fallback
    license_file.write_text("Custom License Name", encoding='utf-8')
    identity = get_project_identity(tmp_path)
    assert identity["project_license"] == "Custom License Name"

    # Test long first line fallback to filename
    license_file.write_text("This is a very long first line that definitely does not look like a license name because it is just way too long for that.", encoding='utf-8')
    identity = get_project_identity(tmp_path)
    assert identity["project_license"] == "LICENSE"
