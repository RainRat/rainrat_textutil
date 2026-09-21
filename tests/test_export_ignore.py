import copy
import json
import os
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

import sourcecombine
import utils


def test_export_ignore_patterns_default_file(tmp_path, monkeypatch):
    """Test export_ignore_patterns function writing to default .sourcecombineignore."""
    monkeypatch.chdir(tmp_path)
    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    config['filters']['exclusions']['filenames'] = ['*.tmp', '*.log']
    config['filters']['exclusions']['folders'] = ['build', 'dist']

    count = sourcecombine.export_ignore_patterns(None, config=config)

    assert count == 4
    out_file = tmp_path / ".sourcecombineignore"
    assert out_file.exists()
    content = out_file.read_text(encoding='utf-8')
    assert "# Exported SourceCombine Ignore Patterns" in content
    assert "*.tmp" in content
    assert "*.log" in content
    assert "build" in content
    assert "dist" in content


def test_export_ignore_patterns_custom_file(tmp_path, monkeypatch):
    """Test export_ignore_patterns writing to a custom file path."""
    monkeypatch.chdir(tmp_path)
    custom_path = tmp_path / "custom" / "ignore_rules.txt"
    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    config['filters']['exclusions']['filenames'] = ['*.cache']
    config['filters']['exclusions']['folders'] = []

    count = sourcecombine.export_ignore_patterns(str(custom_path), config=config)

    assert count == 1
    assert custom_path.exists()
    content = custom_path.read_text(encoding='utf-8')
    assert "*.cache" in content


def test_export_ignore_patterns_stdout(capsys, tmp_path, monkeypatch):
    """Test export_ignore_patterns outputting to stdout when path is '-'."""
    monkeypatch.chdir(tmp_path)
    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    config['filters']['exclusions']['filenames'] = ['*.bak']
    config['filters']['exclusions']['folders'] = []

    count = sourcecombine.export_ignore_patterns('-', config=config)

    assert count == 1
    captured = capsys.readouterr()
    assert "# Exported SourceCombine Ignore Patterns" in captured.out
    assert "*.bak" in captured.out


def test_export_ignore_patterns_json(capsys, tmp_path, monkeypatch):
    """Test export_ignore_patterns outputting JSON format."""
    monkeypatch.chdir(tmp_path)
    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    config['filters']['exclusions']['filenames'] = ['*.pyc']
    config['filters']['exclusions']['folders'] = []

    count = sourcecombine.export_ignore_patterns(".sourcecombineignore", config=config, json_format=True)

    assert count == 1
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["output_path"] == ".sourcecombineignore"
    assert data["total"] == 1
    assert "Excluded Filenames (Config)" in data["ignore_patterns"]
    assert "*.pyc" in data["ignore_patterns"]["Excluded Filenames (Config)"]


def test_cli_export_ignore(tmp_path, monkeypatch):
    """Test CLI execution with --export-ignore."""
    monkeypatch.chdir(tmp_path)
    target_path = tmp_path / "exported.ignore"

    with patch("sys.argv", ["sourcecombine.py", "--export-ignore", str(target_path), "--exclude-file", "*.spec"]):
        with pytest.raises(SystemExit) as excinfo:
            sourcecombine.main()
        assert excinfo.value.code == 0

    assert target_path.exists()
    content = target_path.read_text(encoding='utf-8')
    assert "*.spec" in content


def test_cli_export_ig_shortcut_alias(tmp_path, monkeypatch):
    """Test CLI execution with --export-ig shortcut alias."""
    monkeypatch.chdir(tmp_path)
    target_path = tmp_path / "exported_alias.ignore"

    with patch("sys.argv", ["sourcecombine.py", "--export-ig", str(target_path), "--exclude-folder", "coverage_dir"]):
        with pytest.raises(SystemExit) as excinfo:
            sourcecombine.main()
        assert excinfo.value.code == 0

    assert target_path.exists()
    content = target_path.read_text(encoding='utf-8')
    assert "coverage_dir" in content


def test_cli_export_ignore_json(capsys, tmp_path, monkeypatch):
    """Test CLI execution with --export-ignore and --json."""
    monkeypatch.chdir(tmp_path)

    with patch("sys.argv", ["sourcecombine.py", "--export-ignore", "-", "--json", "--exclude-file", "*.log"]):
        with pytest.raises(SystemExit) as excinfo:
            sourcecombine.main()
        assert excinfo.value.code == 0

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["output_path"] == "-"
    assert data["total"] >= 1


def test_export_ignore_error_handling(tmp_path, monkeypatch):
    """Test error handling when writing to an invalid/unwritable path."""
    monkeypatch.chdir(tmp_path)
    invalid_path = tmp_path / "read_only_dir" / "file.ignore"
    # Create directory and make it read-only or pass directory as target
    dir_target = tmp_path / "dir_target"
    dir_target.mkdir()

    with pytest.raises(utils.InvalidConfigError, match="Failed to export ignore patterns"):
        sourcecombine.export_ignore_patterns(str(dir_target))
