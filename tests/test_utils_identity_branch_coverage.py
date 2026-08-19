from pathlib import Path
import pytest
import utils


def test_gradle_settings_kts_and_build_gradle_kts(tmp_path):
    # Tests settings.gradle.kts fallback and build.gradle.kts version extraction
    settings_file = tmp_path / "settings.gradle.kts"
    settings_file.write_text('rootProject.name = "kts_proj"', encoding="utf-8")
    build_file = tmp_path / "build.gradle.kts"
    build_file.write_text('version = "1.2.3"', encoding="utf-8")

    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "kts_proj"
    assert identity["project_version"] == "1.2.3"
    assert identity["manifest_source"] == "settings.gradle.kts"


def test_podspec_with_authors(tmp_path):
    podspec = tmp_path / "test.podspec"
    podspec.write_text("Pod::Spec.new do |s|\n  s.name = 'MyPod'\n  s.authors = 'Alice <alice@example.com>'\nend", encoding="utf-8")
    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "MyPod"
    assert identity["project_author"] == "Alice <alice@example.com>"


def test_podspec_without_authors(tmp_path):
    podspec = tmp_path / "test.podspec"
    podspec.write_text("Pod::Spec.new do |s|\n  s.name = 'MyPod'\n  s.version = '1.0'\nend", encoding="utf-8")
    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "MyPod"
    assert identity["project_author"] == ""


def test_pyproject_table_license_and_urls(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        "[project]\nname = 'tablepkg'\nversion = '0.1.0'\n"
        "[project.license]\ntext = 'Apache-2.0'\n"
        "[project.urls]\nhomepage = 'https://example.com'\n",
        encoding="utf-8"
    )
    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "tablepkg"
    assert identity["project_license"] == "Apache-2.0"
    assert identity["project_url"] == "https://example.com"


def test_pyproject_dict_license(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        "[project]\nname = 'dictpkg'\nlicense = { text = 'BSD-3-Clause' }\n",
        encoding="utf-8"
    )
    identity = utils.get_project_identity(tmp_path)
    assert identity["project_license"] == "BSD-3-Clause"


