import pytest
from pathlib import Path
from unittest.mock import patch
import utils

def test_gradle_build_gradle_kts_fallback(tmp_path):
    (tmp_path / "settings.gradle").write_text("rootProject.name = 'test-gradle'", encoding='utf-8')
    (tmp_path / "build.gradle.kts").write_text("version = '1.2.3-kts'", encoding='utf-8')

    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "test-gradle"
    assert identity["project_version"] == "1.2.3-kts"

def test_dotnet_sln_parsing(tmp_path):
    (tmp_path / "Project.sln").write_text('Project("{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}") = "MyProj", "src\\MyProj.csproj", "{GUID}"', encoding='utf-8')
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "MyProj.csproj").write_text('<Project><PropertyGroup><AssemblyName>RealName</AssemblyName><Version>1.0.1</Version></PropertyGroup></Project>', encoding='utf-8')

    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "RealName"
    assert identity["project_version"] == "1.0.1"

def test_dotnet_csproj_only(tmp_path):
    (tmp_path / "only.csproj").write_text('<Project><PropertyGroup><Description>A desc</Description><PackageLicenseExpression>MIT</PackageLicenseExpression></PropertyGroup></Project>', encoding='utf-8')
    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "only"
    assert identity["project_description"] == "A desc"
    assert identity["project_license"] == "MIT"

def test_clojure_project_clj(tmp_path):
    (tmp_path / "project.clj").write_text('(defproject my-clj "0.2.0" :description "Clojure app" :license {:name "EPL-2.0"})', encoding='utf-8')
    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "my-clj"
    assert identity["project_version"] == "0.2.0"
    assert identity["project_description"] == "Clojure app"
    assert identity["project_license"] == "EPL-2.0"

def test_cocoapods_podspec(tmp_path):
    (tmp_path / "MyPod.podspec").write_text("Pod::Spec.new do |s| s.name = 'MyPod' s.version = '1.2.3' s.summary = 'Pod summary' s.license = 'Apache 2' end", encoding='utf-8')
    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "MyPod"
    assert identity["project_version"] == "1.2.3"
    assert identity["project_description"] == "Pod summary"
    assert identity["project_license"] == "Apache 2"

def test_xcode_project(tmp_path):
    (tmp_path / "App.xcodeproj").mkdir()
    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "App"

def test_java_pom_xml(tmp_path):
    (tmp_path / "pom.xml").write_text('<project><artifactId>my-artifact</artifactId><version>1.1</version><description>Java desc</description><licenses><license><name>MIT</name></license></licenses></project>', encoding='utf-8')
    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "my-artifact"
    assert identity["project_version"] == "1.1"
    assert identity["project_description"] == "Java desc"
    assert identity["project_license"] == "MIT"

def test_go_mod(tmp_path):
    (tmp_path / "go.mod").write_text("module github.com/user/repo", encoding='utf-8')
    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "github.com/user/repo"

def test_readme_setext_and_paragraph(tmp_path):
    (tmp_path / "README.md").write_text("Setext Name\n=========\n\nThis is the description paragraph.\nIt should be captured.", encoding='utf-8')
    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "Setext Name"
    assert identity["project_description"] == "This is the description paragraph."

def test_readme_long_description_truncation(tmp_path):
    long_desc = "A" * 250
    (tmp_path / "README.md").write_text(f"# Long Project\n\n{long_desc}", encoding='utf-8')
    identity = utils.get_project_identity(tmp_path)
    assert len(identity["project_description"]) == 200
    assert identity["project_description"].endswith("...")

def test_license_extraction(tmp_path):
    (tmp_path / "LICENSE.txt").write_text("The MIT License\n\nCopyright (c) 2024", encoding='utf-8')
    identity = utils.get_project_identity(tmp_path)
    assert identity["project_license"] == "MIT"

def test_license_extraction_short_line(tmp_path):
    (tmp_path / "COPYING").write_text("Custom License Name", encoding='utf-8')
    identity = utils.get_project_identity(tmp_path)
    assert identity["project_license"] == "Custom License Name"

