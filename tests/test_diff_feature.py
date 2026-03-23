import os
import sys
import pytest
from pathlib import Path
from sourcecombine import main, find_and_combine_files

def test_diff_apply_in_place(tmp_path, monkeypatch, capsys):
    from sourcecombine import C_GREEN, C_RED, C_CYAN, C_BOLD, C_RESET
    # Force NO_COLOR to empty string to ensure colors are rendered if we mock isatty
    monkeypatch.setenv("NO_COLOR", "")

    # Setup test environment
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    file1 = project_dir / "file1.txt"
    file1.write_text("line1\nline2\nline3\n", encoding="utf-8")

    # Run with apply-in-place and compact (which should change the file) and --diff
    # Use dry-run to avoid actual changes but still see the diff
    args = ["sourcecombine.py", str(project_dir), "--apply-in-place", "--compact", "--diff", "--dry-run"]
    monkeypatch.setattr(sys, "argv", args)

    # Mock compact_blank_lines to actually change something if compact is not enough
    # Actually, let's just use a regex replacement that we know will change something
    config_file = tmp_path / "config.yml"
    config_file.write_text("""
processing:
  apply_in_place: true
  regex_replacements:
    - pattern: 'line2'
      replacement: 'lineTWO'
output:
  show_diff: true
""", encoding="utf-8")

    args = ["sourcecombine.py", "--config", str(config_file), str(project_dir), "--dry-run"]
    monkeypatch.setattr(sys, "argv", args)

    main()

    captured = capsys.readouterr()
    # Check for diff markers in stderr
    assert "--- a/file1.txt" in captured.err
    assert "+++ b/file1.txt" in captured.err
    assert "-line1" not in captured.err # Context line
    assert "-line2" in captured.err
    assert "+lineTWO" in captured.err

def test_diff_extract(tmp_path, monkeypatch, capsys):
    # Setup test environment
    extract_dir = tmp_path / "extract"
    extract_dir.mkdir()

    # Existing file with different content
    existing_file = extract_dir / "file1.txt"
    existing_file.write_text("old content\n", encoding="utf-8")

    # Combined file content
    combined_content = """--- file1.txt ---
new content
--- end file1.txt ---
"""
    combined_file = tmp_path / "combined.txt"
    combined_file.write_text(combined_content, encoding="utf-8")

    # Run extraction with --diff
    args = ["sourcecombine.py", "--extract", str(combined_file), "-o", str(extract_dir), "--diff", "--dry-run"]
    monkeypatch.setattr(sys, "argv", args)

    with pytest.raises(SystemExit):
        main()

    captured = capsys.readouterr()
    # Check for diff markers in stderr
    assert "--- a/file1.txt" in captured.err
    assert "+++ b/file1.txt" in captured.err
    assert "-old content" in captured.err
    assert "+new content" in captured.err
