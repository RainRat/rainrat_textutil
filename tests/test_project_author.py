import os
import json
from pathlib import Path
import pytest
import utils
from sourcecombine import find_and_combine_files

def test_project_author_detection_node(tmp_path):
    # package.json with string author
    pkg_json = tmp_path / "package.json"
    pkg_json.write_text(json.dumps({
        "name": "node-project",
        "author": "John Doe <john@example.com>"
    }))
    identity = utils.get_project_identity(tmp_path)
    assert identity["project_author"] == "John Doe <john@example.com>"
    pkg_json.unlink()

    # package.json with object author
    pkg_json.write_text(json.dumps({
        "name": "node-project",
        "author": {"name": "Jane Doe", "email": "jane@example.com"}
    }))
    identity = utils.get_project_identity(tmp_path)
    assert identity["project_author"] == "Jane Doe"

def test_project_author_detection_python(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    # New style
    pyproject.write_text("""
[project]
name = "py-project"
authors = [{name = "Pythonista"}]
""")
    identity = utils.get_project_identity(tmp_path)
    assert identity["project_author"] == "Pythonista"

    # Simple style
    pyproject.write_text("""
[project]
name = "py-project"
author = "Simple Author"
""")
    identity = utils.get_project_identity(tmp_path)
    assert identity["project_author"] == "Simple Author"

def test_project_author_detection_rust(tmp_path):
    cargo = tmp_path / "Cargo.toml"
    cargo.write_text("""
[package]
name = "rust-project"
authors = ["Ferris <ferris@rust-lang.org>", "Other"]
""")
    identity = utils.get_project_identity(tmp_path)
    assert identity["project_author"] == "Ferris <ferris@rust-lang.org>"

def test_project_author_detection_dotnet(tmp_path):
    csproj = tmp_path / "app.csproj"
    csproj.write_text("""
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <Authors>DotNet Dev</Authors>
  </PropertyGroup>
</Project>
""")
    identity = utils.get_project_identity(tmp_path)
    assert identity["project_author"] == "DotNet Dev"

def test_project_author_placeholder_rendering(tmp_path):
    # Setup project
    (tmp_path / "package.json").write_text(json.dumps({
        "name": "render-test",
        "author": "Render Artist"
    }))
    (tmp_path / "file.txt").write_text("content")

    config = utils.DEFAULT_CONFIG.copy()
    config['output'] = config['output'].copy()
    config['output']['global_header_template'] = "Author: {{PROJECT_AUTHOR}}"
    config['search'] = config['search'].copy()
    config['search']['root_folders'] = [str(tmp_path)]

    output_file = tmp_path / "out.txt"
    find_and_combine_files(config, output_file)

    assert "Author: Render Artist" in output_file.read_text()
