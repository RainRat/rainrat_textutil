import sys
import os
import time
from pathlib import Path
import pytest

# Add project root to path
sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

import utils
from sourcecombine import find_and_combine_files

@pytest.fixture
def test_env(tmp_path):
    root = tmp_path / "root"
    root.mkdir()

    # Create files with different sizes and contents
    (root / "a.txt").write_text("small", encoding="utf-8") # 5 chars
    (root / "b.txt").write_text("very large content here", encoding="utf-8") # 23 chars
    (root / "c.txt").write_text("medium content", encoding="utf-8") # 14 chars

    # Create a subfolder for depth tests
    sub = root / "sub"
    sub.mkdir()
    (sub / "d.txt").write_text("depth 2", encoding="utf-8")

    # Set modification times (a < c < b)
    now = time.time()
    os.utime(root / "a.txt", (now - 100, now - 100))
    os.utime(root / "c.txt", (now - 50, now - 50))
    os.utime(root / "b.txt", (now - 10, now - 10))

    return root, tmp_path

def test_sort_by_name(test_env, monkeypatch):
    root, tmp_path = test_env
    out_file = tmp_path / "out.txt"
    config = {
        "search": {"root_folders": [str(root)]},
        "output": {
            "file": str(out_file),
            "sort_by": "name",
            "header_template": "{{FILENAME}}\n",
            "footer_template": "\n"
        }
    }

    find_and_combine_files(config, str(out_file))
    content = out_file.read_text(encoding="utf-8")
    lines = [line.strip() for line in content.splitlines() if line.strip().endswith(".txt")]
    # Default is alphabetical: a, b, c, sub/d
    assert lines == ["a.txt", "b.txt", "c.txt", "sub/d.txt"]

def test_sort_by_name_reverse(test_env, monkeypatch):
    root, tmp_path = test_env
    out_file = tmp_path / "out.txt"
    config = {
        "search": {"root_folders": [str(root)]},
        "output": {
            "file": str(out_file),
            "sort_by": "name",
            "sort_reverse": True,
            "header_template": "{{FILENAME}}\n",
            "footer_template": "\n"
        }
    }

    find_and_combine_files(config, str(out_file))
    content = out_file.read_text(encoding="utf-8")
    lines = [line.strip() for line in content.splitlines() if line.strip().endswith(".txt")]
    assert lines == ["sub/d.txt", "c.txt", "b.txt", "a.txt"]

def test_sort_by_size(test_env, monkeypatch):
    root, tmp_path = test_env
    out_file = tmp_path / "out.txt"
    config = {
        "search": {"root_folders": [str(root)]},
        "output": {
            "file": str(out_file),
            "sort_by": "size",
            "header_template": "{{FILENAME}}\n",
            "footer_template": "\n"
        }
    }

    find_and_combine_files(config, str(out_file))
    content = out_file.read_text(encoding="utf-8")
    lines = [line.strip() for line in content.splitlines() if line.strip().endswith(".txt")]
    # Sizes: a(5), sub/d(7), c(14), b(23)
    assert lines == ["a.txt", "sub/d.txt", "c.txt", "b.txt"]

def test_sort_by_modified(test_env, monkeypatch):
    root, tmp_path = test_env
    out_file = tmp_path / "out.txt"
    config = {
        "search": {"root_folders": [str(root)]},
        "output": {
            "file": str(out_file),
            "sort_by": "modified",
            "header_template": "{{FILENAME}}\n",
            "footer_template": "\n"
        }
    }

    find_and_combine_files(config, str(out_file))
    content = out_file.read_text(encoding="utf-8")
    lines = [line.strip() for line in content.splitlines() if line.strip().endswith(".txt")]
    # Times: a (oldest), c, b, sub/d (newest)
    assert lines[0] == "a.txt"
    assert lines[1] == "c.txt"
    assert lines[2] == "b.txt"
    assert lines[3] == "sub/d.txt"

