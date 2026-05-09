import os
from pathlib import Path
from sourcecombine import find_and_combine_files, utils

def test_cli_template_overrides(tmp_path):
    """Test that template overrides provided via CLI (mocked via config) are applied."""
    # Setup: create some dummy files
    file1 = tmp_path / "file1.txt"
    file1.write_text("content1", encoding='utf-8')
    file2 = tmp_path / "file2.txt"
    file2.write_text("content2", encoding='utf-8')

    output_file = tmp_path / "combined.txt"

    # Simulate CLI overrides by crafting the config dictionary
    # In sourcecombine.main(), these values are injected into config['output']
    config = {
        'search': {'root_folders': [str(tmp_path)], 'recursive': False},
        'filters': {'max_size_bytes': 5}, # file1 and file2 are 8 bytes, so they will be skipped
        'output': {
            'header_template': "H: {{FILENAME}}\n",
            'footer_template': "F: {{FILENAME}}\n",
            'global_header_template': "GLOBAL START\n",
            'global_footer_template': "GLOBAL END\n",
            'max_size_placeholder': "SKIP: {{FILENAME}}\n",
        }
    }

    # Run the combination
    find_and_combine_files(config, str(output_file))

    # Verify output
    content = output_file.read_text(encoding='utf-8')

    assert "GLOBAL START\n" in content
    assert "GLOBAL END\n" in content
    # Both files exceed 5 bytes, so they should use the max_size_placeholder
    assert "SKIP: file1.txt\n" in content
    assert "SKIP: file2.txt\n" in content
    # Header/Footer should also be present around the placeholder
    assert "H: file1.txt\nSKIP: file1.txt\nF: file1.txt\n" in content
    assert "H: file2.txt\nSKIP: file2.txt\nF: file2.txt\n" in content

def test_cli_template_overrides_no_skip(tmp_path):
    """Test template overrides when files are not skipped."""
    file1 = tmp_path / "file1.txt"
    file1.write_text("c1", encoding='utf-8')

    output_file = tmp_path / "combined.txt"

    config = {
        'search': {'root_folders': [str(tmp_path)], 'recursive': False},
        'output': {
            'header_template': "START {{FILENAME}}\n",
            'footer_template': "END {{FILENAME}}\n",
            'global_header_template': "PROJECT START\n",
            'global_footer_template': "PROJECT END\n",
        }
    }

    find_and_combine_files(config, str(output_file))

    content = output_file.read_text(encoding='utf-8')

    assert content == "PROJECT START\nSTART file1.txt\nc1END file1.txt\nPROJECT END\n"
