import os
import json
from pathlib import Path
import pytest
import utils
from sourcecombine import find_and_combine_files

def test_project_identity_detection(tmp_path):
    """Test that project identity is correctly detected from various manifest files."""

    # 1. package.json
    pkg_json = tmp_path / "package.json"
    pkg_json.write_text(json.dumps({
        "name": "node-project",
        "version": "1.2.3",
        "description": "A node project",
        "license": "MIT"
    }))
    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "node-project"
    assert identity["project_version"] == "1.2.3"
    assert identity["project_description"] == "A node project"
    assert identity["project_license"] == "MIT"
    pkg_json.unlink()

    # 2. pyproject.toml
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("""
[project]
name = "py-project"
version = "0.1.0"
description = "A python project"
license = {text = "Apache-2.0"}
""")
    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "py-project"
    assert identity["project_version"] == "0.1.0"
    assert identity["project_description"] == "A python project"
    assert identity["project_license"] == "Apache-2.0"
    pyproject.unlink()

    # 3. Cargo.toml
    cargo = tmp_path / "Cargo.toml"
    cargo.write_text("""
[package]
name = "rust-project"
version = "1.0.0"
description = "A rust project"
license = "GPL-3.0"
""")
    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "rust-project"
    assert identity["project_version"] == "1.0.0"
    assert identity["project_description"] == "A rust project"
    assert identity["project_license"] == "GPL-3.0"
    cargo.unlink()

def test_project_placeholders_rendering(tmp_path):
    """Test that project placeholders are correctly rendered in the output."""

    # Setup a project with package.json
    pkg_json = tmp_path / "package.json"
    pkg_json.write_text(json.dumps({
        "name": "my-app",
        "version": "2.0.0",
        "description": "My awesome app",
        "license": "ISC"
    }))

    # Create a dummy file to combine
    (tmp_path / "hello.txt").write_text("Hello")

    config = utils.DEFAULT_CONFIG.copy()
    config['output'] = config['output'].copy()
    config['output']['global_header_template'] = "Project: {{PROJECT_NAME}} v{{PROJECT_VERSION}}\nDesc: {{PROJECT_DESCRIPTION}}\nLicense: {{PROJECT_LICENSE}}\n"
    config['search'] = config['search'].copy()
    config['search']['root_folders'] = [str(tmp_path)]

    output_file = tmp_path / "combined.txt"

    # Run find_and_combine_files
    find_and_combine_files(
        config=config,
        output_path=output_file
    )

    content = output_file.read_text()
    assert "Project: my-app v2.0.0" in content
    assert "Desc: My awesome app" in content
    assert "License: ISC" in content
