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
    """Test parse_ignore_file with a non-existent file path."""
    assert utils.parse_ignore_file("non_existent_file.txt") == []

def test_parse_ignore_file_with_comments_and_empty_lines(tmp_path):
    """Test parse_ignore_file skips comments and empty lines."""
    ignore_file = tmp_path / ".ignore"
    ignore_file.write_text("# Comment\n\n  \npattern1\n  # Nested comment\npattern2  ", encoding='utf-8')

    patterns = utils.parse_ignore_file(ignore_file)
    assert patterns == ["pattern1", "pattern2"]

def test_parse_ignore_file_exception(monkeypatch, caplog, tmp_path):
    """Test parse_ignore_file handling an exception during read."""
    import logging

    def mock_read_file_best_effort(path):
        raise RuntimeError("Mocked read error")

    # We need to mock it in utils since parse_ignore_file calls it
    monkeypatch.setattr(utils, "read_file_best_effort", mock_read_file_best_effort)

    # Create a dummy file so is_file() passes
    dummy = tmp_path / "dummy_ignore"
    dummy.touch()

    caplog.set_level(logging.WARNING)
    patterns = utils.parse_ignore_file(dummy)
    assert patterns == []
    assert "Could not read ignore file" in caplog.text
    assert "Mocked read error" in caplog.text
