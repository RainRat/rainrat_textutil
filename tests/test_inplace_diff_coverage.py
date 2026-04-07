import sys
import pytest
from sourcecombine import main

def test_inplace_diff_during_metadata_pass(tmp_path, monkeypatch, capsys):
    # Setup test environment
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    file1 = project_dir / "file1.txt"
    file1.write_text("old content\n", encoding="utf-8")

    config_file = tmp_path / "config.yml"
    config_file.write_text(f"""
search:
  root_folders:
    - {project_dir.as_posix()}
processing:
  apply_in_place: true
  regex_replacements:
    - pattern: 'old'
      replacement: 'new'
output:
  show_diff: true
  sort_by: 'size'  # This triggers the metadata pass
  file: {(tmp_path / "combined.txt").as_posix()}
""", encoding="utf-8")

    # Run without --dry-run and without --estimate-tokens
    args = ["sourcecombine.py", "--config", str(config_file)]
    monkeypatch.setattr(sys, "argv", args)

    try:
        main()
    except SystemExit as e:
        assert e.code == 0

    captured = capsys.readouterr()
    # Check for diff markers in stderr
    assert "--- a/file1.txt" in captured.err
    assert "+++ b/file1.txt" in captured.err
    assert "-old content" in captured.err
    assert "+new content" in captured.err

    # Verify file was actually updated
    assert file1.read_text(encoding="utf-8") == "new content\n"
