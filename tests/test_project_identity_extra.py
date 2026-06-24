import json
from pathlib import Path
from unittest.mock import patch
import utils

def test_get_project_identity_dotnet_solution_with_project(tmp_path):
    sln = tmp_path / "test.sln"
    sln.write_text('Project("{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}") = "MyApp", "src\\MyApp.csproj", "{GUID}"', encoding='utf-8')

    csproj = tmp_path / "src" / "MyApp.csproj"
    csproj.parent.mkdir()
    csproj.write_text('<Project><PropertyGroup><AssemblyName>FinalName</AssemblyName><Version>1.0.1</Version></PropertyGroup></Project>', encoding='utf-8')

    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "FinalName"
    assert identity["project_version"] == "1.0.1"

def test_get_project_identity_dotnet_solution_no_match(tmp_path):
    sln = tmp_path / "SolutionOnly.sln"
    sln.write_text('Some other content', encoding='utf-8')

    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == tmp_path.name

def test_get_project_identity_gradle_kts(tmp_path):
    settings = tmp_path / "settings.gradle.kts"
    settings.write_text('rootProject.name = "kotlin-gradle"', encoding='utf-8')

    build = tmp_path / "build.gradle.kts"
    build.write_text('version = "2.3.4"', encoding='utf-8')

    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "kotlin-gradle"
    assert identity["project_version"] == "2.3.4"

def test_get_project_identity_clojure(tmp_path):
    project_clj = tmp_path / "project.clj"
    project_clj.write_text('(defproject my-clj "1.2.3" :description "Clojure desc" :license {:name "EPL"})', encoding='utf-8')

    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "my-clj"
    assert identity["project_version"] == "1.2.3"
    assert identity["project_description"] == "Clojure desc"
    assert identity["project_license"] == "EPL"

def test_get_project_identity_cocoapods(tmp_path):
    podspec = tmp_path / "MyPod.podspec"
    podspec.write_text('Spec.name = "MyPod"\nSpec.version = "0.9"\nSpec.summary = "Pod summary"\nSpec.license = "MIT"', encoding='utf-8')

    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "MyPod"
    assert identity["project_version"] == "0.9"
    assert identity["project_description"] == "Pod summary"
    assert identity["project_license"] == "MIT"

def test_get_project_identity_xcode(tmp_path):
    xcodeproj = tmp_path / "MyiOSApp.xcodeproj"
    xcodeproj.mkdir()

    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "MyiOSApp"

def test_get_project_identity_swift_package(tmp_path):
    package_swift = tmp_path / "Package.swift"
    package_swift.write_text('let package = Package(name: "SwiftPkg")', encoding='utf-8')

    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "SwiftPkg"

def test_get_project_identity_readme_setext(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text("Setext Name\n===========\n\nThis is a description paragraph.\n", encoding='utf-8')

    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "Setext Name"
    assert identity["project_description"] == "This is a description paragraph."

def test_get_project_identity_readme_truncation(tmp_path):
    readme = tmp_path / "README.md"
    long_desc = "A" * 300
    readme.write_text(f"# Long Project\n\n{long_desc}", encoding='utf-8')

    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "Long Project"
    assert len(identity["project_description"]) == 200
    assert identity["project_description"].endswith("...")

def test_get_project_identity_license_extraction(tmp_path):
    license_file = tmp_path / "LICENSE"
    license_file.write_text("The MIT License\n\nCopyright (c) 2023", encoding='utf-8')

    identity = utils.get_project_identity(tmp_path)
    assert identity["project_license"] == "MIT"

def test_get_project_identity_license_fallback_filename(tmp_path):
    license_file = tmp_path / "COPYING"
    license_file.write_text("This project is licensed under the terms of this file which is long.\n\nRest of file", encoding='utf-8')

    identity = utils.get_project_identity(tmp_path)
    assert identity["project_license"] == "COPYING"

def test_get_project_identity_exceptions_coverage(tmp_path):
    with patch("pathlib.Path.read_text", side_effect=Exception("Failed")):
        (tmp_path / "package.json").write_text("{}", encoding='utf-8')
        (tmp_path / "settings.gradle").write_text("rootProject.name='test'", encoding='utf-8')

        identity = utils.get_project_identity(tmp_path)
        assert identity["project_name"] == tmp_path.name

def test_get_project_identity_dotnet_exception_coverage(tmp_path):
    (tmp_path / "test.csproj").write_text("<Project/>", encoding='utf-8')
    with patch("utils.re.search", side_effect=Exception("Regex error")):
        identity = utils.get_project_identity(tmp_path)
        assert identity["project_name"] == tmp_path.name
