import json
from pathlib import Path
from unittest.mock import patch
from utils import get_project_identity

def test_get_project_identity_cmake_homepage(tmp_path):
    cmake_file = tmp_path / "CMakeLists.txt"
    cmake_file.write_text('project(MyProj HOMEPAGE_URL "https://example.com")', encoding='utf-8')

    identity = get_project_identity(tmp_path)
    assert identity["project_name"] == "MyProj"
    assert identity["project_url"] == "https://example.com"
    assert identity["manifest_source"] == "CMakeLists.txt"

def test_get_project_identity_elixir_homepage(tmp_path):
    mix_file = tmp_path / "mix.exs"
    mix_file.write_text('def project do [app: :my_app, version: "0.1.0", homepage_url: "https://elixir.org"] end', encoding='utf-8')

    identity = get_project_identity(tmp_path)
    assert identity["project_name"] == "my_app"
    assert identity["project_version"] == "0.1.0"
    assert identity["project_url"] == "https://elixir.org"
    assert identity["manifest_source"] == "mix.exs"

def test_get_project_identity_deno_json(tmp_path):
    deno_file = tmp_path / "deno.json"
    data = {
        "name": "my-deno-app",
        "version": "1.2.3",
        "description": "Deno description",
        "license": "MIT"
    }
    deno_file.write_text(json.dumps(data), encoding='utf-8')

    identity = get_project_identity(tmp_path)
    assert identity["project_name"] == "my-deno-app"
    assert identity["project_version"] == "1.2.3"
    assert identity["project_description"] == "Deno description"
    assert identity["project_license"] == "MIT"
    assert identity["manifest_source"] == "deno.json"

def test_get_project_identity_deno_jsonc(tmp_path):
    deno_file = tmp_path / "deno.jsonc"
    deno_file.write_text('''{
        // This is a comment
        "name": "my-deno-jsonc",
        /* Multi-line
           comment */
        "version": "1.0.0"
    }''', encoding='utf-8')

    identity = get_project_identity(tmp_path)
    assert identity["project_name"] == "my-deno-jsonc"
    assert identity["project_version"] == "1.0.0"
    assert identity["manifest_source"] == "deno.jsonc"

def test_get_project_identity_zig(tmp_path):
    zig_file = tmp_path / "build.zig.zon"
    zig_file.write_text('.name = "my-zig-project",\n.version = "0.11.0",', encoding='utf-8')

    identity = get_project_identity(tmp_path)
    assert identity["project_name"] == "my-zig-project"
    assert identity["project_version"] == "0.11.0"
    assert identity["manifest_source"] == "build.zig.zon"

def test_get_project_identity_pubspec_repository(tmp_path):
    pubspec = tmp_path / "pubspec.yaml"
    pubspec.write_text('name: my_flutter_app\nrepository: https://github.com/user/repo', encoding='utf-8')

    identity = get_project_identity(tmp_path)
    assert identity["project_name"] == "my_flutter_app"
    assert identity["project_url"] == "https://github.com/user/repo"
    assert identity["manifest_source"] == "pubspec.yaml"

def test_get_project_identity_readme_full_fallback(tmp_path):
    # Tests the paragraph extraction and Setext header together
    readme = tmp_path / "README.md"
    readme.write_text("My Project Name\n===============\n\n\n\nThis is the actual description paragraph.\nIt continues here.", encoding='utf-8')

    identity = get_project_identity(tmp_path)
    assert identity["project_name"] == "My Project Name"
    assert identity["project_description"] == "This is the actual description paragraph."

def test_get_project_identity_license_prefixes(tmp_path):
    test_cases = [
        ("The Apache License 2.0", "Apache"),
        ("MIT License", "MIT"),
        ("GPL License", "GPL"),
        ("BSD License", "BSD"),
        ("Unlicense", "Unlicense"),
    ]
    for content, expected in test_cases:
        license_file = tmp_path / "LICENSE"
        license_file.write_text(content, encoding='utf-8')
        identity = get_project_identity(tmp_path)
        assert identity["project_license"] == expected, f"Failed for {content}"

