import pytest
from pathlib import Path
from sourcecombine import _generate_tree_string

def test_generate_tree_string_weighted_folders():
    root = Path("/root")
    paths = [
        root / "README.md",
        root / "src" / "main.py",
        root / "src" / "utils.py",
        root / "tests" / "test_main.py",
    ]

    # Metadata with size and tokens
    metadata = {
        root / "README.md": {'size': 1024, 'tokens': 250},
        root / "src" / "main.py": {'size': 2048, 'tokens': 500},
        root / "src" / "utils.py": {'size': 512, 'tokens': 125},
        root / "tests" / "test_main.py": {'size': 1024, 'tokens': 250},
    }

    result = _generate_tree_string(paths, root, 'text', metadata=metadata)

    # Check root - total: 4 files, 4608 bytes (4.50 KB), 1125 tokens
    assert "root/ (4 files, 4.50 KB, 1,125 tokens)" in result

    # README.md is first
    assert "├── README.md (1.00 KB, 250 tokens)" in result

    # Check src - total: 2 files, 2560 bytes (2.50 KB), 625 tokens
    # src is second, followed by tests, so it uses ├──
    assert "├── src (2 files, 2.50 KB, 625 tokens)" in result

    # Check tests - total: 1 file, 1024 bytes (1.00 KB), 250 tokens
    # tests is last.
    assert "└── tests (1 file, 1.00 KB, 250 tokens)" in result

    # Check individual files
    # main.py is child of src. since src is NOT last, prefix is "│   "
    assert "│   ├── main.py (2.00 KB, 500 tokens)" in result
    assert "│   └── utils.py (512.00 B, 125 tokens)" in result

    # test_main.py is child of tests. since tests IS last, prefix is "    "
    assert "    └── test_main.py (1.00 KB, 250 tokens)" in result

def test_generate_tree_string_weighted_folders_no_tokens():
    root = Path("/root")
    paths = [
        root / "a.txt",
        root / "sub" / "b.txt",
    ]

    # Metadata with only size
    metadata = {
        root / "a.txt": {'size': 100},
        root / "sub" / "b.txt": {'size': 200},
    }

    result = _generate_tree_string(paths, root, 'text', metadata=metadata)

    # Check root
    assert "root/ (2 files, 300.00 B)" in result
    # Tokens should not be mentioned if they are 0 or missing
    assert "tokens" not in result

    # Check sub
    assert "└── sub (1 file, 200.00 B)" in result
    assert "    └── b.txt (200.00 B)" in result
