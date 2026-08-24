import os
import json
from pathlib import Path
import pytest
import utils
from sourcecombine import explain_paths, main
from unittest.mock import patch

def test_explain_paths_nonexistent(tmp_path, capsys):
    """Test explaining a nonexistent file."""
    nonexistent = tmp_path / "does_not_exist.txt"
    config = utils.DEFAULT_CONFIG.copy()

    # 1. Text format
    explain_paths([str(nonexistent)], config=config, json_format=False)
    captured = capsys.readouterr()
    assert "PATH MATCH ANALYSIS & EXPLANATION" in captured.out
    assert "EXCLUDED" in captured.out
    assert "The path does not exist on disk." in captured.out
    assert "N/A (file does not exist on disk)" in captured.out

    # 2. JSON format
    explain_paths([str(nonexistent)], config=config, json_format=True)
    captured = capsys.readouterr()
    results = json.loads(captured.out)
    assert len(results) == 1
    assert results[0]["exists"] is False
    assert results[0]["included"] is False
    assert results[0]["reason_code"] == "not_file"

def test_explain_paths_directory(tmp_path, capsys):
    """Test explaining a directory path."""
    subfolder = tmp_path / "subfolder"
    subfolder.mkdir()
    config = utils.DEFAULT_CONFIG.copy()

    # 1. Text format
    explain_paths([str(subfolder)], config=config, json_format=False)
    captured = capsys.readouterr()
    assert "PATH MATCH ANALYSIS & EXPLANATION" in captured.out
    assert "EXCLUDED" in captured.out
    assert "The path is a directory." in captured.out
    assert "N/A (path is a directory)" in captured.out

    # 2. JSON format
    explain_paths([str(subfolder)], config=config, json_format=True)
    captured = capsys.readouterr()
    results = json.loads(captured.out)
    assert len(results) == 1
    assert results[0]["exists"] is True
    assert results[0]["included"] is False
    assert results[0]["reason_code"] == "directory"

def test_explain_paths_oserror(tmp_path, capsys):
    """Test explaining a path that raises an OSError on stat/is_file."""
    bad_path = tmp_path / "bad_perm"
    config = utils.DEFAULT_CONFIG.copy()

    with patch.object(Path, "is_file", side_effect=OSError("Permission denied")):
        explain_paths([str(bad_path)], config=config, json_format=True)
        captured = capsys.readouterr()
        results = json.loads(captured.out)
        assert len(results) == 1
        assert results[0]["exists"] is False
        assert results[0]["reason_code"] == "not_file"


def test_explain_paths_included(tmp_path, capsys):
    """Test explaining a valid file that should be included."""
    valid_file = tmp_path / "hello.py"
    valid_file.write_text("print('hello world')")

    config = utils.DEFAULT_CONFIG.copy()
    config['search'] = {
        'root_folders': [str(tmp_path)],
        'effective_allowed_extensions': ('.py',),
        'effective_exclude_extensions': ()
    }

    explain_paths([str(valid_file)], config=config, json_format=False)
    captured = capsys.readouterr()
    assert "INCLUDED" in captured.out
    assert "The file passed all configuration filters and would be combined." in captured.out
    assert "Language: python" in captured.out
    assert "Size:" in captured.out

    explain_paths([str(valid_file)], config=config, json_format=True)
    captured = capsys.readouterr()
    results = json.loads(captured.out)
    assert len(results) == 1
    assert results[0]["exists"] is True
    assert results[0]["included"] is True
    assert results[0]["metadata"]["language"] == "python"