def test_get_project_identity_license_short_name(tmp_path):
    license_file = tmp_path / "LICENSE.txt"
    license_file.write_text("Custom License Name", encoding='utf-8')
    identity = get_project_identity(tmp_path)
    assert identity["project_license"] == "Custom License Name"

def test_get_project_identity_clojure_url(tmp_path):
    project_clj = tmp_path / "project.clj"
    project_clj.write_text('(defproject my-clj "1.0.0" :url "https://clojure.org")', encoding='utf-8')
    identity = get_project_identity(tmp_path)
    assert identity["project_url"] == "https://clojure.org"

def test_get_project_identity_cocoapods_homepage(tmp_path):
    podspec = tmp_path / "My.podspec"
    podspec.write_text('s.name = "MyPod"\ns.homepage = "https://cocoapods.org"', encoding='utf-8')
    identity = get_project_identity(tmp_path)
    assert identity["project_url"] == "https://cocoapods.org"

def test_get_project_identity_dotnet_url(tmp_path):
    csproj = tmp_path / "test.csproj"
    csproj.write_text('<Project><PropertyGroup><PackageProjectUrl>https://dotnet.microsoft.com/</PackageProjectUrl></PropertyGroup></Project>', encoding='utf-8')
    identity = get_project_identity(tmp_path)
    assert identity["project_url"] == "https://dotnet.microsoft.com/"

def test_get_project_identity_cargo_repository(tmp_path):
    cargo = tmp_path / "Cargo.toml"
    cargo.write_text('[package]\nname = "my-cargo"\nrepository = "https://github.com/rust-lang/cargo"', encoding='utf-8')
    identity = get_project_identity(tmp_path)
    assert identity["project_url"] == "https://github.com/rust-lang/cargo"

def test_get_project_identity_pom_url(tmp_path):
    pom = tmp_path / "pom.xml"
    pom.write_text('<project><url>https://maven.apache.org</url></project>', encoding='utf-8')
    identity = get_project_identity(tmp_path)
    assert identity["project_url"] == "https://maven.apache.org"

def test_get_project_identity_gemspec_homepage(tmp_path):
    gemspec = tmp_path / "test.gemspec"
    gemspec.write_text('Gem::Specification.new do |s| s.name = "my-gem"; s.homepage = "https://rubygems.org" end', encoding='utf-8')
    identity = get_project_identity(tmp_path)
    assert identity["project_url"] == "https://rubygems.org"

def test_get_project_identity_manifest_exception_handling(tmp_path):
    # Target 'except Exception: pass' blocks
    # We use a broad patch to trigger exceptions across different manifest types
    with patch("pathlib.Path.read_text", side_effect=Exception("Read error")):
        # Create files so they are detected, then reading them fails
        (tmp_path / "project.clj").write_text("", encoding='utf-8')
        (tmp_path / "test.podspec").write_text("", encoding='utf-8')
        (tmp_path / "test.gemspec").write_text("", encoding='utf-8')
        (tmp_path / "mix.exs").write_text("", encoding='utf-8')
        (tmp_path / "Package.swift").write_text("", encoding='utf-8')
        (tmp_path / "CMakeLists.txt").write_text("", encoding='utf-8')
        (tmp_path / "Project.toml").write_text("", encoding='utf-8')
        (tmp_path / "deno.json").write_text("", encoding='utf-8')
        (tmp_path / "build.zig.zon").write_text("", encoding='utf-8')
        (tmp_path / "pubspec.yaml").write_text("", encoding='utf-8')
        (tmp_path / "README.md").write_text("", encoding='utf-8')
        (tmp_path / "LICENSE").write_text("", encoding='utf-8')

        identity = get_project_identity(tmp_path)
        assert identity["project_name"] == tmp_path.name
