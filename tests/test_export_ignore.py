import json
import pytest
from pathlib import Path
from unittest.mock import patch
import sourcecombine
import utils


def test_export_ignore_patterns_default_file(tmp_path, monkeypatch):
    """Test export_ignore_patterns creating default .sourcecombineignore."""
    monkeypatch.chdir(tmp_path)
    config = {
        'search': {'ignore_files': []},
        'filters': {
            'exclusions': {
                'filenames': ['*.log', '*.tmp'],
                'folders': ['build', 'dist/']
            }
        }
    }

    sourcecombine.export_ignore_patterns(".sourcecombineignore", config=config)

    target = tmp_path / ".sourcecombineignore"
    assert target.exists()
    content = target.read_text(encoding="utf-8")
    assert "# SourceCombine Ignore File (.sourcecombineignore)" in content
    assert "*.log" in content
    assert "*.tmp" in content
    assert "build/" in content
    assert "dist/" in content


def test_export_ignore_patterns_custom_file(tmp_path, monkeypatch):
    """Test export_ignore_patterns with a custom target file path."""
    monkeypatch.chdir(tmp_path)
    config = {
        'search': {'ignore_files': []},
        'filters': {
            'exclusions': {
                'filenames': ['*.bak'],
                'folders': ['node_modules']
            }
        }
    }

    out_file = tmp_path / "custom" / "my.ignore"
    sourcecombine.export_ignore_patterns(str(out_file), config=config)

    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "*.bak" in content
    assert "node_modules/" in content


def test_export_ignore_patterns_directory_target(tmp_path, monkeypatch):
    """Test export_ignore_patterns when target is a directory path."""
    monkeypatch.chdir(tmp_path)
    out_dir = tmp_path / "subfolder"
    out_dir.mkdir()

    config = {
        'search': {'ignore_files': []},
        'filters': {
            'exclusions': {
                'filenames': ['*.cache'],
                'folders': ['temp']
            }
        }
    }

    sourcecombine.export_ignore_patterns(str(out_dir), config=config)

    expected = out_dir / ".sourcecombineignore"
    assert expected.exists()
    content = expected.read_text(encoding="utf-8")
    assert "*.cache" in content
    assert "temp/" in content


def test_export_ignore_patterns_stdout(capsys):
    """Test export_ignore_patterns streaming plain text to stdout."""
    config = {
        'search': {'ignore_files': []},
        'filters': {
            'exclusions': {
                'filenames': ['*.swp'],
                'folders': ['out']
            }
        }
    }

    sourcecombine.export_ignore_patterns("-", config=config)

    captured = capsys.readouterr()
    assert "# SourceCombine Ignore File" in captured.out
    assert "*.swp" in captured.out
    assert "out/" in captured.out


def test_export_ignore_patterns_json_stdout(capsys):
    """Test export_ignore_patterns with json_format=True streaming to stdout."""
    config = {
        'search': {'ignore_files': []},
        'filters': {
            'exclusions': {
                'filenames': ['*.json_test'],
                'folders': ['venv']
            }
        }
    }

    sourcecombine.export_ignore_patterns("-", config=config, json_format=True)

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "patterns" in data
    assert "*.json_test" in data["patterns"]
    assert "venv/" in data["patterns"]


def test_export_ignore_patterns_json_file(tmp_path):
    """Test export_ignore_patterns with json_format=True saving to a file."""
    out_json = tmp_path / "ignore.json"
    config = {
        'search': {'ignore_files': []},
        'filters': {
            'exclusions': {
                'filenames': ['*.o'],
                'folders': ['target']
            }
        }
    }

    sourcecombine.export_ignore_patterns(str(out_json), config=config, json_format=True)

    assert out_json.exists()
    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert data["total"] == 2
    assert "*.o" in data["patterns"]
    assert "target/" in data["patterns"]


def test_export_ignore_with_existing_ignore_file(tmp_path, monkeypatch):
    """Test that existing ignore files are read and included in exported ignore patterns."""
    monkeypatch.chdir(tmp_path)

    ignore_file = tmp_path / ".sourcecombineignore"
    ignore_file.write_text("*.pyc\n__pycache__/\n", encoding="utf-8")

    config = {
        'search': {'ignore_files': [str(ignore_file)]},
        'filters': {
            'exclusions': {
                'filenames': ['*.log'],
                'folders': ['dist']
            }
        }
    }

    out_file = tmp_path / "exported.ignore"
    sourcecombine.export_ignore_patterns(str(out_file), config=config)

    content = out_file.read_text(encoding="utf-8")
    assert "*.pyc" in content
    assert "__pycache__/" in content
    assert "*.log" in content
    assert "dist/" in content


def test_cli_export_ignore_default(tmp_path, monkeypatch):
    """Test CLI execution with --export-ignore."""
    monkeypatch.chdir(tmp_path)
    export_path = tmp_path / "exported.ignore"

    with patch("sys.argv", ["sourcecombine.py", "--export-ignore", str(export_path), "-x", "*.tmp"]):
        with pytest.raises(SystemExit) as excinfo:
            sourcecombine.main()
        assert excinfo.value.code == 0

    assert export_path.exists()
    content = export_path.read_text(encoding="utf-8")
    assert "*.tmp" in content


def test_cli_export_ig_shortcut_alias(tmp_path, monkeypatch):
    """Test CLI execution using shortcut alias --export-ig."""
    monkeypatch.chdir(tmp_path)
    export_path = tmp_path / "shortcut.ignore"

    with patch("sys.argv", ["sourcecombine.py", "--export-ig", str(export_path), "-X", "build"]):
        with pytest.raises(SystemExit) as excinfo:
            sourcecombine.main()
        assert excinfo.value.code == 0

    assert export_path.exists()
    content = export_path.read_text(encoding="utf-8")
    assert "build/" in content


def test_cli_export_ignore_json(tmp_path, monkeypatch, capsys):
    """Test CLI execution with --export-ignore - --json."""
    monkeypatch.chdir(tmp_path)

    with patch("sys.argv", ["sourcecombine.py", "--export-ignore", "-", "--json", "-x", "*.out"]):
        with pytest.raises(SystemExit) as excinfo:
            sourcecombine.main()
        assert excinfo.value.code == 0

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "*.out" in data["patterns"]


def test_cli_export_ignore_conflict_files_from(tmp_path, monkeypatch):
    """Test error when --export-ignore is combined with --files-from."""
    monkeypatch.chdir(tmp_path)

    with patch("sys.argv", ["sourcecombine.py", "--export-ignore", "--files-from", "files.txt"]):
        with pytest.raises(SystemExit) as excinfo:
            sourcecombine.main()
        assert excinfo.value.code == 1


def test_export_ignore_os_error(tmp_path, monkeypatch):
    """Test OSError handling when writing ignore file fails."""
    monkeypatch.chdir(tmp_path)

    with patch("pathlib.Path.write_text", side_effect=OSError("Permission denied")):
        with pytest.raises(SystemExit) as excinfo:
            sourcecombine.export_ignore_patterns(str(tmp_path / "fail.ignore"))
        assert excinfo.value.code == 1