def test_explain_paths_relative_root_display(tmp_path, capsys, monkeypatch):
    """Test that 'Relative to root:' is omitted when path equals relative_path, and included when they differ."""
    monkeypatch.chdir(tmp_path)
    file_path = tmp_path / "sample.py"
    file_path.write_text("a = 1")

    config = utils.DEFAULT_CONFIG.copy()
    config['search'] = {'root_folders': ["."]}

    # 1. When path equals relative_path ("sample.py"), "Relative to root:" should be omitted.
    explain_paths(["sample.py"], config=config, json_format=False)
    captured = capsys.readouterr()
    assert "Path: sample.py" in captured.out
    assert "Relative to root:" not in captured.out

    # 2. When path differs from relative_path ("./sample.py"), "Relative to root:" should be shown.
    explain_paths(["./sample.py"], config=config, json_format=False)
    captured = capsys.readouterr()
    assert "Path: ./sample.py" in captured.out
    assert "Relative to root: sample.py" in captured.out

def test_explain_paths_excluded_by_extension(tmp_path, capsys):
    """Test explaining a file excluded by extension settings."""
    txt_file = tmp_path / "notes.txt"
    txt_file.write_text("some notes")

    config = utils.DEFAULT_CONFIG.copy()
    config['search'] = {
        'root_folders': [str(tmp_path)],
        'effective_allowed_extensions': ('.py',),
        'effective_exclude_extensions': ()
    }

    explain_paths([str(txt_file)], config=config, json_format=False)
    captured = capsys.readouterr()
    assert "EXCLUDED" in captured.out
    assert "The file extension is not allowed" in captured.out

def test_explain_paths_excluded_by_glob(tmp_path, capsys):
    """Test explaining a file excluded by folder or filename exclusion glob."""
    temp_file = tmp_path / "temp.log"
    temp_file.write_text("debug logs")

    config = utils.DEFAULT_CONFIG.copy()
    config['search'] = {
        'root_folders': [str(tmp_path)],
    }
    config['filters'] = {
        'exclusions': {
            'filenames': ['*.log'],
            'folders': []
        }
    }

    explain_paths([str(temp_file)], config=config, json_format=False)
    captured = capsys.readouterr()
    assert "EXCLUDED" in captured.out
    assert "Excluded by filename/folder glob patterns" in captured.out

def test_explain_paths_too_large(tmp_path, capsys):
    """Test explaining a file that exceeds max size limit."""
    large_file = tmp_path / "large.py"
    large_file.write_text("x" * 1000)

    config = utils.DEFAULT_CONFIG.copy()
    config['search'] = {
        'root_folders': [str(tmp_path)],
    }
    config['filters'] = {
        'max_size_bytes': 10
    }

    explain_paths([str(large_file)], config=config, json_format=True)
    captured = capsys.readouterr()
    results = json.loads(captured.out)
    assert results[0]["included"] is False
    assert results[0]["reason_code"] == "too_large"

def test_explain_paths_binary(tmp_path, capsys):
    """Test explaining a binary file."""
    bin_file = tmp_path / "binary.bin"
    bin_file.write_bytes(b"\x00\x01\x02\x03\xff")

    config = utils.DEFAULT_CONFIG.copy()
    config['search'] = {
        'root_folders': [str(tmp_path)],
    }
    config['filters'] = {
        'skip_binary': True
    }

    explain_paths([str(bin_file)], config=config, json_format=True)
    captured = capsys.readouterr()
    results = json.loads(captured.out)
    assert results[0]["included"] is False
    assert results[0]["reason_code"] == "binary"

def test_explain_cli_integration(tmp_path, capsys):
    """Test the CLI integration of --explain via main() mock."""
    test_file = tmp_path / "test.py"
    test_file.write_text("print('test')")

    test_argv = ["sourcecombine.py", "--explain", str(test_file)]

    with patch("sys.argv", test_argv), pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "PATH MATCH ANALYSIS & EXPLANATION" in captured.out
    assert "test.py" in captured.out

def test_explain_cli_json_integration(tmp_path, capsys):
    """Test the CLI integration of --explain with --json via main() mock."""
    test_file = tmp_path / "test.py"
    test_file.write_text("print('test')")

    test_argv = ["sourcecombine.py", "--explain", str(test_file), "--json"]

    with patch("sys.argv", test_argv), pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    results = json.loads(captured.out)
    assert len(results) == 1
    assert results[0]["path"] == str(test_file)
