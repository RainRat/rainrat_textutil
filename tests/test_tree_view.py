import pytest
from unittest.mock import patch, MagicMock
import sys
import os
from pathlib import Path
import yaml
from sourcecombine import main, _print_tree

def test_tree_view_output(capsys, tmp_path):
    """Verify that --tree produces the expected hierarchical output."""

    # Setup a directory structure
    root = tmp_path / "myproj"
    root.mkdir()
    (root / "file1.txt").write_text("content")
    src = root / "src"
    src.mkdir()
    (src / "main.py").write_text("print('hello')")
    (src / "utils.py").write_text("def util(): pass")
    docs = root / "docs"
    docs.mkdir()
    (docs / "readme.md").write_text("# Readme")

    # Run with --tree
    # We use main() to test the integration of the flag and the printing logic
    with patch.object(sys, 'argv', ["sourcecombine.py", str(root), "--tree"]):
        try:
            main()
        except SystemExit:
            pass

    captured = capsys.readouterr()
    out = captured.out

    # Expected output structure (order of items at same level is alphabetical):
    # myproj/
    # ├── docs
    # │   └── readme.md
    # ├── file1.txt
    # └── src
    #     ├── main.py
    #     └── utils.py

    assert "myproj/" in out
    assert "├── docs" in out
    assert "│   └── readme.md" in out
    assert "├── file1.txt" in out
    assert "└── src" in out
    assert "    ├── main.py" in out
    assert "    └── utils.py" in out

    # Verify summary title in stderr
    assert "Tree View Summary" in captured.err

def test_tree_view_with_pairing(capsys, tmp_path):
    """Verify --tree works correctly when pairing is enabled."""
    root = tmp_path / "pairproj"
    root.mkdir()
    (root / "foo.c").write_text("c")
    (root / "foo.h").write_text("h")
    (root / "bar.c").write_text("lone c")

    config = {
        'search': {'root_folders': [str(root)]},
        'pairing': {
            'enabled': True,
            'source_extensions': ['.c'],
            'header_extensions': ['.h'],
            'include_mismatched': False
        }
    }

    config_file = tmp_path / "config.yml"
    with open(config_file, 'w') as f:
        yaml.dump(config, f)

    with patch.object(sys, 'argv', ["sourcecombine.py", str(config_file), "--tree"]):
        try:
            main()
        except SystemExit:
            pass

    captured = capsys.readouterr()
    out = captured.out

    assert "pairproj/" in out
    assert "├── foo.c" in out
    assert "└── foo.h" in out
    # bar.c should not be included because include_mismatched is False and it's not paired
    assert "bar.c" not in out

def test_print_tree_fallback_path(capsys):
    """Test the fallback logic in _print_tree when paths are not relative to root."""
    # This specifically targets the try-except ValueError block in _print_tree (line 699)

    # Use absolute paths that are clearly not under the root_path
    paths = [Path("/external_root/some_file.txt")]
    root_path = Path("/app/project")

    _print_tree(paths, root_path)

    captured = capsys.readouterr()
    # It should still print the root name
    assert "project/" in captured.out

    # And it should have used the absolute path in the tree
    # Path("/external_root/some_file.txt").parts -> ('/', 'external_root', 'some_file.txt')
    assert "external_root" in captured.out
    assert "some_file.txt" in captured.out

def test_tree_view_no_files(capsys, tmp_path):
    """Verify tree view behavior when no files are matched."""
    root = tmp_path / "emptyproj"
    root.mkdir()

    # Run with --tree on empty dir
    with patch.object(sys, 'argv', ["sourcecombine.py", str(root), "--tree"]):
        try:
            main()
        except SystemExit:
            pass

    captured = capsys.readouterr()
    # If no files are matched, iteration_targets is empty, so no tree is printed.
    assert captured.out == ""
    assert "Total Files:      0" in captured.err
