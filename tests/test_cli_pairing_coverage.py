import sys
import pytest
import logging
from sourcecombine import main

def test_cli_pairing_injection_coverage(tmp_path, monkeypatch):
    """Test CLI pairing flags injection into config."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "main.cpp").write_text("int main() { return 0; }")
    (project_dir / "main.h").write_text("int main();")

    output_dir = tmp_path / "output"

    # --pair, --include-unpaired, --pair-template
    args = [
        "sourcecombine.py",
        str(project_dir),
        "-o", str(output_dir),
        "--pair", "cpp", "h",
        "--include-unpaired",
        "--pair-template", "{{STEM}}.combined_test"
    ]
    monkeypatch.setattr(sys, "argv", args)

    try:
        main()
    except SystemExit as e:
        assert e.code == 0

    assert (output_dir / "main.combined_test").exists()

def test_cli_pairing_injection_no_lists(tmp_path, monkeypatch):
    """Test CLI pairing when source/header extensions are not lists in config."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "main.cpp").write_text("int main() { return 0; }")
    (project_dir / "main.h").write_text("int main();")

    output_dir = tmp_path / "output"

    config_file = tmp_path / "config.yml"
    config_file.write_text("""
pairing:
  enabled: false
  source_extensions: not_a_list
  header_extensions: not_a_list
""", encoding="utf-8")

    args = [
        "sourcecombine.py",
        "--config", str(config_file),
        str(project_dir),
        "-o", str(output_dir),
        "--pair", ".cpp", ".h"
    ]
    monkeypatch.setattr(sys, "argv", args)

    try:
        main()
    except SystemExit as e:
        assert e.code == 0

    assert (output_dir / "main.combined").exists()