def test_pyproject_without_authors_and_license(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[project]\nname = 'mypkg'\nversion = '0.1.0'\n", encoding="utf-8")
    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "mypkg"
    assert identity["project_author"] == ""
    assert identity["project_license"] == ""


def test_gemspec_with_homepage(tmp_path):
    gemspec = tmp_path / "mygem.gemspec"
    gemspec.write_text("Gem::Specification.new do |s|\n  s.name = 'mygem'\n  s.homepage = 'https://gems.example.com'\nend", encoding="utf-8")
    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "mygem"
    assert identity["project_url"] == "https://gems.example.com"


def test_gemspec_without_homepage(tmp_path):
    gemspec = tmp_path / "mygem.gemspec"
    gemspec.write_text("Gem::Specification.new do |s|\n  s.name = 'mygem'\n  s.version = '0.2.0'\nend", encoding="utf-8")
    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "mygem"
    assert identity["project_url"] == ""


def test_elixir_mix_with_homepage(tmp_path):
    mix = tmp_path / "mix.exs"
    mix.write_text('defmodule MyMix.MixProject do\n  app: :mymix,\n  homepage_url: "https://elixir.example.com"\nend', encoding="utf-8")
    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "mymix"
    assert identity["project_url"] == "https://elixir.example.com"


def test_elixir_mix_without_homepage(tmp_path):
    mix = tmp_path / "mix.exs"
    mix.write_text("defmodule MyMix.MixProject do\n  app: :mymix,\n  version: \"0.3.0\"\nend", encoding="utf-8")
    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "mymix"
    assert identity["project_url"] == ""


def test_swift_package_with_name(tmp_path):
    pkg = tmp_path / "Package.swift"
    pkg.write_text('// swift-tools-version:5.5\nimport PackageDescription\nlet package = Package(\n  name: "MySwiftPkg"\n)\n', encoding="utf-8")
    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "MySwiftPkg"
    assert identity["manifest_source"] == "Package.swift"


def test_swift_package_without_name(tmp_path):
    pkg = tmp_path / "Package.swift"
    pkg.write_text("// swift-tools-version:5.5\nimport PackageDescription\n", encoding="utf-8")
    identity = utils.get_project_identity(tmp_path)
    assert identity["manifest_source"] == "Package.swift"


def test_cmake_with_full_details(tmp_path):
    cmake = tmp_path / "CMakeLists.txt"
    cmake.write_text(
        'project(FullCMake VERSION 2.5.0 DESCRIPTION "A complete CMake project" HOMEPAGE_URL "https://cmake.example.com")\n',
        encoding="utf-8"
    )
    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "FullCMake"
    assert identity["project_version"] == "2.5.0"
    assert identity["project_description"] == "A complete CMake project"
    assert identity["project_url"] == "https://cmake.example.com"


def test_cmake_without_project_call(tmp_path):
    cmake = tmp_path / "CMakeLists.txt"
    cmake.write_text("cmake_minimum_required(VERSION 3.10)\n", encoding="utf-8")
    identity = utils.get_project_identity(tmp_path)
    assert identity["manifest_source"] is None


def test_julia_project_with_version(tmp_path):
    julia = tmp_path / "Project.toml"
    julia.write_text('name = "MyJuliaApp"\nversion = "1.4.2"\n', encoding="utf-8")
    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "MyJuliaApp"
    assert identity["project_version"] == "1.4.2"


def test_julia_project_without_version(tmp_path):
    julia = tmp_path / "Project.toml"
    julia.write_text("name = \"MyJuliaApp\"\n", encoding="utf-8")
    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "MyJuliaApp"
    assert identity["project_version"] == ""


def test_readme_atx_header_and_long_description(tmp_path):
    readme = tmp_path / "README.md"
    long_desc = "This is a very long description that exceeds two hundred characters in length. " * 4
    readme.write_text(f"# ATX Project\n\n{long_desc}\n", encoding="utf-8")
    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "ATX Project"
    assert identity["project_description"].endswith("...")
    assert len(identity["project_description"]) == 200


def test_readme_setext_header_and_no_header(tmp_path):
    # Setext H1 header
    dir1 = tmp_path / "d1"
    dir1.mkdir()
    readme1 = dir1 / "README.md"
    readme1.write_text("Setext App\n==========\nSome description here.\n", encoding="utf-8")
    identity1 = utils.get_project_identity(dir1)
    assert identity1["project_name"] == "Setext App"
    assert identity1["project_description"] == "Some description here."

    # No H1 header at all
    dir2 = tmp_path / "d2"
    dir2.mkdir()
    readme2 = dir2 / "README.md"
    readme2.write_text("Just plain text in readme.\n", encoding="utf-8")
    identity2 = utils.get_project_identity(dir2)
    assert identity2["project_name"] == "d2"
    assert identity2["project_description"] == ""


def test_license_fallback_branches(tmp_path):
    # 1. License and author already present (from package.json)
    dir1 = tmp_path / "d1"
    dir1.mkdir()
    (dir1 / "package.json").write_text('{"name": "p1", "license": "MIT", "author": "Alice"}', encoding="utf-8")
    (dir1 / "LICENSE").write_text("Copyright (c) 2024 Bob", encoding="utf-8")
    id1 = utils.get_project_identity(dir1)
    assert id1["project_author"] == "Alice"
    assert id1["project_license"] == "MIT"

    # 2. License already present, author missing -> extracts author from LICENSE
    dir2 = tmp_path / "d2"
    dir2.mkdir()
    (dir2 / "package.json").write_text('{"name": "p2", "license": "MIT"}', encoding="utf-8")
    (dir2 / "LICENSE").write_text("Copyright (c) 2024 Bob", encoding="utf-8")
    id2 = utils.get_project_identity(dir2)
    assert id2["project_author"] == "Bob"
    assert id2["project_license"] == "MIT"

    # 3. Long first line (>= 50 chars) without license keyword in LICENSE
    dir3 = tmp_path / "d3"
    dir3.mkdir()
    long_line = "A" * 60 + "\nCopyright (c) 2024 Charlie"
    (dir3 / "LICENSE").write_text(long_line, encoding="utf-8")
    id3 = utils.get_project_identity(dir3)
    assert id3["project_license"] == "LICENSE"
    assert id3["project_author"] == "Charlie"

    # 4. Short first line (< 50 chars) without license keyword in LICENSE
    dir4 = tmp_path / "d4"
    dir4.mkdir()
    short_line = "Custom License Agreement\nCopyright (c) 2024 Dave"
    (dir4 / "LICENSE").write_text(short_line, encoding="utf-8")
    id4 = utils.get_project_identity(dir4)
    assert id4["project_license"] == "Custom License Agreement"
    assert id4["project_author"] == "Dave"

    # 5. Empty license file
    dir5 = tmp_path / "d5"
    dir5.mkdir()
    (dir5 / "LICENSE").write_text("   \n  \n", encoding="utf-8")
    id5 = utils.get_project_identity(dir5)
    assert id5["project_license"] == ""

    # 6. Copyright matches but author cleans to empty string
    dir6 = tmp_path / "d6"
    dir6.mkdir()
    (dir6 / "LICENSE").write_text("MIT License\nCopyright 2024 . All rights reserved", encoding="utf-8")
    id6 = utils.get_project_identity(dir6)
    assert id6["project_license"] == "MIT"
    assert id6["project_author"] == ""


def test_get_project_identity_outer_exception(monkeypatch):
    monkeypatch.setattr(utils.Path, "resolve", lambda self: (_ for _ in ()).throw(RuntimeError("OS Error")))
    identity = utils.get_project_identity("some_path")
    assert identity["project_name"] == "Project"
