import pytest
import logging
from unittest.mock import patch, MagicMock
import sys
from io import StringIO
import sourcecombine
from sourcecombine import main
import yaml

def test_dry_run_output(capsys, caplog, tmp_path):
    # This test verifies that logging actually works as expected in pytest environment
    # using caplog fixture.

    (tmp_path / "test_file.txt").write_text("content")

    # Run with --dry-run
    with patch.object(sys, 'argv', ["sourcecombine.py", str(tmp_path), "--dry-run"]):
        try:
            main()
        except SystemExit:
            pass

    # capsys catches print() to stdout/stderr
    captured = capsys.readouterr()
    # caplog catches logging

    # We expect the summary to be in stderr
    assert "DRY RUN COMPLETE" in captured.err

    # We expect the filename to be logged at INFO level
    # Since pytest intercepts logging, we check caplog
    assert "test_file.txt" in caplog.text

def test_list_files_proposal(capsys, tmp_path):
    # This test verifies the new --list-files feature

    (tmp_path / "test_file.txt").write_text("content")
    (tmp_path / "src").mkdir()
    (tmp_path / "src/other.py").write_text("print('hello')")

    # Run with --list-files
    with patch.object(sys, 'argv', ["sourcecombine.py", str(tmp_path), "--list-files"]):
        try:
            main()
        except SystemExit:
            pass

    captured = capsys.readouterr()

    # stdout should contain the filenames
    assert "test_file.txt" in captured.out
    assert "src/other.py" in captured.out

    # stderr should contain the summary
    assert "FILE LISTING COMPLETE" in captured.err

    # stdout should NOT contain log info
    assert "SourceCombine starting" not in captured.out
    assert "Output: Listing files only" not in captured.out

def test_list_files_excludes_size(capsys, tmp_path):
    # Create a config that excludes large files
    (tmp_path / "large.txt").write_text("A" * 1000)
    (tmp_path / "small.txt").write_text("A")

    config = {
        'search': {'root_folders': [str(tmp_path)]},
        'filters': {'max_size_bytes': 10},
        'output': {'max_size_placeholder': '[SKIPPED]'}
    }

    config_file = tmp_path / "config.yml"
    with open(config_file, 'w') as f:
        yaml.dump(config, f)

    # Run with --list-files.
    # Current implementation: It SHOULD include "large.txt" because a placeholder is written (so it's "processed").

    with patch.object(sys, 'argv', ["sourcecombine.py", str(config_file), "--list-files"]):
        try:
            main()
        except SystemExit:
            pass

    captured = capsys.readouterr()
    assert "large.txt" in captured.out
    assert "small.txt" in captured.out

def test_list_files_with_pairing(capsys, tmp_path):
    """Verify --list-files works correctly when pairing is enabled."""

    # Setup files for pairing
    (tmp_path / "src").mkdir()
    (tmp_path / "src/foo.c").write_text("c code")
    (tmp_path / "src/foo.h").write_text("h code")
    (tmp_path / "src/bar.c").write_text("c code only")

    # Create config with pairing enabled
    config = {
        'search': {'root_folders': [str(tmp_path)]},
        'pairing': {
            'enabled': True,
            'source_extensions': ['.c'],
            'header_extensions': ['.h'],
            'include_mismatched': True
        }
    }

    config_file = tmp_path / "config.yml"
    with open(config_file, 'w') as f:
        yaml.dump(config, f)

    # Run with --list-files
    with patch.object(sys, 'argv', ["sourcecombine.py", str(config_file), "--list-files"]):
        try:
            main()
        except SystemExit:
            pass

    captured = capsys.readouterr()

    # With pairing enabled, --list-files should list the *source* files that make up the pairs
    # The current implementation in sourcecombine.py:822 (in find_and_combine_files)
    # calls _pair_files and then collects unique paths.

    assert "src/foo.c" in captured.out
    assert "src/foo.h" in captured.out
    assert "src/bar.c" in captured.out

    # Verify summary title
    assert "FILE LISTING COMPLETE" in captured.err

def test_list_files_with_pairing_mismatched_disabled(capsys, tmp_path):
    """Verify --list-files respects include_mismatched=False."""

    (tmp_path / "src").mkdir()
    (tmp_path / "src/foo.c").write_text("c code")
    (tmp_path / "src/foo.h").write_text("h code")
    (tmp_path / "src/bar.c").write_text("c code only")

    config = {
        'search': {'root_folders': [str(tmp_path)]},
        'pairing': {
            'enabled': True,
            'source_extensions': ['.c'],
            'header_extensions': ['.h'],
            'include_mismatched': False
        }
    }

    config_file = tmp_path / "config.yml"
    with open(config_file, 'w') as f:
        yaml.dump(config, f)

    with patch.object(sys, 'argv', ["sourcecombine.py", str(config_file), "--list-files"]):
        try:
            main()
        except SystemExit:
            pass

    captured = capsys.readouterr()

    assert "src/foo.c" in captured.out
    assert "src/foo.h" in captured.out
    assert "src/bar.c" not in captured.out


def test_list_files_tree_estimate_tokens(capsys, tmp_path):
    """Verify --list-files with --tree and --estimate-tokens."""
    (tmp_path / "test.py").write_text("print('hello')", encoding="utf-8")

    with patch.object(sys, "argv", ["sourcecombine.py", str(tmp_path), "--list-files", "--tree", "--estimate-tokens"]):
        try:
            main()
        except SystemExit:
            pass

    captured = capsys.readouterr()
    # Tree should contain tokens
    assert "test.py" in captured.out
    assert "tokens" in captured.out
    # When estimate_tokens is set, it takes precedence in summary title
    assert "TOKEN ESTIMATION COMPLETE" in captured.err

def test_list_files_with_token_estimation_approx(tmp_path, capsys):
    """Cover sourcecombine.py line 1213: stats['token_count_is_approx'] = True in list_files mode."""
    import sourcecombine
    from unittest.mock import patch
    root = tmp_path / "root"
    root.mkdir()
    (root / "file1.txt").write_text("content", encoding="utf-8")

    config = {
        "search": {"root_folders": [str(root)]},
        "output": {"file": str(tmp_path / "out.txt")}
    }

    # Mock estimate_tokens to return is_approx=True
    with patch("utils.estimate_tokens", return_value=(10, True)):
        stats = sourcecombine.find_and_combine_files(
            config,
            output_path=str(tmp_path / "out.txt"),
            list_files=True,
            estimate_tokens=True,
            tree_view=False
        )

    assert stats['token_count_is_approx'] is True
