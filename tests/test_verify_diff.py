import sys
import pytest
from pathlib import Path
from sourcecombine import verify_files, main

def test_verify_files_with_diff(tmp_path, capsys, monkeypatch):
    """Verify that verify_files correctly shows a diff when requested."""
    monkeypatch.setenv("NO_COLOR", "1") # Disable colors for easier assertion

    root = tmp_path / "root"
    root.mkdir()
    file_path = root / "test.txt"
    file_path.write_text("actual content", encoding="utf-8")

    sources = [
        ("combined.txt", "--- test.txt ---\nexpected content\n--- end test.txt ---\n")
    ]

    # Run with show_diff=True
    verify_files(sources, root_folder=root, show_diff=True)

    captured = capsys.readouterr()
    assert "[MISMATCH] test.txt (content mismatch)" in captured.out
    assert "--- a/test.txt" in captured.err
    assert "+++ b/test.txt" in captured.err
    assert "-actual content" in captured.err
    assert "+expected content" in captured.err

def test_verify_cli_diff(tmp_path, capsys, monkeypatch):
    """Verify that the CLI correctly passes the --diff flag to verification."""
    monkeypatch.setenv("NO_COLOR", "1")

    root = tmp_path / "root"
    root.mkdir()
    file_path = root / "test.txt"
    file_path.write_text("actual content", encoding="utf-8")

    combined_file = tmp_path / "combined.json"
    import json
    combined_file.write_text(json.dumps([
        {"path": "test.txt", "content": "expected content"}
    ]), encoding="utf-8")

    # Run CLI: python sourcecombine.py --verify combined.json --diff
    monkeypatch.setattr(sys, "argv", ["sourcecombine.py", "--verify", str(combined_file), "--diff"])
    # Need to be in a directory where it can find the file, or use absolute path
    # verify_files uses root_folder="." in main, so we should change cwd or mock it
    monkeypatch.chdir(root)

    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0

    captured = capsys.readouterr()
    assert "[MISMATCH] test.txt (content mismatch)" in captured.out
    assert "--- a/test.txt" in captured.err
    assert "+expected content" in captured.err
