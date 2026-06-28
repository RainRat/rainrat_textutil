import os
import subprocess
import sys
from pathlib import Path
import pytest
from sourcecombine import main

def test_project_info_basic(tmp_path, capsys, monkeypatch, mocker):
    """Test that --project-info displays basic project metadata."""
    project_dir = tmp_path / "my_project"
    project_dir.mkdir()

    # Create a package.json to be detected
    package_json = project_dir / "package.json"
    package_json.write_text('{"name": "test-project", "version": "1.2.3", "description": "A test project", "license": "MIT"}', encoding='utf-8')

    # Mock Git commands to avoid dependency on actual git environment
    def mock_run(args, **kwargs):
        cmd = " ".join(args)
        if "rev-parse --show-toplevel" in cmd:
            return mocker.Mock(stdout=str(project_dir), returncode=0)
        if "rev-parse --abbrev-ref HEAD" in cmd:
            return mocker.Mock(stdout="main-branch", returncode=0)
        if "log -1 --format=%H%n%an%n%ai" in cmd:
            return mocker.Mock(stdout="abcdef1234567890\nTest Author\n2023-01-01 12:00:00 +0000", returncode=0)
        if "remote get-url origin" in cmd:
            return mocker.Mock(stdout="https://github.com/user/test-project.git", returncode=0)
        if "status --porcelain" in cmd:
            return mocker.Mock(stdout="M file.txt\nA new.txt", returncode=0)
        if "describe --tags" in cmd:
            return mocker.Mock(stdout="v1.0.0", returncode=0)
        return mocker.Mock(stdout="", returncode=0)

    mocker.patch("subprocess.run", side_effect=mock_run)

    # Change to project directory
    monkeypatch.chdir(project_dir)

    # Set up CLI arguments
    monkeypatch.setattr(sys, 'argv', ['sourcecombine.py', '--project-info'])

    with pytest.raises(SystemExit) as excinfo:
        main()

    assert excinfo.value.code == 0

    out, err = capsys.readouterr()

    # Check for expected output components
    assert "Detected Project Information:" in out
    assert "Project Information" in out
    assert "Name" in out
    assert "test-project" in out
    assert "Version" in out
    assert "1.2.3" in out
    assert "License" in out
    assert "MIT" in out

    assert "Git Information" in out
    assert "Branch" in out
    assert "main-branch" in out
    assert "Commit" in out
    assert "abcdef1234567890" in out
    assert "Remote URL" in out
    assert "https://github.com/user/test-project.git" in out
    assert "Status" in out
    assert "1 modified, 1 added" in out

def test_project_info_overrides(tmp_path, capsys, monkeypatch, mocker):
    """Test that --project-info respects CLI overrides."""
    project_dir = tmp_path / "override_project"
    project_dir.mkdir()

    # Mock subprocess.run to return "N/A" for Git
    mocker.patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "git"))

    monkeypatch.chdir(project_dir)

    # Set up CLI arguments with overrides
    monkeypatch.setattr(sys, 'argv', [
        'sourcecombine.py',
        '--project-info',
        '--project-name', 'Overridden Name',
        '--project-version', '9.9.9',
        '--project-license', 'Apache-2.0'
    ])

    with pytest.raises(SystemExit) as excinfo:
        main()

    assert excinfo.value.code == 0

    out, err = capsys.readouterr()

    assert "Overridden Name" in out
    assert "9.9.9" in out
    assert "Apache-2.0" in out
    assert "Git Information" in out
    assert "Branch" in out
    assert "N/A" in out
