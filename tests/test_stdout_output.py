import sys
import logging
import pytest
from pathlib import Path
from contextlib import redirect_stdout
import io
import sourcecombine
from sourcecombine import find_and_combine_files, InvalidConfigError

def test_stdout_output(tmp_path, capsys):
    """Test that output is written to stdout when -o - is used."""

    # Create some dummy files
    f1 = tmp_path / "file1.txt"
    f1.write_text("Content of file 1", encoding="utf-8")
    f2 = tmp_path / "file2.txt"
    f2.write_text("Content of file 2", encoding="utf-8")

    config = {
        'search': {'root_folders': [str(tmp_path)]},
        'filters': {'min_size_bytes': 0},
        'output': {'file': 'default.txt'}
    }

    # Run the function
    find_and_combine_files(config, output_path='-')

    captured = capsys.readouterr()
    stdout_content = captured.out

    assert "Content of file 1" in stdout_content
    assert "Content of file 2" in stdout_content
    assert "--- file1.txt ---" in stdout_content # Header check

    # Verify stdout is not closed by printing something
    print("Post-execution check")
    captured_post = capsys.readouterr()
    assert "Post-execution check" in captured_post.out

def test_stdout_output_pairing_error(tmp_path):
    """Test that pairing mode raises an error with -o -."""
    config = {
        'search': {'root_folders': [str(tmp_path)]},
        'pairing': {'enabled': True},
        'output': {'folder': 'output_folder'}
    }

    with pytest.raises(InvalidConfigError, match="Writing to the terminal is not available in pairing mode"):
        find_and_combine_files(config, output_path='-')

def test_stdout_output_dry_run(tmp_path, capsys):
    """Test that dry-run does NOT write to stdout even if -o - is specified."""
    f1 = tmp_path / "file1.txt"
    f1.write_text("Content of file 1", encoding="utf-8")

    config = {
        'search': {'root_folders': [str(tmp_path)]},
    }

    find_and_combine_files(config, output_path='-', dry_run=True)

    captured = capsys.readouterr()
    assert "Content of file 1" not in captured.out

def test_stdout_output_clipboard_priority(tmp_path, capsys):
    """Test that clipboard mode takes precedence over stdout."""
    # Mock pyperclip to avoid errors and verify interaction
    import sys
    from unittest.mock import MagicMock

    # Mocking pyperclip module
    mock_pyperclip = MagicMock()
    with pytest.MonkeyPatch.context() as m:
        m.setitem(sys.modules, 'pyperclip', mock_pyperclip)

        f1 = tmp_path / "file1.txt"
        f1.write_text("Content of file 1", encoding="utf-8")

        config = {
            'search': {'root_folders': [str(tmp_path)]},
        }

        # Pass clipboard=True AND output_path='-'
        find_and_combine_files(config, output_path='-', clipboard=True)

        captured = capsys.readouterr()
        # Should not be in stdout
        assert "Content of file 1" not in captured.out

        # Verify copy was called
        mock_pyperclip.copy.assert_called()
        args, _ = mock_pyperclip.copy.call_args
        assert "Content of file 1" in args[0]
