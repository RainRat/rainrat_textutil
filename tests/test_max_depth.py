import os
from pathlib import Path
import pytest
from sourcecombine import collect_file_paths, find_and_combine_files
import utils

def setup_test_folders(tmp_path):
    """
    root/
      f1.txt
      sub1/
        f2.txt
        sub2/
          f3.txt
    """
    root = tmp_path / "test_root"
    root.mkdir()
    (root / "f1.txt").write_text("root file")

    sub1 = root / "sub1"
    sub1.mkdir()
    (sub1 / "f2.txt").write_text("sub1 file")

    sub2 = sub1 / "sub2"
    sub2.mkdir()
    (sub2 / "f3.txt").write_text("sub2 file")

    return root

def test_collect_file_paths_max_depth(tmp_path):
    root = setup_test_folders(tmp_path)

    # No limit
    paths, _, _ = collect_file_paths(str(root), recursive=True, exclude_folders=[])
    assert len(paths) == 3

    # depth 1 (root files only)
    paths, _, _ = collect_file_paths(str(root), recursive=True, exclude_folders=[], max_depth=1)
    assert len(paths) == 1
    assert paths[0].name == "f1.txt"

    # depth 2 (root and sub1)
    paths, _, _ = collect_file_paths(str(root), recursive=True, exclude_folders=[], max_depth=2)
    assert len(paths) == 2
    names = {p.name for p in paths}
    assert "f1.txt" in names
    assert "f2.txt" in names
    assert "f3.txt" not in names

def test_find_and_combine_files_max_depth(tmp_path):
    root = setup_test_folders(tmp_path)
    output = tmp_path / "combined.txt"

    config = utils.DEFAULT_CONFIG.copy()
    config['search'] = {'root_folders': [str(root)], 'max_depth': 1}

    stats = find_and_combine_files(config, str(output))
    assert stats['total_files'] == 1

    content = output.read_text()
    assert "f1.txt" in content
    assert "f2.txt" not in content

def test_cli_max_depth(tmp_path, monkeypatch):
    import sys
    from sourcecombine import main

    root = setup_test_folders(tmp_path)
    output = tmp_path / "combined_cli.txt"

    # Mock CLI arguments
    monkeypatch.setattr(sys, 'argv', [
        'sourcecombine.py',
        str(root),
        '--output', str(output),
        '--max-depth', '1'
    ])

    # main() doesn't always call sys.exit(0), so we just call it and check the output.
    main()

    assert output.exists()
    content = output.read_text()
    assert "f1.txt" in content
    assert "f2.txt" not in content

def test_invalid_max_depth():
    config = utils.DEFAULT_CONFIG.copy()
    config['search'] = {'max_depth': -1}
    with pytest.raises(utils.InvalidConfigError, match="search.max_depth must be 0 or more"):
        utils.validate_config(config)
