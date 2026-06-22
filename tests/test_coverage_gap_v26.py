import os
import sys
from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch
import sourcecombine
import utils

def test_markdown_summary_line_counts_only():
    """Test Markdown summary when tokens are 0 but lines are present."""
    # top_files: (tokens, size, path, status, lines, language)
    stats = {
        'total_files': 2,
        'total_size_bytes': 2000,
        'total_tokens': 0,
        'total_lines': 100,
        'top_files': [
            (0, 1000, "src/file1.py", "success", 60, "python"),
            (0, 1000, "src/file2.py", "success", 40, "python")
        ],
        'files_by_language': {'python': 2},
        'lines_by_language': {'python': 100},
        'size_by_language': {'python': 2000},
        'tokens_by_language': {'python': 0}
    }

    output = sourcecombine._generate_project_overview(stats, output_format='markdown')

    # Check for line count columns in Markdown for files
    assert "| Lines |" in output
    assert "| 60 |" in output
    assert "| 40 |" in output

    # Check for Largest Folders (by lines)
    assert "## Largest Folders (by lines)" in output
    assert "| Folder | Lines | Size | Files | % |" in output
    assert "| `src` | 100 |" in output

    # Check for Language Breakdown
    assert "## Languages" in output
    assert "| Language | Count | Lines | % Files | % Lines |" in output
    assert "| `python` | 2 | 100 |" in output

def test_markdown_summary_with_tokens():
    """Test Markdown summary with tokens to cover remaining lines in _generate_project_overview."""
    stats = {
        'total_files': 1,
        'total_size_bytes': 1000,
        'total_tokens': 500,
        'total_lines': 50,
        'top_files': [
            (500, 1000, "file.py", "success", 50, "python")
        ],
        'files_by_language': {'python': 1},
        'lines_by_language': {'python': 50},
        'size_by_language': {'python': 1000},
        'tokens_by_language': {'python': 500}
    }
    output = sourcecombine._generate_project_overview(stats, output_format='markdown')
    assert "| Tokens |" in output
    assert "| 500 |" in output

def test_cli_project_info_with_config_target(tmp_path, monkeypatch, mocker):
    """Test --project-info where first target is a config file (lines 4338-4342)."""
    project_dir = tmp_path / "proj"
    project_dir.mkdir()
    config_file = tmp_path / "myconfig.yml"
    config_file.write_text("search:\n  root_folders: ['.']", encoding='utf-8')

    monkeypatch.chdir(project_dir)
    monkeypatch.setattr(sys, 'argv', ['sourcecombine.py', '--project-info', str(config_file), '.'])

    # Mock necessary parts to avoid full execution
    mocker.patch("sourcecombine._populate_project_stats")
    mocker.patch("sourcecombine._get_git_info", return_value={})
    mocker.patch("sourcecombine._generate_project_overview", return_value="Summary")
    mocker.patch("sourcecombine.print")

    with pytest.raises(SystemExit) as exc:
        sourcecombine.main()
    assert exc.value.code == 0

def test_cli_project_info_without_config_target(tmp_path, monkeypatch, mocker):
    """Test --project-info where first target is NOT a config file (line 4344)."""
    project_dir = tmp_path / "proj"
    project_dir.mkdir()

    monkeypatch.chdir(project_dir)
    monkeypatch.setattr(sys, 'argv', ['sourcecombine.py', '--project-info', '.'])

    # Mock necessary parts to avoid full execution
    mocker.patch("sourcecombine._populate_project_stats")
    mocker.patch("sourcecombine._get_git_info", return_value={})
    mocker.patch("sourcecombine._generate_project_overview", return_value="Summary")
    mocker.patch("sourcecombine.print")

    with pytest.raises(SystemExit) as exc:
        sourcecombine.main()
    assert exc.value.code == 0

def test_cli_project_info_default_config(tmp_path, monkeypatch, mocker):
    """Test --project-info fallback to default config filenames (lines 4346-4350)."""
    project_dir = tmp_path / "proj_default_cfg"
    project_dir.mkdir()
    (project_dir / "sourcecombine.yml").write_text("search:\n  root_folders: ['.']", encoding='utf-8')

    monkeypatch.chdir(project_dir)
    monkeypatch.setattr(sys, 'argv', ['sourcecombine.py', '--project-info'])

    mocker.patch("sourcecombine._populate_project_stats")
    mocker.patch("sourcecombine._get_git_info", return_value={})
    mocker.patch("sourcecombine._generate_project_overview", return_value="Summary")
    mocker.patch("sourcecombine.print")

    with pytest.raises(SystemExit) as exc:
        sourcecombine.main()
    assert exc.value.code == 0

def test_cli_project_info_invalid_config(tmp_path, monkeypatch, mocker):
    """Test --project-info with invalid config file (lines 4357-4358)."""
    project_dir = tmp_path / "proj_invalid_cfg"
    project_dir.mkdir()

    monkeypatch.chdir(project_dir)
    monkeypatch.setattr(sys, 'argv', ['sourcecombine.py', '--project-info', '--config', 'nonexistent.yml'])

    with pytest.raises(SystemExit) as exc:
        sourcecombine.main()
    assert exc.value.code == 1

def test_get_project_identity_exception_handling(tmp_path):
    """Test exception handling in get_project_identity for various manifests."""
    # List of files that trigger try-except blocks
    manifests = [
        "test.csproj", "settings.gradle", "project.clj", "test.podspec",
        "pyproject.toml", "Cargo.toml", "pom.xml", "go.mod",
        "test.gemspec", "mix.exs", "Package.swift", "README.md", "LICENSE"
    ]
    for m in manifests:
        (tmp_path / m).write_text("dummy", encoding='utf-8')

    real_read_text = Path.read_text
    def mock_read_text(self, *args, **kwargs):
        if any(self.name.endswith(ext) for ext in [".csproj", ".podspec", ".gemspec"]) or self.name in manifests:
            raise Exception("Forced error")
        return real_read_text(self, *args, **kwargs)

    with patch.object(Path, "read_text", mock_read_text):
        identity = utils.get_project_identity(tmp_path)
        # Should survive all exceptions and fallback to folder name
        assert identity["project_name"] == tmp_path.name

def test_gradle_kts_fallback_coverage(tmp_path):
    """Exercise line 1471: fallback to settings.gradle.kts."""
    (tmp_path / "settings.gradle.kts").write_text("rootProject.name = 'kts-project'", encoding='utf-8')
    (tmp_path / "build.gradle.kts").write_text("version = '2.0.0'", encoding='utf-8')

    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "kts-project"
    assert identity["project_version"] == "2.0.0"

def test_get_project_identity_global_exception(tmp_path):
    """Exercise the very last catch-all Exception in get_project_identity."""
    with patch("utils.Path.is_dir", side_effect=Exception("Fatal")):
        identity = utils.get_project_identity(tmp_path)
        assert identity["project_name"] == tmp_path.name

def test_get_project_identity_license_exception(tmp_path):
    """Exercise exception in license file reading (line 1764)."""
    (tmp_path / "LICENSE").write_text("MIT", encoding='utf-8')

    real_read_text = Path.read_text
    def mock_read_text(self, *args, **kwargs):
        if self.name == "LICENSE":
            raise Exception("License read error")
        return real_read_text(self, *args, **kwargs)

    with patch.object(Path, "read_text", mock_read_text):
        identity = utils.get_project_identity(tmp_path)
        assert not identity.get("project_license")
