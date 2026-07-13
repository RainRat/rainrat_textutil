import json
import os
import sys
from pathlib import Path
from unittest.mock import patch
import pytest
from sourcecombine import main
import utils

def test_format_author():
    assert utils._format_author("John Doe") == "John Doe"
    assert utils._format_author({"name": "John Doe"}) == "John Doe"
    assert utils._format_author({"name": "John Doe", "email": "john@example.com"}) == "John Doe <john@example.com>"
    assert utils._format_author({"name": "John Doe", "url": "https://example.com"}) == "John Doe (https://example.com)"
    assert utils._format_author({"name": "John Doe", "email": "john@example.com", "url": "https://example.com"}) == "John Doe <john@example.com> (https://example.com)"
    assert utils._format_author([{"name": "John"}, {"name": "Jane"}]) == "John, Jane"
    assert utils._format_author(None) is None

def test_author_detection_package_json(tmp_path):
    pkg_json = tmp_path / "package.json"
    pkg_json.write_text(json.dumps({"name": "test-pkg", "author": "John Doe"}), encoding="utf-8")
    identity = utils.get_project_identity(tmp_path)
    assert identity["project_author"] == "John Doe"

    pkg_json.write_text(json.dumps({"name": "test-pkg", "author": {"name": "Jane Doe", "email": "jane@example.com"}}), encoding="utf-8")
    identity = utils.get_project_identity(tmp_path)
    assert identity["project_author"] == "Jane Doe <jane@example.com>"

def test_author_detection_pyproject_toml(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('authors = [{name = "Pythonista"}]', encoding="utf-8")
    identity = utils.get_project_identity(tmp_path)
    assert identity["project_author"] == "Pythonista"

def test_author_detection_cargo_toml(tmp_path):
    cargo = tmp_path / "Cargo.toml"
    cargo.write_text('[package]\nname = "rust-pkg"\nauthors = ["Rustacean <rust@example.com>"]', encoding="utf-8")
    identity = utils.get_project_identity(tmp_path)
    assert identity["project_author"] == "Rustacean <rust@example.com>"

def test_author_detection_license_fallback(tmp_path):
    license_file = tmp_path / "LICENSE"
    license_file.write_text("Copyright (c) 2023 Original Author", encoding="utf-8")
    identity = utils.get_project_identity(tmp_path)
    assert identity["project_author"] == "Original Author"

def test_project_author_cli_override(tmp_path, capsys):
    (tmp_path / "file1.txt").write_text("content", encoding="utf-8")

    with patch.object(sys, 'argv', ["sourcecombine", "--project-author", "CLI Author", "--project-info", str(tmp_path)]):
        with pytest.raises(SystemExit):
            main()

    out, err = capsys.readouterr()
    assert "Author" in out
    assert "CLI Author" in out

def test_project_author_placeholder(tmp_path):
    (tmp_path / "file1.txt").write_text("content", encoding="utf-8")
    output_file = tmp_path / "output.txt"

    # We use a dummy package.json to set the author
    (tmp_path / "package.json").write_text(json.dumps({"name": "test", "author": "Manifest Author"}), encoding="utf-8")

    with patch.object(sys, 'argv', ["sourcecombine", str(tmp_path), "--output", str(output_file), "--global-header", "Author: {{PROJECT_AUTHOR}}", "--exclude-file", "package.json"]):
        main()

    content = output_file.read_text(encoding="utf-8")
    assert "Author: Manifest Author" in content
