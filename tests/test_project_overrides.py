import os
import sys
from pathlib import Path
import pytest
from unittest.mock import patch

# Add root directory to sys.path for imports
sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

import sourcecombine
import utils

def test_project_information_overrides(tmp_path, capsys):
    """Test manual project information overrides via CLI and config."""
    # Create a dummy project structure
    project_dir = tmp_path / "my_project"
    project_dir.mkdir()
    (project_dir / "file1.txt").write_text("Hello World", encoding="utf-8")

    # 1. Test CLI Overrides
    output_file = tmp_path / "combined.txt"
    test_args = [
        "sourcecombine.py",
        str(project_dir),
        "--output", str(output_file),
        "--project-name", "Custom Name",
        "--project-version", "1.2.3",
        "--project-license", "MIT-Custom",
        "--header", "Project: {{PROJECT_NAME}} v{{PROJECT_VERSION}} [{{PROJECT_LICENSE}}]\n"
    ]

    with patch.object(sys, 'argv', test_args):
        try:
            sourcecombine.main()
        except SystemExit as e:
            assert e.code == 0

    content = output_file.read_text(encoding="utf-8")
    assert "Project: Custom Name v1.2.3 [MIT-Custom]" in content

    # 2. Test Config Overrides
    config_file = tmp_path / "config.yml"
    config_content = """
project:
  name: "Config Name"
  version: "4.5.6"
  description: "Config Description"
  license: "Apache-Config"
  url: "https://example.com"
output:
  header_template: "Project: {{PROJECT_NAME}} v{{PROJECT_VERSION}} ({{PROJECT_URL}})\\n"
"""
    config_file.write_text(config_content, encoding="utf-8")

    output_file_2 = tmp_path / "combined_2.txt"
    test_args_2 = [
        "sourcecombine.py",
        str(project_dir),
        "--config", str(config_file),
        "--output", str(output_file_2)
    ]

    with patch.object(sys, 'argv', test_args_2):
        try:
            sourcecombine.main()
        except SystemExit as e:
            assert e.code == 0

    content_2 = output_file_2.read_text(encoding="utf-8")
    assert "Project: Config Name v4.5.6 (https://example.com)" in content_2

def test_license_file_detection(tmp_path):
    """Test automatic detection of project license from a LICENSE file."""
    project_dir = tmp_path / "license_project"
    project_dir.mkdir()
    (project_dir / "LICENSE").write_text("MIT License\n\nCopyright (c) 2023...", encoding="utf-8")

    identity = utils.get_project_identity(project_dir)
    assert identity["project_license"] == "MIT"

    # Test with Apache License
    (project_dir / "LICENSE").write_text("Apache License\nVersion 2.0, January 2004...", encoding="utf-8")
    identity = utils.get_project_identity(project_dir)
    assert identity["project_license"] == "Apache"

    # Test with custom short line
    (project_dir / "LICENSE").write_text("My Custom License", encoding="utf-8")
    identity = utils.get_project_identity(project_dir)
    assert identity["project_license"] == "My Custom License"

    # Test with long first line (fallback to filename)
    (project_dir / "LICENSE").write_text("This is a very long first line that doesn't look like a license name at all and just keeps going on and on...", encoding="utf-8")
    identity = utils.get_project_identity(project_dir)
    assert identity["project_license"] == "LICENSE"

def test_extraction_project_overrides(tmp_path):
    """Test that project overrides also work during extraction templates."""
    combined_content = """[
  {"path": "src/main.py", "content": "print('hello')"}
]"""
    combined_file = tmp_path / "combined.json"
    combined_file.write_text(combined_content, encoding="utf-8")

    extract_dir = tmp_path / "extract_out"
    extract_dir.mkdir()

    # We'll use a config that has a processing rule that might use placeholders if we were doing more complex extraction,
    # but here we just want to see if stats is populated for the summary.

    test_args = [
        "sourcecombine.py",
        str(combined_file),
        "--extract",
        "--output", str(extract_dir),
        "--project-name", "Extracted Project",
        "--json-summary", str(tmp_path / "summary.json")
    ]

    with patch.object(sys, 'argv', test_args):
        try:
            sourcecombine.main()
        except SystemExit as e:
            assert e.code == 0

    summary_content = (tmp_path / "summary.json").read_text(encoding="utf-8")
    assert '"project_name": "Extracted Project"' in summary_content
