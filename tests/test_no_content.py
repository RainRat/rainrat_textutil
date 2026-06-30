import sys; import os; from pathlib import Path; sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

import json
import pytest
from pathlib import Path
import sourcecombine
import utils

@pytest.fixture
def temp_project(tmp_path):
    # Create a small temporary project
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "file1.py").write_text("print('hello')", encoding='utf-8')
    (project_dir / "file2.txt").write_text("world", encoding='utf-8')
    return project_dir

def test_no_content_text_format(temp_project, tmp_path):
    output_file = tmp_path / "combined.txt"
    config = utils.DEFAULT_CONFIG.copy()
    config['search'] = {'root_folders': [str(temp_project)]}
    config['output'] = {
        'file': str(output_file),
        'format': 'text',
        'skip_content': True,
        'header_template': "--- {{FILENAME}} ---\n",
        'footer_template': "--- end {{FILENAME}} ---\n"
    }

    sourcecombine.find_and_combine_files(config, str(output_file), output_format='text')

    content = output_file.read_text(encoding='utf-8')
    # Templates should be present
    assert "--- file1.py ---" in content
    assert "--- end file1.py ---" in content
    assert "--- file2.txt ---" in content
    assert "--- end file2.txt ---" in content
    # Actual file content should be absent
    assert "print('hello')" not in content
    assert "world" not in content

def test_no_content_json_format(temp_project, tmp_path):
    output_file = tmp_path / "combined.json"
    config = utils.DEFAULT_CONFIG.copy()
    config['search'] = {'root_folders': [str(temp_project)]}
    config['output'] = {
        'file': str(output_file),
        'format': 'json',
        'skip_content': True
    }

    sourcecombine.find_and_combine_files(config, str(output_file), output_format='json')

    with open(output_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    assert len(data) == 2
    for entry in data:
        # Metadata should be present
        assert 'path' in entry
        assert 'tokens' in entry
        assert 'size_bytes' in entry
        # content field should be absent
        assert 'content' not in entry

def test_no_content_markdown_format(temp_project, tmp_path):
    output_file = tmp_path / "combined.md"
    config = utils.DEFAULT_CONFIG.copy()
    config['search'] = {'root_folders': [str(temp_project)]}
    config['output'] = {
        'file': str(output_file),
        'format': 'markdown',
        'skip_content': True,
        'header_template': "## {{FILENAME}}\n\n```{{LANG}}\n",
        'footer_template': "\n```\n\n"
    }

    sourcecombine.find_and_combine_files(config, str(output_file), output_format='markdown')

    content = output_file.read_text(encoding='utf-8')
    # Templates should be present
    assert "## file1.py" in content
    assert "```python" in content
    # Actual file content should be absent
    assert "print('hello')" not in content

def test_no_content_csv_format(temp_project, tmp_path):
    output_file = tmp_path / "combined.csv"
    config = utils.DEFAULT_CONFIG.copy()
    config['search'] = {'root_folders': [str(temp_project)]}
    config['output'] = {
        'file': str(output_file),
        'format': 'csv',
        'skip_content': True
    }

    sourcecombine.find_and_combine_files(config, str(output_file), output_format='csv')

    import csv
    with open(output_file, 'r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == 2
    for row in rows:
        assert row['path'] in ('file1.py', 'file2.txt')
        # content field should be empty string
        assert row['content'] == ""
        # Metadata should still be present
        assert int(row['size_bytes']) > 0
