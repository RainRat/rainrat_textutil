import sys
import os
import logging
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import io
import yaml

# Adjust sys.path to include the project root
sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

from sourcecombine import main, utils

@pytest.fixture(autouse=True)
def reset_logging():
    """Reset logging before and after each test."""
    root = logging.getLogger()
    for h in root.handlers[:]:
        root.removeHandler(h)
    root.setLevel(logging.NOTSET)
    yield
    for h in root.handlers[:]:
        root.removeHandler(h)

@pytest.fixture
def mock_argv():
    """Context manager to mock sys.argv."""
    def _mock_argv(args):
        return patch.object(sys, 'argv', ['sourcecombine.py'] + args)
    return _mock_argv

@pytest.fixture
def temp_cwd(tmp_path):
    """Context manager to change current working directory."""
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(original_cwd)

def test_files_from_file(temp_cwd, mock_argv):
    """Test reading file list from a text file."""
    # Create target files
    f1 = temp_cwd / "file1.txt"
    f1.write_text("content1", encoding="utf-8")
    f2 = temp_cwd / "file2.py"
    f2.write_text("content2", encoding="utf-8")

    # Create file list
    list_file = temp_cwd / "mylist.txt"
    list_file.write_text(f"{f1}\n{f2}\n", encoding="utf-8")

    with patch('sourcecombine.find_and_combine_files') as mock_combine:
        mock_combine.return_value = {}
        with mock_argv(['--files-from', str(list_file)]):
            main()

        assert mock_combine.called
        explicit_files = mock_combine.call_args.kwargs.get('explicit_files')
        assert explicit_files is not None
        assert f1.resolve() in explicit_files
        assert f2.resolve() in explicit_files
        assert len(explicit_files) == 2

def test_files_from_stdin(temp_cwd, mock_argv):
    """Test reading file list from stdin."""
    f1 = temp_cwd / "file1.txt"
    f1.write_text("content1", encoding="utf-8")

    stdin_content = f"{f1}\n"

    with patch('sourcecombine.find_and_combine_files') as mock_combine:
        mock_combine.return_value = {}
        with patch('sys.stdin', io.StringIO(stdin_content)):
            with mock_argv(['--files-from', '-']):
                main()

        assert mock_combine.called
        explicit_files = mock_combine.call_args.kwargs.get('explicit_files')
        assert f1.resolve() in explicit_files

def test_files_from_and_init_conflict(temp_cwd, mock_argv, caplog):
    """Test conflict between --files-from and --init."""
    caplog.set_level(logging.ERROR)
    with mock_argv(['--files-from', 'list.txt', '--init']):
        with pytest.raises(SystemExit) as excinfo:
            main()

    assert excinfo.value.code == 1
    assert "You cannot use --init and --files-from at the same time" in caplog.text

def test_files_from_missing_file(temp_cwd, mock_argv, caplog):
    """Test error when --files-from points to a missing file."""
    caplog.set_level(logging.ERROR)
    with mock_argv(['--files-from', 'nonexistent.txt']):
        with pytest.raises(SystemExit) as excinfo:
            main()

    assert excinfo.value.code == 1
    assert "Failed to read file list from 'nonexistent.txt'" in caplog.text

def test_files_from_no_config_fallback(temp_cwd, mock_argv, caplog):
    """Test that --files-from falls back to defaults when no config is found."""
    f1 = temp_cwd / "file1.txt"
    f1.write_text("content1", encoding="utf-8")
    list_file = temp_cwd / "list.txt"
    list_file.write_text(f"{f1}\n", encoding="utf-8")

    caplog.set_level(logging.INFO)

    with patch('sourcecombine.find_and_combine_files') as mock_combine:
        mock_combine.return_value = {}
        with mock_argv(['--files-from', str(list_file)]):
            main()

    assert "No configuration found. Using default settings with --files-from" in caplog.text
    assert mock_combine.called
    config_passed = mock_combine.call_args.args[0]
    # Verify it has search section
    assert 'search' in config_passed

def test_files_from_outside_root(temp_cwd, mock_argv, capsys):
    """Test handling of files outside root path (CWD) in tree view and TOC."""
    # Create a file outside temp_cwd
    outside_dir = temp_cwd.parent / "outside_dir"
    outside_dir.mkdir(exist_ok=True)
    f_outside = outside_dir / "outside.txt"
    f_outside.write_text("outside content", encoding="utf-8")

    list_file = temp_cwd / "list.txt"
    list_file.write_text(f"{f_outside}\n", encoding="utf-8")

    # Test Tree View
    with mock_argv(['--files-from', str(list_file), '--tree']):
        main()

    captured = capsys.readouterr()
    # It should fallback to absolute path structure.
    # Since it's a tree, we check for components.
    assert "outside.txt" in captured.out
    assert "outside_dir" in captured.out

    # Test TOC (Table of Contents)
    with mock_argv(['--files-from', str(list_file), '--toc', '-o', '-']):
        main()

    captured = capsys.readouterr()
    # TOC should also fallback to absolute path if relative_to fails
    # In TOC it's just str(path)
    assert str(f_outside.resolve()) in captured.out

    # Test normal processing (triggers FileProcessor)
    with mock_argv(['--files-from', str(list_file), '-o', '-']):
        main()

    captured = capsys.readouterr()
    assert "outside content" in captured.out
