import pytest
from pathlib import Path
import utils

def test_pubspec_yaml_detection(tmp_path):
    pubspec_content = """
name: my_flutter_app
description: A new Flutter project.
version: 1.0.0+1
homepage: https://example.com/flutter_app
repository: https://github.com/example/flutter_app

environment:
  sdk: '>=3.0.0 <4.0.0'

dependencies:
  flutter:
    sdk: flutter
"""
    pubspec_file = tmp_path / "pubspec.yaml"
    pubspec_file.write_text(pubspec_content)

    identity = utils.get_project_identity(tmp_path)

    assert identity["project_name"] == "my_flutter_app"
    assert identity["project_version"] == "1.0.0+1"
    assert identity["project_description"] == "A new Flutter project."
    assert identity["project_url"] == "https://example.com/flutter_app"
    assert identity["manifest_source"] == "pubspec.yaml"

def test_pubspec_yaml_no_homepage(tmp_path):
    pubspec_content = """
name: my_dart_lib
repository: https://github.com/example/dart_lib
"""
    pubspec_file = tmp_path / "pubspec.yaml"
    pubspec_file.write_text(pubspec_content)

    identity = utils.get_project_identity(tmp_path)

    assert identity["project_name"] == "my_dart_lib"
    assert identity["project_url"] == "https://github.com/example/dart_lib"

def test_package_json_url_extraction(tmp_path):
    package_json_content = """
{
  "name": "node-project",
  "version": "1.2.3",
  "homepage": "https://node-project.org"
}
"""
    (tmp_path / "package.json").write_text(package_json_content)

    identity = utils.get_project_identity(tmp_path)
    assert identity["project_url"] == "https://node-project.org"

def test_pyproject_toml_url_extraction(tmp_path):
    pyproject_toml_content = """
[project]
name = "python-project"
version = "0.1.0"

[project.urls]
Homepage = "https://python-project.io"
"""
    (tmp_path / "pyproject.toml").write_text(pyproject_toml_content)

    identity = utils.get_project_identity(tmp_path)
    assert identity["project_url"] == "https://python-project.io"

def test_cargo_toml_url_extraction(tmp_path):
    cargo_toml_content = """
[package]
name = "rust-crate"
version = "0.5.0"
homepage = "https://rust-crate.rs"
"""
    (tmp_path / "Cargo.toml").write_text(cargo_toml_content)

    identity = utils.get_project_identity(tmp_path)
    assert identity["project_url"] == "https://rust-crate.rs"
