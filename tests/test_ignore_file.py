import os
from pathlib import Path
import pytest
import utils
from sourcecombine import find_and_combine_files

def test_ignore_file_integration(tmp_path):
    """Test that .sourcecombineignore correctly filters files."""

    # Setup project structure
    project_root = tmp_path / "my_project"
    project_root.mkdir()

    (project_root / "keep.py").write_text("print('keep')")
    (project_root / "skip.log").write_text("log data")
    (project_root / "skip_this.py").write_text("print('skip')")

    # Create .sourcecombineignore
    (project_root / ".sourcecombineignore").write_text("*.log\nskip_this.py\n")

    # Create output file path
    output_file = tmp_path / "combined.txt"

    # Mock config
    config = utils.DEFAULT_CONFIG.copy()
    config['search'] = config['search'].copy()
    config['search']['root_folders'] = [str(project_root)]

    # Change current working directory to project_root to test auto-detection
    original_cwd = os.getcwd()
    os.chdir(project_root)

    try:
        # Run find_and_combine_files
        find_and_combine_files(
            config=config,
            output_path=str(output_file)
        )

        content = output_file.read_text()

        # Verify filtering
        assert "keep.py" in content
        assert "skip.log" not in content
        assert "skip_this.py" not in content

    finally:
        os.chdir(original_cwd)

def test_ignore_file_manual_cli(tmp_path):
    """Test that --ignore-file CLI override works."""

    # Setup project structure
    project_root = tmp_path / "my_project_cli"
    project_root.mkdir()

    (project_root / "keep.py").write_text("print('keep')")
    (project_root / "custom_skip.txt").write_text("skip me")

    # Create a custom ignore file
    custom_ignore = tmp_path / "custom.ignore"
    custom_ignore.write_text("custom_skip.txt\n")

    # Create output file path
    output_file = tmp_path / "combined_cli.txt"

    # Mock config
    config = utils.DEFAULT_CONFIG.copy()
    config['search'] = config['search'].copy()
    config['search']['root_folders'] = [str(project_root)]
    config['search']['ignore_files'] = [str(custom_ignore)]

    # Run find_and_combine_files
    find_and_combine_files(
        config=config,
        output_path=str(output_file)
    )

    content = output_file.read_text()

    # Verify filtering
    assert "keep.py" in content
    assert "custom_skip.txt" not in content

def test_parse_ignore_file_non_existent():
    """Test parse_ignore_file with a non-existent path."""
    assert utils.parse_ignore_file("non_existent_file") == []

def test_parse_ignore_file_skips_comments_and_empty_lines(tmp_path):
    """Test that parse_ignore_file skips comments and empty lines."""
    ignore_file = tmp_path / "test.ignore"
    ignore_file.write_text("  \n# comment\npattern1\n  # another comment\n  pattern2  \n", encoding="utf-8")

    patterns = utils.parse_ignore_file(ignore_file)
    assert patterns == ["pattern1", "pattern2"]

def test_parse_ignore_file_exception_handling(tmp_path, caplog):
    """Test parse_ignore_file exception handling during reading."""
    ignore_file = tmp_path / "locked.ignore"
    ignore_file.touch()

    from unittest.mock import patch
    with patch("utils.read_file_best_effort", side_effect=Exception("Read error")):
        patterns = utils.parse_ignore_file(ignore_file)
        assert patterns == []
        assert "Could not read ignore file" in caplog.text
        assert "Read error" in caplog.text
