import os
import shutil
import pytest
from pathlib import Path
from sourcecombine import find_and_combine_files

def test_mirror_mode_basic(tmp_path):
    # Setup input directory
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    (input_dir / "file1.txt").write_text("content1")
    (input_dir / "subdir").mkdir()
    (input_dir / "subdir" / "file2.txt").write_text("content2")

    # Setup output directory
    output_dir = tmp_path / "output"

    config = {
        'search': {
            'root_folders': [str(input_dir)],
            'recursive': True,
        },
        'output': {
            'mirror': True,
        },
        'filters': {},
        'processing': {},
    }

    find_and_combine_files(config, str(output_dir))

    # Verify results
    assert (output_dir / "file1.txt").exists()
    assert (output_dir / "file1.txt").read_text() == "content1"
    assert (output_dir / "subdir" / "file2.txt").exists()
    assert (output_dir / "subdir" / "file2.txt").read_text() == "content2"

def test_mirror_mode_with_processing(tmp_path):
    # Setup input directory
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    (input_dir / "file1.txt").write_text("   content   with   many   spaces   ")

    # Setup output directory
    output_dir = tmp_path / "output"

    config = {
        'search': {
            'root_folders': [str(input_dir)],
            'recursive': True,
        },
        'output': {
            'mirror': True,
        },
        'filters': {},
        'processing': {
            'compact_whitespace': True,
        },
    }

    find_and_combine_files(config, str(output_dir))

    # Verify results - should be compacted
    assert (output_dir / "file1.txt").exists()
    # compact_whitespace: "   content   with   many   spaces   " -> "  content  with  many  spaces" (max 2 spaces)
    content = (output_dir / "file1.txt").read_text()
    assert "   " not in content
    assert "  " in content # Should have exactly 2 spaces

def test_mirror_mode_with_exclusion(tmp_path):
    # Setup input directory
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    (input_dir / "file1.txt").write_text("content1")
    (input_dir / "skip.me").write_text("skip")

    # Setup output directory
    output_dir = tmp_path / "output"

    config = {
        'search': {
            'root_folders': [str(input_dir)],
            'recursive': True,
        },
        'output': {
            'mirror': True,
        },
        'filters': {
            'exclusions': {
                'filenames': ['*.me'],
            }
        },
        'processing': {},
    }

    find_and_combine_files(config, str(output_dir))

    # Verify results
    assert (output_dir / "file1.txt").exists()
    assert not (output_dir / "skip.me").exists()

def test_mirror_mode_invalid_config(tmp_path):
    config = {
        'output': {
            'mirror': True,
        },
        'pairing': {
            'enabled': True,
        }
    }
    # find_and_combine_files should raise InvalidConfigError
    import utils
    with pytest.raises(utils.InvalidConfigError):
        find_and_combine_files(config, str(tmp_path / "output"))

def test_mirror_mode_cli_output(tmp_path, capsys):
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    (input_dir / "file1.txt").write_text("content1")
    output_dir = tmp_path / "output"

    # We need to mock sys.argv or just call main?
    # Calling main is better for integration test.
    import sys
    import sourcecombine

    test_args = ["sourcecombine.py", str(input_dir), "--output", str(output_dir), "--mirror"]
    from unittest.mock import patch
    with patch.object(sys, 'argv', test_args):
        # We need to catch SystemExit from main if any
        try:
            sourcecombine.main()
        except SystemExit as e:
            assert e.code == 0

    captured = capsys.readouterr()
    # Check if "Mirror" or "Mirrored" appears in stderr summary
    assert "MIRROR" in captured.err or "Mirrored" in captured.err
    assert "to" in captured.err
    # Path might be truncated in summary, so we check for the filename part at least
    assert output_dir.name in captured.err