def test_license_extraction_filename_fallback(tmp_path):
    (tmp_path / "LICENSE.md").write_text("A very long first line that does not match any common license name pattern and is longer than fifty characters.", encoding='utf-8')
    identity = utils.get_project_identity(tmp_path)
    assert identity["project_license"] == "LICENSE.md"

def test_project_identity_dotnet_exception(tmp_path):
    (tmp_path / "test.csproj").write_text("<AssemblyName>Test</AssemblyName>", encoding='utf-8')
    with patch("pathlib.Path.read_text", side_effect=RuntimeError("dotnet error")):
        identity = utils.get_project_identity(tmp_path)
        assert identity["project_name"] == tmp_path.name

def test_project_identity_gradle_exception(tmp_path):
    (tmp_path / "settings.gradle").write_text("rootProject.name = 'test'", encoding='utf-8')
    with patch("pathlib.Path.read_text", side_effect=RuntimeError("gradle error")):
        identity = utils.get_project_identity(tmp_path)
        assert identity["project_name"] == tmp_path.name

def test_project_identity_clojure_exception(tmp_path):
    (tmp_path / "project.clj").write_text("(defproject test \"0.1\")", encoding='utf-8')
    with patch("pathlib.Path.read_text", side_effect=RuntimeError("clojure error")):
        identity = utils.get_project_identity(tmp_path)
        assert identity["project_name"] == tmp_path.name

def test_project_identity_cocoapods_exception(tmp_path):
    (tmp_path / "test.podspec").write_text("s.name = 'test'", encoding='utf-8')
    with patch("pathlib.Path.read_text", side_effect=RuntimeError("cocoapods error")):
        identity = utils.get_project_identity(tmp_path)
        assert identity["project_name"] == tmp_path.name

def test_project_identity_swift_exception(tmp_path):
    (tmp_path / "Package.swift").write_text("name: 'test'", encoding='utf-8')
    with patch("pathlib.Path.read_text", side_effect=RuntimeError("swift error")):
        identity = utils.get_project_identity(tmp_path)
        assert identity["project_name"] == tmp_path.name

def test_project_identity_go_exception(tmp_path):
    (tmp_path / "go.mod").write_text("module test", encoding='utf-8')
    with patch("pathlib.Path.read_text", side_effect=RuntimeError("go error")):
        identity = utils.get_project_identity(tmp_path)
        assert identity["project_name"] == tmp_path.name

def test_project_identity_ruby_exception(tmp_path):
    (tmp_path / "test.gemspec").write_text("s.name = 'test'", encoding='utf-8')
    with patch("pathlib.Path.read_text", side_effect=RuntimeError("ruby error")):
        identity = utils.get_project_identity(tmp_path)
        assert identity["project_name"] == tmp_path.name

def test_project_identity_elixir_exception(tmp_path):
    (tmp_path / "mix.exs").write_text("app: :test", encoding='utf-8')
    with patch("pathlib.Path.read_text", side_effect=RuntimeError("elixir error")):
        identity = utils.get_project_identity(tmp_path)
        assert identity["project_name"] == tmp_path.name

def test_project_identity_readme_exception(tmp_path):
    (tmp_path / "README.md").write_text("# Test Project", encoding='utf-8')
    with patch("pathlib.Path.read_text", side_effect=RuntimeError("readme error")):
        identity = utils.get_project_identity(tmp_path)
        assert identity["project_name"] == tmp_path.name

def test_project_identity_license_exception(tmp_path):
    (tmp_path / "LICENSE").write_text("MIT License", encoding='utf-8')
    (tmp_path / "README.md").write_text("# Test", encoding='utf-8')

    original_read_text = Path.read_text
    def side_effect(self, *args, **kwargs):
        if self.name == "LICENSE":
            raise RuntimeError("license error")
        return original_read_text(self, *args, **kwargs)

    with patch("pathlib.Path.read_text", side_effect=side_effect):
        identity = utils.get_project_identity(tmp_path)
        assert identity["project_license"] == ""
