import os
import sys
from pathlib import Path
from sourcecombine import find_and_combine_files, utils

def test_output_file_is_excluded(tmp_path):
    """Test that the output file is automatically excluded from the combined result."""
    # Create a dummy folder with some files
    test_dir = tmp_path / "test_project"
    test_dir.mkdir()

    file1 = test_dir / "file1.txt"
    file1.write_text("content 1", encoding="utf-8")

    file2 = test_dir / "file2.txt"
    file2.write_text("content 2", encoding="utf-8")

    # Create what will be the output file beforehand
    output_file = test_dir / "combined_output.txt"
    output_file.write_text("old content", encoding="utf-8")

    config = utils.DEFAULT_CONFIG.copy()
    config['search'] = {'root_folders': [str(test_dir)]}
    config['output'] = {'file': str(output_file)}

    # Run the tool
    stats = find_and_combine_files(
        config,
        str(output_file),
        dry_run=False
    )

    # Verify stats
    assert stats['total_discovered'] == 3 # file1, file2, output_file
    assert stats['total_files'] == 2      # file1, file2
    assert stats['filter_reasons'].get('output_file') == 1

    # Verify content of output_file
    content = output_file.read_text(encoding="utf-8")
    assert "file1.txt" in content
    assert "content 1" in content
    assert "file2.txt" in content
    assert "content 2" in content
    assert "combined_output.txt" not in content
    assert "old content" not in content

def test_output_file_is_excluded_dry_run(tmp_path):
    """Test that the output file is excluded even in dry-run mode."""
    test_dir = tmp_path / "test_project_dry"
    test_dir.mkdir()

    file1 = test_dir / "file1.txt"
    file1.write_text("content 1", encoding="utf-8")

    output_file = test_dir / "combined_output.txt"
    output_file.touch()

    config = utils.DEFAULT_CONFIG.copy()
    config['search'] = {'root_folders': [str(test_dir)]}
    config['output'] = {'file': str(output_file)}

    stats = find_and_combine_files(
        config,
        str(output_file),
        dry_run=True
    )

    assert stats['total_discovered'] == 2
    assert stats['total_files'] == 1
    assert stats['filter_reasons'].get('output_file') == 1
