import pytest
from pathlib import Path
from utils import get_project_identity, get_language_tag

def test_get_project_identity_pubspec_yaml(tmp_path):
    """Test that get_project_identity correctly parses pubspec.yaml."""
    pubspec_content = """
name: my_awesome_app
description: A very cool Flutter application.
version: 1.2.3+4
homepage: https://example.com
environment:
  sdk: ">=2.12.0 <3.0.0"
"""
    pubspec_file = tmp_path / "pubspec.yaml"
    pubspec_file.write_text(pubspec_content, encoding='utf-8')

    identity = get_project_identity(tmp_path)

    assert identity["project_name"] == "my_awesome_app"
    assert identity["project_version"] == "1.2.3+4"
    assert identity["project_description"] == "A very cool Flutter application."
    assert identity["manifest_source"] == "pubspec.yaml"

def test_get_project_identity_pubspec_quoted(tmp_path):
    """Test pubspec parsing with quoted values and comments."""
    pubspec_content = """
name: 'quoted_name' # name comment
version: "2.0.0" # version comment
description: 'Quoted description'
"""
    pubspec_file = tmp_path / "pubspec.yaml"
    pubspec_file.write_text(pubspec_content, encoding='utf-8')

    identity = get_project_identity(tmp_path)

    assert identity["project_name"] == "quoted_name"
    assert identity["project_version"] == "2.0.0"
    assert identity["project_description"] == "Quoted description"

def test_language_tag_pubspec():
    """Test that pubspec.yaml/lock are mapped to yaml language."""
    assert get_language_tag("pubspec.yaml") == "yaml"
    assert get_language_tag("pubspec.lock") == "yaml"
    assert get_language_tag("mix.exs") == "elixir"
    assert get_language_tag("Project.toml") == "toml"
