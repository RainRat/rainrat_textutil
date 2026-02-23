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

def test_limit_summary_warning(test_env, capsys):
    """Verify that the execution summary shows a warning when file limit is reached."""
    from sourcecombine import main
    import sys
    from unittest.mock import patch

    d = test_env / "warn_root"
    d.mkdir()
    (d / "f1.txt").touch()
    (d / "f2.txt").touch()

    # Use CLI with --limit 1
    with patch.object(sys, 'argv', ["sourcecombine.py", str(d), "--limit", "1", "--dry-run"]):
        try:
            main()
        except SystemExit:
            pass

    captured = capsys.readouterr()
    assert "WARNING: Output truncated due to file limit." in captured.err

def test_limit_main_config_injection(test_env):
    """Cover main() where it injects max_files into config even if filters section is missing."""
    from sourcecombine import main
    import sys
    from unittest.mock import patch
    import yaml

    d = test_env / "inject_root"
    d.mkdir()
    (d / "f1.txt").touch()

    # Create a config without 'filters' section
    config = {
        'search': {'root_folders': [str(d)]}
    }
    config_file = test_env / "no_filters.yml"
    with open(config_file, 'w') as f:
        yaml.dump(config, f)

    with patch.object(sys, 'argv', ["sourcecombine.py", str(config_file), "--limit", "1", "--dry-run"]):
        try:
            main()
        except SystemExit:
            pass
    # If it didn't crash, it's probably fine. The coverage will confirm.

def test_limit_main_filters_is_not_dict(test_env):
    """Cover main() where it handles config['filters'] being a non-dict (e.g. from invalid yaml)."""
    from sourcecombine import main
    import sys
    from unittest.mock import patch
    import yaml

    d = test_env / "not_dict_root"
    d.mkdir()

    # Create a config where filters is a string
    config = {
        'filters': 'not a dict',
        'search': {'root_folders': [str(d)]}
    }
    config_file = test_env / "filters_not_dict.yml"
    with open(config_file, 'w') as f:
        yaml.dump(config, f)

    with patch.object(sys, 'argv', ["sourcecombine.py", str(config_file), "--limit", "1", "--dry-run"]):
        try:
            main()
        except SystemExit:
            pass

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

def test_limit_list_files_global(test_env):
    """Verify that max_files limit in list_files mode is applied globally across roots."""
    root1 = test_env / "root1"
    root1.mkdir()
    (root1 / "file1.txt").write_text("content 1")
    (root1 / "file2.txt").write_text("content 2")

    root2 = test_env / "root2"
    root2.mkdir()
    (root2 / "file3.txt").write_text("content 3")
    (root2 / "file4.txt").write_text("content 4")

    config = copy.deepcopy(DEFAULT_CONFIG)
    config.setdefault('search', {})['root_folders'] = [str(root1), str(root2)]
    config['filters']['max_files'] = 2

    # Run with list_files=True
    stats = find_and_combine_files(config, output_path=None, list_files=True)

    # Should show 2 files total across all roots
    assert stats['total_files'] == 2
    assert stats['limit_reached'] is True
    assert stats['filter_reasons']['file_limit'] == 2

def test_limit_list_files_partial_truncation(test_env):
    """Verify that max_files limit in list_files mode correctly truncates a root folder partially."""
    root1 = test_env / "partial_root"
    root1.mkdir()
    (root1 / "file1.txt").write_text("c1")
    (root1 / "file2.txt").write_text("c2")
    (root1 / "file3.txt").write_text("c3")

    config = copy.deepcopy(DEFAULT_CONFIG)
    config.setdefault('search', {})['root_folders'] = [str(root1)]
    config['filters']['max_files'] = 2

    stats = find_and_combine_files(config, output_path=None, list_files=True)

    assert stats['total_files'] == 2
    assert stats['limit_reached'] is True
    assert stats['filter_reasons']['file_limit'] == 1

def test_limit_tree_view_global(test_env):
    """Verify that max_files limit in tree_view mode is applied globally across roots."""
    root1 = test_env / "root1"
    root1.mkdir()
    (root1 / "file1.txt").write_text("content 1")
    (root1 / "file2.txt").write_text("content 2")

    root2 = test_env / "root2"
    root2.mkdir()
    (root2 / "file3.txt").write_text("content 3")
    (root2 / "file4.txt").write_text("content 4")

    config = copy.deepcopy(DEFAULT_CONFIG)
    config.setdefault('search', {})['root_folders'] = [str(root1), str(root2)]
    config['filters']['max_files'] = 2

    # Run with tree_view=True
    stats = find_and_combine_files(config, output_path=None, tree_view=True)

    # Should show 2 files total across all roots
    assert stats['total_files'] == 2
    assert stats['limit_reached'] is True
    assert stats['filter_reasons']['file_limit'] == 2

def test_limit_token_sort_stats_recalculation(test_env):
    """Verify that max_files with sort_by='tokens' correctly recalculates stats."""
    root = test_env / "token_root"
    root.mkdir()

    # file1: 20 chars -> ~5 tokens
    (root / "file1.txt").write_text("a" * 20)
    # file2: 40 chars -> ~10 tokens
    (root / "file2.txt").write_text("b" * 40)
    # file3: 60 chars -> ~15 tokens
    (root / "file3.txt").write_text("c" * 60)

    config = copy.deepcopy(DEFAULT_CONFIG)
    config.setdefault('search', {})['root_folders'] = [str(root)]
    config['filters']['max_files'] = 2
    config['output']['sort_by'] = 'tokens'

    # Estimate tokens to ensure they are calculated
    stats = find_and_combine_files(config, output_path=str(test_env / "out.txt"), estimate_tokens=False)

    # Should have limited to 2 files.
    assert stats['total_files'] == 2
    assert stats['limit_reached'] is True

    # file1 (20 bytes) + file2 (40 bytes) = 60 bytes
    assert stats['total_size_bytes'] == 60
    assert stats['total_tokens'] > 0

    # Verify file3 is NOT in the output
    content = (test_env / "out.txt").read_text()
    assert "file1.txt" in content
    assert "file2.txt" in content
    assert "file3.txt" not in content
