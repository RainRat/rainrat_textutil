import os
from pathlib import Path
import pytest
from sourcecombine import find_and_combine_files, extract_files
from utils import DEFAULT_CONFIG
import copy

@pytest.fixture
def test_env(tmp_path):
    """Create a test environment with multiple files."""
    d = tmp_path / "src"
    d.mkdir()
    (d / "file1.txt").write_text("content 1", encoding='utf-8')
    (d / "file2.txt").write_text("content 2", encoding='utf-8')
    (d / "file3.txt").write_text("content 3", encoding='utf-8')
    return tmp_path

def test_limit_single_mode(test_env):
    config = copy.deepcopy(DEFAULT_CONFIG)
    config.setdefault('search', {})['root_folders'] = [str(test_env / "src")]
    config['filters']['max_files'] = 2

    output_file = test_env / "combined.txt"
    stats = find_and_combine_files(config, str(output_file))

    assert stats['total_files'] == 2
    assert stats['limit_reached'] is True
    assert stats['filter_reasons']['file_limit'] == 1

    content = output_file.read_text(encoding='utf-8')
    assert "file1.txt" in content
    assert "file2.txt" in content
    assert "file3.txt" not in content

def test_limit_with_sort(test_env):
    # file3 is largest by tokens (if we had tokens) or just by alphabetical name here
    # Let's make file3 larger
    (test_env / "src" / "file3.txt").write_text("content 3 - very long indeed", encoding='utf-8')

    config = copy.deepcopy(DEFAULT_CONFIG)
    config.setdefault('search', {})['root_folders'] = [str(test_env / "src")]
    config['filters']['max_files'] = 1
    config['output']['sort_by'] = 'size'
    config['output']['sort_reverse'] = True

    output_file = test_env / "combined.txt"
    stats = find_and_combine_files(config, str(output_file))

    assert stats['total_files'] == 1
    assert "file3.txt" in output_file.read_text(encoding='utf-8')

def test_limit_pairing(test_env):
    d = test_env / "pair_src"
    d.mkdir()
    (d / "a.cpp").touch()
    (d / "a.h").touch()
    (d / "b.cpp").touch()
    (d / "b.h").touch()
    (d / "c.cpp").touch()
    (d / "c.h").touch()

    config = copy.deepcopy(DEFAULT_CONFIG)
    config.setdefault('search', {})['root_folders'] = [str(d)]
    config['pairing'] = {
        'enabled': True,
        'source_extensions': ['.cpp'],
        'header_extensions': ['.h']
    }
    config['filters']['max_files'] = 2

    out_dir = test_env / "out"
    stats = find_and_combine_files(config, str(out_dir))

    assert stats['limit_reached'] is True
    assert stats['filter_reasons']['file_limit'] == 1 # 3 pairs total, 1 skipped

    # Count .combined files
    combined_files = list(out_dir.glob("*.combined"))
    assert len(combined_files) == 2

def test_limit_extraction(test_env):
    content = """--- file1.txt ---
content 1
--- end file1.txt ---
--- file2.txt ---
content 2
--- end file2.txt ---
--- file3.txt ---
content 3
--- end file3.txt ---
"""
    out_dir = test_env / "extracted"
    out_dir.mkdir()

    stats = extract_files(content, str(out_dir), limit=2)

    assert stats['total_files'] == 2
    assert stats['limit_reached'] is True
    assert stats['filter_reasons']['file_limit'] == 1

    assert (out_dir / "file1.txt").exists()
    assert (out_dir / "file2.txt").exists()
    assert not (out_dir / "file3.txt").exists()
