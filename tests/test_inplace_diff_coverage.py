import sys
import pytest
from pathlib import Path
from sourcecombine import main

def test_inplace_diff_coverage(tmp_path, monkeypatch, capsys):
    """Test in-place update diff display without dry-run to ensure coverage of line 2153."""

    # Setup test environment
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    file1 = project_dir / "file1.txt"
    file1.write_text("line1\nline2\nline3\n", encoding="utf-8")

    # Configuration that triggers an in-place change via regex
    config_file = tmp_path / "config.yml"
    config_file.write_text("""
search:
  root_folders: ["{project_dir}"]
filters:
  max_total_tokens: 1000000
processing:
  apply_in_place: true
  create_backups: false
  regex_replacements:
    - pattern: 'line2'
      replacement: 'lineTWO'
output:
  show_diff: true
""".format(project_dir=project_dir.as_posix()), encoding="utf-8")

    # Run WITHOUT --dry-run to hit the diff display in the actual update path
    args = ["sourcecombine.py", "--config", str(config_file)]
    monkeypatch.setattr(sys, "argv", args)
    monkeypatch.chdir(tmp_path)

    # Calling main() will run the full logic
    main()

    captured = capsys.readouterr()
    # Check for diff markers in stderr (or wherever _print_diff outputs)
    # _print_diff uses rich/click-like colored output to stderr or stdout.
    # Looking at _print_diff implementation in sourcecombine.py:44:
    # It prints to sys.stdout by default if not redirected, but let's check.

    assert "--- a/file1.txt" in captured.out or "--- a/file1.txt" in captured.err
    assert "+++ b/file1.txt" in captured.out or "+++ b/file1.txt" in captured.err
    assert "-line2" in captured.out or "-line2" in captured.err
    assert "+lineTWO" in captured.out or "+lineTWO" in captured.err

    # Verify file was actually changed
    assert file1.read_text(encoding="utf-8") == "line1\nlineTWO\nline3\n"
