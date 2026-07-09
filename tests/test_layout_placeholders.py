import pytest
import os
from pathlib import Path
from sourcecombine import find_and_combine_files
import utils

def test_layout_placeholders_in_header(tmp_path):
    """Test that layout placeholders in global_header work and suppress default output."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "file1.txt").write_text("Content 1", encoding='utf-8')
    (project_dir / "file2.txt").write_text("Content 2", encoding='utf-8')

    config = {
        'search': {'root_folders': [str(project_dir)]},
        'output': {
            'global_header_template': "PROJECT: {{PROJECT_NAME}}\nSTRUCTURE:\n{{TREE}}\nSUMMARY:\n{{OVERVIEW}}\nCONTENTS:\n{{TOC}}\n---\n",
            'include_tree': True,
            'project_overview': True,
            'table_of_contents': True
        }
    }

    output_file = tmp_path / "combined.txt"
    find_and_combine_files(config, str(output_file))

    content = output_file.read_text(encoding='utf-8')

    # Check that placeholders are resolved
    assert "PROJECT: project" in content
    assert "STRUCTURE:" in content
    assert "project/" in content  # Part of the tree
    assert "SUMMARY:" in content
    assert "Project Overview:" in content
    assert "CONTENTS:" in content
    assert "Table of Contents:" in content
    assert "file1.txt" in content

    # Check for duplication (should NOT be prepended before the header)
    # The header starts with "PROJECT:", so "Project Overview:" should only appear after "SUMMARY:"
    parts = content.split("SUMMARY:")
    assert "Project Overview:" not in parts[0]
    assert "Project Overview:" in parts[1]

    # Similarly for tree and TOC
    parts_tree = content.split("STRUCTURE:")
    assert "project/" not in parts_tree[0]
    assert "project/" in parts_tree[1]

    parts_toc = content.split("CONTENTS:")
    assert "Table of Contents:" not in parts_toc[0]
    assert "Table of Contents:" in parts_toc[1]

def test_layout_placeholders_in_footer(tmp_path):
    """Test that layout placeholders in global_footer work."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "file1.txt").write_text("Content 1", encoding='utf-8')

    config = {
        'search': {'root_folders': [str(project_dir)]},
        'output': {
            'global_footer_template': "\nFOOTER START\n{{TREE}}\nFOOTER END",
            'include_tree': False, # Explicitly disable flag, but use placeholder
        }
    }

    output_file = tmp_path / "combined.txt"
    find_and_combine_files(config, str(output_file))

    content = output_file.read_text(encoding='utf-8')

    assert "FOOTER START" in content
    assert "project/" in content
    assert "FOOTER END" in content

    # Ensure it's in the footer area
    assert content.index("FOOTER START") > content.index("Content 1")

def test_layout_placeholders_no_flags(tmp_path):
    """Test that layout placeholders work even if corresponding flags are False."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "file1.txt").write_text("Content 1", encoding='utf-8')

    config = {
        'search': {'root_folders': [str(project_dir)]},
        'output': {
            'global_header_template': "TOC:\n{{TOC}}\n",
            'table_of_contents': False, # Flag is off
        }
    }

    output_file = tmp_path / "combined.txt"
    find_and_combine_files(config, str(output_file))

    content = output_file.read_text(encoding='utf-8')
    assert "Table of Contents:" in content
    assert "file1.txt" in content
