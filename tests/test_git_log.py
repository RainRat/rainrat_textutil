import os
import subprocess
import pytest
from pathlib import Path
from sourcecombine import main

def test_git_log_feature(tmp_path, monkeypatch, capsys):
    # Setup a dummy git repo
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()

    # Change to repo_dir
    monkeypatch.chdir(repo_dir)

    # Init git
    subprocess.run(["git", "init"], check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "you@example.com"], check=True)
    subprocess.run(["git", "config", "user.name", "Your Name"], check=True)

    # Create a file and commit it
    test_file = repo_dir / "test.txt"
    test_file.write_text("Hello World", encoding="utf-8")
    subprocess.run(["git", "add", "test.txt"], check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], check=True)

    # Create another commit
    test_file.write_text("Hello World 2", encoding="utf-8")
    subprocess.run(["git", "add", "test.txt"], check=True)
    subprocess.run(["git", "commit", "-m", "Second commit"], check=True)

    # Output file
    output_file = tmp_path / "output.txt"

    # Run sourcecombine with --overview and --git-log
    monkeypatch.setattr("sys.argv", ["sourcecombine.py", str(repo_dir), "-o", str(output_file), "--overview", "--git-log", "2"])

    main()

    # Verify output
    content = output_file.read_text(encoding="utf-8")
    assert "Recent Changes:" in content
    assert "Second commit" in content
    assert "Initial commit" in content

def test_git_log_markdown(tmp_path, monkeypatch):
    # Setup a dummy git repo
    repo_dir = tmp_path / "repo_md"
    repo_dir.mkdir()
    monkeypatch.chdir(repo_dir)

    subprocess.run(["git", "init"], check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "you@example.com"], check=True)
    subprocess.run(["git", "config", "user.name", "Your Name"], check=True)

    (repo_dir / "a.py").write_text("print(1)", encoding="utf-8")
    subprocess.run(["git", "add", "a.py"], check=True)
    subprocess.run(["git", "commit", "-m", "Commit A"], check=True)

    output_file = tmp_path / "output.md"
    monkeypatch.setattr("sys.argv", ["sourcecombine.py", ".", "-o", str(output_file), "--overview", "--git-log", "1", "--markdown"])

    main()

    content = output_file.read_text(encoding="utf-8")
    assert "### Recent Changes" in content
    assert "```text" in content
    assert "Commit A" in content
