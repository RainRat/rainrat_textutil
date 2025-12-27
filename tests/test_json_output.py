import json
import logging
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
import sys

# Ensure repo root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sourcecombine import find_and_combine_files, InvalidConfigError
import utils

def test_json_output_success(tmp_path):
    # Setup
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "a.py").write_text("print('a')", encoding="utf-8")
    (src_dir / "b.txt").write_text("text b", encoding="utf-8")

    config = {
        'search': {'root_folders': [str(src_dir)]},
        'filters': {},
        'output': {'file': str(tmp_path / "output.json")},
        'pairing': {'enabled': False}
    }

    # Execute
    stats = find_and_combine_files(config, str(tmp_path / "output.json"), output_format='json')

    # Verify
    assert stats['total_files'] == 2

    with open(tmp_path / "output.json", 'r', encoding='utf-8') as f:
        data = json.load(f)

    assert isinstance(data, list)
    assert len(data) == 2

    # Sort by path to ensure deterministic check
    data.sort(key=lambda x: x['path'])

    assert data[0]['path'] == 'a.py'
    assert data[0]['content'] == "print('a')"

    assert data[1]['path'] == 'b.txt'
    assert data[1]['content'] == "text b"

def test_json_output_incompatible_with_pairing():
    config = {
        'search': {'root_folders': []},
        'pairing': {'enabled': True}
    }
    with pytest.raises(InvalidConfigError, match="JSON format is not compatible"):
        find_and_combine_files(config, "out", output_format='json')

def test_json_output_excludes_header_templates(tmp_path):
    # JSON output should NOT have the header templates inside the content string,
    # nor should it wrap the file in templates.
    # The content inside JSON should be raw processed content.

    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "a.txt").write_text("content", encoding="utf-8")

    config = {
        'search': {'root_folders': [str(src_dir)]},
        'output': {
            'file': str(tmp_path / "output.json"),
            'header_template': 'HEADER',
            'footer_template': 'FOOTER',
            'global_header_template': 'GLOBAL_HEAD',
            'global_footer_template': 'GLOBAL_FOOT'
        },
        'pairing': {'enabled': False}
    }

    find_and_combine_files(config, str(tmp_path / "output.json"), output_format='json')

    with open(tmp_path / "output.json", 'r', encoding='utf-8') as f:
        # If global header was written to file, this would fail JSON parsing
        data = json.load(f)

    assert len(data) == 1
    # Content should not contain per-file templates
    assert data[0]['content'] == "content"
    # And definitely not the global ones
    assert "GLOBAL_HEAD" not in json.dumps(data)

def test_json_output_max_size_placeholder(tmp_path):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    large_file = src_dir / "large.txt"
    large_file.write_text("A" * 100, encoding="utf-8")

    config = {
        'search': {'root_folders': [str(src_dir)]},
        'filters': {'max_size_bytes': 10},
        'output': {
            'file': str(tmp_path / "output.json"),
            'max_size_placeholder': 'SKIPPED {{FILENAME}}'
        },
        'pairing': {'enabled': False}
    }

    find_and_combine_files(config, str(tmp_path / "output.json"), output_format='json')

    with open(tmp_path / "output.json", 'r', encoding='utf-8') as f:
        data = json.load(f)

    assert len(data) == 1
    assert data[0]['path'] == 'large.txt'
    assert data[0]['content'] == 'SKIPPED large.txt'