def test_sort_by_depth(test_env, monkeypatch):
    root, tmp_path = test_env
    out_file = tmp_path / "out.txt"
    config = {
        "search": {"root_folders": [str(root)]},
        "output": {
            "file": str(out_file),
            "sort_by": "depth",
            "header_template": "{{FILENAME}}\n",
            "footer_template": "\n"
        }
    }

    find_and_combine_files(config, str(out_file))
    content = out_file.read_text(encoding="utf-8")
    lines = [line.strip() for line in content.splitlines() if line.strip().endswith(".txt")]
    # Depth 1: a, b, c. Depth 2: sub/d
    # Within same depth, falls back to name.
    assert lines == ["a.txt", "b.txt", "c.txt", "sub/d.txt"]

def test_sort_by_tokens(test_env, monkeypatch):
    root, tmp_path = test_env
    monkeypatch.setattr(utils, "tiktoken", None) # Use char length / 4

    out_file = tmp_path / "out.txt"
    config = {
        "search": {"root_folders": [str(root)]},
        "output": {
            "file": str(out_file),
            "sort_by": "tokens",
            "header_template": "{{FILENAME}}\n",
            "footer_template": "\n"
        }
    }

    # a: "small" (5 chars) -> 1 token
    # sub/d: "depth 2" (7 chars) -> 1 token
    # c: "medium content" (14 chars) -> 3 tokens
    # b: "very large content here" (23 chars) -> 5 tokens

    find_and_combine_files(config, str(out_file))
    content = out_file.read_text(encoding="utf-8")
    lines = [line.strip() for line in content.splitlines() if line.strip().endswith(".txt")]

    assert lines == ["a.txt", "sub/d.txt", "c.txt", "b.txt"]

def test_sort_with_budget(test_env, monkeypatch):
    root, tmp_path = test_env
    monkeypatch.setattr(utils, "tiktoken", None)

    out_file = tmp_path / "out.txt"
    config = {
        "search": {"root_folders": [str(root)]},
        "filters": {"max_total_tokens": 5}, # a(1) + sub/d(1) + c(3) = 5
        "output": {
            "file": str(out_file),
            "sort_by": "size", # a(5 bytes), sub/d(7), c(14), b(23)
            "header_template": "",
            "footer_template": ""
        }
    }

    stats = find_and_combine_files(config, str(out_file))
    assert stats['total_files'] == 3 # a, sub/d, c
    assert "very large" not in out_file.read_text()

def test_pairing_sort(test_env, monkeypatch):
    root, tmp_path = test_env
    # Create pairs
    (root / "file1.cpp").write_text("src1", encoding="utf-8")
    (root / "file1.h").write_text("hdr1", encoding="utf-8")
    (root / "file2.cpp").write_text("longer source file", encoding="utf-8")
    (root / "file2.h").write_text("hdr2", encoding="utf-8")

    out_dir = tmp_path / "paired"
    config = {
        "search": {"root_folders": [str(root)]},
        "pairing": {
            "enabled": True,
            "source_extensions": [".cpp"],
            "header_extensions": [".h"]
        },
        "output": {
            "folder": str(out_dir),
            "sort_by": "size",
            "paired_filename_template": "{{STEM}}.combined"
        }
    }

    # file1.cpp is smaller than file2.cpp
    # So file1.combined should be processed before file2.combined
    # We can verify via logs or stats (though stats are totals)
    # Let's use dry-run and capture log output
    import logging
    from io import StringIO
    log_stream = StringIO()
    logger = logging.getLogger()
    old_level = logger.level
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(log_stream)
    logger.addHandler(handler)

    try:
        find_and_combine_files(config, str(out_dir), dry_run=True)
        log_output = log_stream.getvalue()
        # [PAIR file1] should appear before [PAIR file2]
        pos1 = log_output.find("[PAIR file1]")
        pos2 = log_output.find("[PAIR file2]")
        assert pos1 != -1
        assert pos2 != -1
        assert pos1 < pos2

        # Now reverse
        log_stream.truncate(0)
        log_stream.seek(0)
        config["output"]["sort_reverse"] = True
        find_and_combine_files(config, str(out_dir), dry_run=True)
        log_output = log_stream.getvalue()
        pos1 = log_output.find("[PAIR file1]")
        pos2 = log_output.find("[PAIR file2]")
        assert pos1 > pos2

    finally:
        logger.removeHandler(handler)
        logger.setLevel(old_level)
