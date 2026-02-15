import json
import os
import shutil
from pathlib import Path
import pytest
from sourcecombine import extract_files
from utils import DEFAULT_CONFIG

def test_filtered_extraction_json(tmp_path):
    output_dir = tmp_path / "output"
    archive_content = json.dumps([
        {"path": "src/main.py", "content": "print('main')"},
        {"path": "src/utils.py", "content": "print('utils')"},
        {"path": "README.md", "content": "# Readme"}
    ])

    config = DEFAULT_CONFIG.copy()
    config['filters'] = {
        'inclusion_groups': {
            'python': {
                'enabled': True,
                'filenames': ['*.py']
            }
        }
    }

    stats = extract_files(archive_content, output_dir, config=config)

    assert stats['total_discovered'] == 3
    assert stats['total_files'] == 2
    assert (output_dir / "src/main.py").exists()
    assert (output_dir / "src/utils.py").exists()
    assert not (output_dir / "README.md").exists()

def test_filtered_extraction_text(tmp_path):
    output_dir = tmp_path / "output"
    archive_content = (
        "--- file1.txt ---\ncontent1\n--- end file1.txt ---\n"
        "--- file2.log ---\ncontent2\n--- end file2.log ---\n"
    )

    config = DEFAULT_CONFIG.copy()
    config['filters'] = {
        'exclusions': {
            'filenames': ['*.log']
        }
    }

    stats = extract_files(archive_content, output_dir, config=config)

    assert stats['total_files'] == 1
    assert (output_dir / "file1.txt").exists()
    assert not (output_dir / "file2.log").exists()

def test_extract_list_files(capsys, tmp_path):
    archive_content = json.dumps([
        {"path": "a.py", "content": "a"},
        {"path": "b.txt", "content": "b"}
    ])

    stats = extract_files(archive_content, tmp_path, list_files=True)

    captured = capsys.readouterr()
    assert "a.py" in captured.out
    assert "b.txt" in captured.out
    assert not (tmp_path / "a.py").exists()
    assert stats['total_files'] == 2

def test_extract_tree_view(capsys, tmp_path):
    archive_content = json.dumps([
        {"path": "src/a.py", "content": "a"},
        {"path": "docs/b.md", "content": "b"}
    ])

    stats = extract_files(archive_content, tmp_path, tree_view=True, source_name="my_archive.json")

    captured = capsys.readouterr()
    assert "my_archive.json/" in captured.out
    assert "src" in captured.out
    assert "a.py" in captured.out
    assert "docs" in captured.out
    assert "b.md" in captured.out
    assert stats['total_files'] == 2

def test_filtered_extraction_with_exclusion_folder(tmp_path):
    output_dir = tmp_path / "output"
    archive_content = json.dumps([
        {"path": "src/main.py", "content": "print('main')"},
        {"path": "tests/test_main.py", "content": "print('test')"},
    ])

    config = DEFAULT_CONFIG.copy()
    config['filters'] = {
        'exclusions': {
            'folders': ['tests']
        }
    }

    stats = extract_files(archive_content, output_dir, config=config)

    assert stats['total_files'] == 1
    assert (output_dir / "src/main.py").exists()
    assert not (output_dir / "tests/test_main.py").exists()
