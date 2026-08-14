import json
from pathlib import Path
from utils import get_project_identity, _parse_json_manifest

def test_parse_json_manifest_gaps(tmp_path):
    manifest = tmp_path / "package.json"
    manifest.write_text(json.dumps({
        "repository": {}
    }), encoding='utf-8')
    identity = {"project_name": "Project"}
    assert _parse_json_manifest(manifest, identity) is True

    manifest.write_text(json.dumps({
        "repository": 123
    }), encoding='utf-8')
    identity = {"project_name": "Project"}
    assert _parse_json_manifest(manifest, identity) is True
    assert "project_url" not in identity

def test_dotnet_gaps(tmp_path):
    sln = tmp_path / "test.sln"
    sln.write_text("Some text that doesn't define projects", encoding='utf-8')
    identity = get_project_identity(tmp_path)
    assert identity["manifest_source"] == "test.sln"

    sln.write_text('Project("{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}") = "MyProj", "NonExistent.csproj"', encoding='utf-8')
    identity = get_project_identity(tmp_path)
    assert identity["manifest_source"] == "test.sln"

    csproj = tmp_path / "MyProj.csproj"
    csproj.write_text('<Project></Project>', encoding='utf-8')
    sln.unlink()
    identity = get_project_identity(tmp_path)
    assert identity["project_name"] == "MyProj"
    assert identity["project_version"] == ""
    assert identity["project_author"] == ""

def test_gradle_gaps(tmp_path):
    settings = tmp_path / "settings.gradle"
    settings.write_text("// no name here", encoding='utf-8')
    identity = get_project_identity(tmp_path)
    assert identity["project_name"] == tmp_path.name

    build = tmp_path / "build.gradle"
    build.write_text("// no version here", encoding='utf-8')
    identity = get_project_identity(tmp_path)
    assert identity["project_version"] == ""

def test_clojure_gaps(tmp_path):
    project = tmp_path / "project.clj"
    project.write_text("(defn foo [])", encoding='utf-8')
    identity = get_project_identity(tmp_path)
    assert identity["project_name"] == tmp_path.name

def test_cocoapods_gaps(tmp_path):
    podspec = tmp_path / "test.podspec"
    podspec.write_text('Pod::Spec.new do |s|\ns.name = "MyPod"\nend', encoding='utf-8')
    identity = get_project_identity(tmp_path)
    assert identity["project_name"] == "MyPod"
    assert identity["project_version"] == ""
    assert identity["project_author"] == ""

def test_python_pyproject_toml_gaps(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[project]\nname = 'test-proj'", encoding='utf-8')
    identity = get_project_identity(tmp_path)
    assert identity["project_name"] == "test-proj"
    assert identity["project_author"] == ""
    assert identity["project_description"] == ""
    assert identity["project_license"] == ""
    assert identity["project_url"] == ""

def test_rust_cargo_toml_gaps(tmp_path):
    cargo = tmp_path / "Cargo.toml"
    cargo.write_text("[dependencies]\n", encoding='utf-8')
    identity = get_project_identity(tmp_path)
    assert identity["project_name"] == tmp_path.name

    cargo.write_text('[package]\nname = "my-cargo"\nhomepage = "https://example.com"\nrepository = "https://github.com/rust-lang/cargo"', encoding='utf-8')
    identity = get_project_identity(tmp_path)
    assert identity["project_url"] == "https://example.com"

def test_go_mod_gaps(tmp_path):
    gomod = tmp_path / "go.mod"
    gomod.write_text("// empty go mod\n", encoding='utf-8')
    identity = get_project_identity(tmp_path)
    assert identity["project_name"] == tmp_path.name

def test_ruby_gemspec_gaps(tmp_path):
    gemspec = tmp_path / "test.gemspec"
    gemspec.write_text('Gem::Specification.new do |s| s.name = "my-gem" end', encoding='utf-8')
    identity = get_project_identity(tmp_path)
    assert identity["project_name"] == "my-gem"
    assert identity["project_author"] == ""

def test_elixir_mix_exs_gaps(tmp_path):
    mix = tmp_path / "mix.exs"
    mix.write_text("def project do [] end", encoding='utf-8')
    identity = get_project_identity(tmp_path)
    assert identity["project_name"] == tmp_path.name

def test_swift_package_swift_gaps(tmp_path):
    swift = tmp_path / "Package.swift"
    swift.write_text("// Swift file", encoding='utf-8')
    identity = get_project_identity(tmp_path)
    assert identity["project_name"] == tmp_path.name

def test_cmake_gaps(tmp_path):
    cmake = tmp_path / "CMakeLists.txt"
    cmake.write_text("project(MyProj)", encoding='utf-8')
    identity = get_project_identity(tmp_path)
    assert identity["project_name"] == "MyProj"
    assert identity["project_version"] == ""
    assert identity["project_description"] == ""

def test_julia_project_toml_gaps(tmp_path):
    julia = tmp_path / "Project.toml"
    julia.write_text("name = 'MyJulia'", encoding='utf-8')
    identity = get_project_identity(tmp_path)
    assert identity["project_name"] == "MyJulia"
    assert identity["project_version"] == ""

def test_zig_gaps(tmp_path):
    zig = tmp_path / "build.zig.zon"
    zig.write_text('.other = "field",', encoding='utf-8')
    identity = get_project_identity(tmp_path)
    assert identity["project_name"] == tmp_path.name
    assert identity["project_version"] == ""

def test_flutter_pubspec_gaps(tmp_path):
    pubspec = tmp_path / "pubspec.yaml"
    pubspec.write_text("description: My Flutter app", encoding='utf-8')
    identity = get_project_identity(tmp_path)
    assert identity["project_name"] == tmp_path.name
    assert identity["project_version"] == ""
    assert identity["project_author"] == ""
    assert identity["project_description"] == "My Flutter app"
    assert identity["project_url"] == ""

def test_readme_and_license_gaps(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text("My Project Name\n===============\n\n=== Subheader", encoding='utf-8')
    identity = get_project_identity(tmp_path)
    assert identity["project_name"] == "My Project Name"
    assert identity["project_description"] == ""

    license_file = tmp_path / "LICENSE"
    license_file.write_text("", encoding='utf-8')
    identity = get_project_identity(tmp_path)
    assert identity["project_license"] == ""

    license_file.write_text("This is a very long sentence that exceeds fifty characters and does not match any prefix.", encoding='utf-8')
    identity = get_project_identity(tmp_path)
    assert identity["project_license"] == "LICENSE"
    assert identity["project_author"] == ""
