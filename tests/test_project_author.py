import os
import json
from pathlib import Path
import pytest
import utils
from sourcecombine import find_and_combine_files

def test_project_author_detection_json(tmp_path):
    """Test that project author is correctly detected from package.json."""
    pkg_json = tmp_path / "package.json"

    # 1. String author
    pkg_json.write_text(json.dumps({"author": "John Doe"}))
    identity = utils.get_project_identity(tmp_path)
    assert identity["project_author"] == "John Doe"

    # 2. Object author
    pkg_json.write_text(json.dumps({
        "author": {
            "name": "Jane Doe",
            "email": "jane@example.com",
            "url": "https://example.com"
        }
    }))
    identity = utils.get_project_identity(tmp_path)
    assert identity["project_author"] == "Jane Doe <jane@example.com> (https://example.com)"

    # 3. List of authors
    pkg_json.write_text(json.dumps({
        "authors": [
            "Alice",
            {"name": "Bob", "email": "bob@example.com"}
        ]
    }))
    identity = utils.get_project_identity(tmp_path)
    assert identity["project_author"] == "Alice, Bob <bob@example.com>"

def test_project_author_detection_pyproject(tmp_path):
    """Test that project author is correctly detected from pyproject.toml."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("""
[project]
authors = [
    { name = "Python Dev", email = "dev@python.org" }
]
""")
    identity = utils.get_project_identity(tmp_path)
    assert identity["project_author"] == "Python Dev"

def test_project_author_detection_cargo(tmp_path):
    """Test that project author is correctly detected from Cargo.toml."""
    cargo = tmp_path / "Cargo.toml"
    cargo.write_text("""
[package]
authors = ["Rustacean <rust@example.com>", "Second Author"]
""")
    identity = utils.get_project_identity(tmp_path)
    assert identity["project_author"] == "Rustacean <rust@example.com>, Second Author"

def test_project_author_detection_license_fallback(tmp_path):
    """Test that project author is correctly detected from LICENSE fallback."""
    license_file = tmp_path / "LICENSE"
    license_file.write_text("""
Copyright (c) 2024 Author Name. All rights reserved.
MIT License...
""")
    # Ensure no manifest exists
    identity = utils.get_project_identity(tmp_path)
    assert identity["project_author"] == "Author Name"

def test_project_author_cli_override(tmp_path):
    """Test that the --project-author CLI flag correctly overrides manifest values."""
    pkg_json = tmp_path / "package.json"
    pkg_json.write_text(json.dumps({"author": "Manifest Author"}))

    (tmp_path / "hello.txt").write_text("Hello")
    output_file = tmp_path / "combined.txt"

    # We need to mock CLI args for find_and_combine_files or use a test-friendly approach.
    # For simplicity, we'll verify rendering in a template using override logic.

    config = utils.DEFAULT_CONFIG.copy()
    config['output'] = config['output'].copy()
    config['output']['global_header_template'] = "Author: {{PROJECT_AUTHOR}}"
    config['search'] = config['search'].copy()
    config['search']['root_folders'] = [str(tmp_path)]

    # Manually inject the override like sourcecombine.main would do
    config['project'] = config.get('project', {}).copy()
    config['project']['author'] = "CLI Override"

    find_and_combine_files(
        config=config,
        output_path=output_file
    )

    assert "Author: CLI Override" in output_file.read_text()

def test_project_author_cli_main(tmp_path, capsys):
    """Test that the --project-author CLI flag works via main()."""
    import sys
    from unittest.mock import patch
    from sourcecombine import main

    (tmp_path / "hello.txt").write_text("Hello")
    output_file = tmp_path / "combined.txt"

    args = [
        "sourcecombine.py",
        str(tmp_path),
        "--output", str(output_file),
        "--project-author", "Command Line Author",
        "--header", "Auth: {{PROJECT_AUTHOR}}\n"
    ]

    with patch.object(sys, 'argv', args):
        try:
            main()
        except SystemExit as exc:
            assert exc.code == 0

    content = output_file.read_text()
    assert "Auth: Command Line Author" in content

def test_project_author_info_command(tmp_path, capsys):
    """Test that --project-info shows the author."""
    import sys
    from unittest.mock import patch
    from sourcecombine import main

    pkg_json = tmp_path / "package.json"
    pkg_json.write_text(json.dumps({"name": "test-p", "author": "Info Author"}))

    args = [
        "sourcecombine.py",
        str(tmp_path),
        "--project-info"
    ]

    with patch.object(sys, 'argv', args):
        try:
            main()
        except SystemExit as exc:
            assert exc.code == 0

    captured = capsys.readouterr()
    assert "Author" in captured.out
    assert "Info Author" in captured.out

def test_project_author_autodetect_rendered(tmp_path):
    """Test that autodetected author from package.json is rendered without overrides."""
    pkg_json = tmp_path / "package.json"
    pkg_json.write_text(json.dumps({
        "name": "auto-p",
        "author": "Auto Author"
    }))
    (tmp_path / "hello.txt").write_text("Hello")
    output_file = tmp_path / "combined.txt"

    config = utils.DEFAULT_CONFIG.copy()
    config['output'] = config['output'].copy()
    config['output']['global_header_template'] = "AUTH: {{PROJECT_AUTHOR}}"
    config['search'] = config['search'].copy()
    config['search']['root_folders'] = [str(tmp_path)]

    find_and_combine_files(config, output_file)

    assert "AUTH: Auto Author" in output_file.read_text()
