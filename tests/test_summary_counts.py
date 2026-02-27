import sys
import os
from pathlib import Path
from unittest.mock import patch
import pytest

# Adjust sys.path to include the project root
sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

import utils
from sourcecombine import find_and_combine_files

def test_summary_counts_with_filtering(tmp_path):
    """Verify that total_discovered and included counts are correct in stats."""
    root = tmp_path / "root"
    root.mkdir()
    (root / "file1.txt").write_text("content1")
    (root / "file2.log").write_text("content2")
    (root / "file3.txt").write_text("content3")

    out_file = tmp_path / "out.txt"
    config = {
        "search": {"root_folders": [str(root)], "recursive": False},
        "filters": {
            "exclusions": {"filenames": ["*.log"]}
        },
        "output": {"file": str(out_file)}
    }

    stats = find_and_combine_files(config, str(out_file))

    # Total discovered should be 3
    assert stats['total_discovered'] == 3
    # Included should be 2 (file1.txt, file3.txt)
    assert stats['total_files'] == 2

def test_summary_counts_with_limit(tmp_path, monkeypatch):
    """Verify that included count reflects the limit truncation while total_discovered does not."""
    root = tmp_path / "root"
    root.mkdir()
    # approx 1 token per 4 chars
    (root / "file1.txt").write_text("1234") # 1 token
    (root / "file2.txt").write_text("5678") # 1 token
    (root / "file3.txt").write_text("9012") # 1 token

    out_file = tmp_path / "out.txt"
    config = {
        "search": {"root_folders": [str(root)], "recursive": False},
        "filters": {"max_total_tokens": 2},
        "output": {
            "file": str(out_file),
            "header_template": None,
            "footer_template": None
        }
    }

    # Mock tiktoken to None for deterministic results
    monkeypatch.setattr(utils, "tiktoken", None)
    stats = find_and_combine_files(config, str(out_file))

    # Total discovered should be 3
    assert stats['total_discovered'] == 3
    # Included should be 2 due to limit
    assert stats['total_files'] == 2
    assert stats['token_limit_reached'] is True
