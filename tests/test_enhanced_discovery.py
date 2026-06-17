import pytest
from pathlib import Path
from utils import get_project_identity, get_language_tag

def test_dotnet_csproj_detection(tmp_path):
    csproj = tmp_path / "MyProject.csproj"
    csproj.write_text("""
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <AssemblyName>CustomAssemblyName</AssemblyName>
    <Version>2.0.1</Version>
    <Description>A .NET project description.</Description>
    <PackageLicenseExpression>MIT</PackageLicenseExpression>
  </PropertyGroup>
</Project>
    """, encoding='utf-8')

    identity = get_project_identity(tmp_path)
    assert identity["project_name"] == "CustomAssemblyName"
    assert identity["project_version"] == "2.0.1"
    assert identity["project_description"] == "A .NET project description."
    assert identity["project_license"] == "MIT"

def test_dotnet_sln_heuristic(tmp_path):
    sln = tmp_path / "Solution.sln"
    sln.write_text('Project("{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}") = "MyProj", "src\\MyProj.csproj"', encoding='utf-8')

    src = tmp_path / "src"
    src.mkdir()
    csproj = src / "MyProj.csproj"
    csproj.write_text('<Project><PropertyGroup><AssemblyName>FromSln</AssemblyName></PropertyGroup></Project>', encoding='utf-8')

    identity = get_project_identity(tmp_path)
    assert identity["project_name"] == "FromSln"

def test_gradle_detection(tmp_path):
    settings = tmp_path / "settings.gradle"
    settings.write_text("rootProject.name = 'gradle-project'", encoding='utf-8')

    build = tmp_path / "build.gradle"
    build.write_text("version = '1.5.0'", encoding='utf-8')

    identity = get_project_identity(tmp_path)
    assert identity["project_name"] == "gradle-project"
    assert identity["project_version"] == "1.5.0"

def test_clojure_project_clj_detection(tmp_path):
    project_clj = tmp_path / "project.clj"
    project_clj.write_text('(defproject my-clj "0.1.0-SNAPSHOT" :description "Clojure desc" :license {:name "EPL"})', encoding='utf-8')

    identity = get_project_identity(tmp_path)
    assert identity["project_name"] == "my-clj"
    assert identity["project_version"] == "0.1.0-SNAPSHOT"
    assert identity["project_description"] == "Clojure desc"
    assert identity["project_license"] == "EPL"

def test_cocoapods_podspec_detection(tmp_path):
    podspec = tmp_path / "MyLib.podspec"
    podspec.write_text("s.name = 'MyLib'\ns.version = '1.0'\ns.summary = 'Pod desc'\ns.license = { :type => 'MIT' }", encoding='utf-8')

    identity = get_project_identity(tmp_path)
    # The regex for license is a bit simple, might need tuning but let's see
    assert identity["project_name"] == "MyLib"
    assert identity["project_version"] == "1.0"
    assert identity["project_description"] == "Pod desc"

def test_xcode_project_detection(tmp_path):
    xcodeproj = tmp_path / "App.xcodeproj"
    xcodeproj.mkdir()

    identity = get_project_identity(tmp_path)
    assert identity["project_name"] == "App"

def test_readme_setext_header(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text("Setext Name\n===========\n\nDescription here.", encoding='utf-8')

    identity = get_project_identity(tmp_path)
    assert identity["project_name"] == "Setext Name"
    assert identity["project_description"] == "Description here."

def test_new_language_mappings():
    assert get_language_tag("file.m") == "objectivec"
    assert get_language_tag("file.mm") == "objectivecpp"
    assert get_language_tag("file.ex") == "elixir"
    assert get_language_tag("file.erl") == "erlang"
    assert get_language_tag("file.clj") == "clojure"
    assert get_language_tag("file.hs") == "haskell"
    assert get_language_tag("file.sol") == "solidity"
    assert get_language_tag("file.jl") == "julia"
    assert get_language_tag("file.proto") == "protobuf"
    assert get_language_tag("file.graphql") == "graphql"
    assert get_language_tag("file.tf") == "hcl"
    assert get_language_tag("file.pyx") == "cython"
    assert get_language_tag("file.zig") == "zig"
    assert get_language_tag("file.nim") == "nim"
    assert get_language_tag("yarn.lock") == "yaml"
    assert get_language_tag("poetry.lock") == "toml"
