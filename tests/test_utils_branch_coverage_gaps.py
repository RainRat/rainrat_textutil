import os
import sys
from pathlib import Path

sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

import pytest
import utils


def test_parse_json_manifest_non_dict(tmp_path):
    manifest = tmp_path / "package.json"
    manifest.write_text("[1, 2, 3]", encoding="utf-8")
    identity = {}
    assert utils._parse_json_manifest(manifest, identity) is False


def test_gradle_without_name_and_version(tmp_path):
    settings = tmp_path / "settings.gradle"
    settings.write_text("// no rootProject.name line here", encoding="utf-8")
    build = tmp_path / "build.gradle"
    build.write_text("// no version line here", encoding="utf-8")

    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == tmp_path.name
    assert identity["project_version"] == ""
    assert identity["manifest_source"] == "settings.gradle"


def test_clojure_without_defproject(tmp_path):
    project_clj = tmp_path / "project.clj"
    project_clj.write_text(";; comment without defproject", encoding="utf-8")

    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == tmp_path.name
    assert identity["project_version"] == ""
    assert identity["manifest_source"] == "project.clj"


def test_podspec_without_name(tmp_path):
    podspec = tmp_path / "test.podspec"
    podspec.write_text("Pod::Spec.new do |s|\n  s.summary = 'Only summary'\nend", encoding="utf-8")

    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == tmp_path.name
    assert identity["project_description"] == "Only summary"
    assert identity["manifest_source"] == "test.podspec"


def test_pyproject_authors_dict_without_name_and_license_dict_without_text(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        "[project]\nname = 'pkg'\nversion = '1.0.0'\n"
        "authors = [{ email = 'foo@example.com' }]\n"
        "license = { file = 'LICENSE' }\n",
        encoding="utf-8"
    )

    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "pkg"
    assert identity["project_author"] == ""
    assert identity["project_license"] == ""


def test_cargo_repository_fallback_without_homepage(tmp_path):
    cargo = tmp_path / "Cargo.toml"
    cargo.write_text(
        "[package]\nname = 'cargopkg'\nversion = '0.1.0'\n"
        "repository = 'https://github.com/org/repo'\n",
        encoding="utf-8"
    )

    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "cargopkg"
    assert identity["project_url"] == "https://github.com/org/repo"


def test_pom_xml_developers_and_license_without_name(tmp_path):
    pom = tmp_path / "pom.xml"
    pom.write_text(
        "<project>\n"
        "  <artifactId>pompkg</artifactId>\n"
        "  <developers><developer><id>dev1</id></developer></developers>\n"
        "  <licenses><license><url>http://example.com</url></license></licenses>\n"
        "</project>",
        encoding="utf-8"
    )

    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "pompkg"
    assert identity["project_author"] == ""
    assert identity["project_license"] == ""


def test_zig_zon_without_version(tmp_path):
    zon = tmp_path / "build.zig.zon"
    zon.write_text('.{\n  .name = "zigpkg",\n}\n', encoding="utf-8")

    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "zigpkg"
    assert identity["project_version"] == ""
    assert identity["manifest_source"] == "build.zig.zon"


def test_deno_jsonc_without_name_or_version(tmp_path):
    deno = tmp_path / "deno.jsonc"
    deno.write_text("// Deno config\n{\n  \"description\": \"A deno package\"\n}\n", encoding="utf-8")

    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == tmp_path.name
    assert identity["project_description"] == "A deno package"
    assert identity["manifest_source"] == "deno.jsonc"


def test_readme_header_followed_by_subheader_leaves_description_empty(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text("# Main Title\n\n## Subheader\n\nSubheader text here.", encoding="utf-8")

    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "Main Title"
    assert identity["project_description"] == ""


def test_license_fallback_with_prepopulated_author(tmp_path):
    pkg = tmp_path / "package.json"
    pkg.write_text('{"name": "pkg", "author": "Prepopulated Author"}', encoding="utf-8")
    lic = tmp_path / "LICENSE"
    lic.write_text("MIT License\nCopyright 2024 Prepopulated Author", encoding="utf-8")

    identity = utils.get_project_identity(tmp_path)
    assert identity["project_author"] == "Prepopulated Author"
    assert identity["project_license"] == "MIT"
