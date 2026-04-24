import sys
import io
import os
from pathlib import Path
import pytest
from sourcecombine import main

def test_diff_combined_output(tmp_path, monkeypatch, capsys):
    # Setup test environment
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    file1 = project_dir / "file1.py"
    file1.write_text("print('hello')\n", encoding="utf-8")

    output_file = tmp_path / "combined.txt"
    # Existing content that differs from what would be generated
    output_file.write_text("old content\n", encoding="utf-8")

    # Run with --output and --diff and --dry-run
    # We use --include "*.py" to be explicit
    args = ["sourcecombine.py", str(project_dir), "-o", str(output_file), "--diff", "--dry-run", "--include", "*.py"]
    monkeypatch.setattr(sys, "argv", args)

    # Force NO_COLOR to empty string to ensure colors are rendered if we mock isatty
    monkeypatch.setenv("NO_COLOR", "")

    main()

    captured = capsys.readouterr()
    # Check for diff markers in stderr
    assert f"--- a/{output_file}" in captured.err or f"--- a/{output_file.as_posix()}" in captured.err
    assert f"+++ b/{output_file}" in captured.err or f"+++ b/{output_file.as_posix()}" in captured.err
    assert "-old content" in captured.err
    assert "print('hello')" in captured.err

def test_diff_paired_output(tmp_path, monkeypatch, capsys):
    # Setup test environment
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    # Source and header pair
    src = project_dir / "main.cpp"
    src.write_text("int main() { return 0; }\n", encoding="utf-8")
    hdr = project_dir / "main.h"
    hdr.write_text("int main();\n", encoding="utf-8")

    out_dir = tmp_path / "pairs"
    out_dir.mkdir()

    # Existing paired output with different content
    existing_paired = out_dir / "main.combined"
    existing_paired.write_text("outdated paired content\n", encoding="utf-8")

    # Run with --pair, --output, --diff, --dry-run
    args = [
        "sourcecombine.py", str(project_dir),
        "-o", str(out_dir),
        "--pair", ".cpp", ".h",
        "--diff", "--dry-run",
        "--pair-template", "{{STEM}}.combined"
    ]
    monkeypatch.setattr(sys, "argv", args)
    monkeypatch.setenv("NO_COLOR", "")

    main()

    captured = capsys.readouterr()
    # Check for diff markers in stderr for the paired file
    # _process_paired_files uses as_posix() for filenames in diff
    expected_file_label = existing_paired.as_posix()
    assert f"--- a/{expected_file_label}" in captured.err
    assert f"+++ b/{expected_file_label}" in captured.err
    assert "-outdated paired content" in captured.err
    assert "+int main();" in captured.err
    assert "+int main() { return 0; }" in captured.err

def test_diff_no_output_file_exists(tmp_path, monkeypatch, capsys):
    # Setup test environment
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    file1 = project_dir / "file1.py"
    file1.write_text("print('hello')\n", encoding="utf-8")

    output_file = tmp_path / "new_combined.txt"
    # output_file does NOT exist

    args = ["sourcecombine.py", str(project_dir), "-o", str(output_file), "--diff", "--dry-run"]
    monkeypatch.setattr(sys, "argv", args)

    main()

    captured = capsys.readouterr()
    # Should NOT show a diff since the file doesn't exist to compare against
    assert "--- a/" not in captured.err
    assert "+++ b/" not in captured.err
